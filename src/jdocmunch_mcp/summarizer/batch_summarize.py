"""AI-powered batch summarization of sections."""

import asyncio
import logging
import os
from typing import Optional

from ..parser.markdown import Section

logger = logging.getLogger(__name__)

# Max concurrent Ollama/Anthropic requests
DEFAULT_CONCURRENCY = 8


class BatchSummarizer:
    """Generate summaries for documentation sections using AI (Anthropic or Ollama)."""

    def __init__(self, api_key: Optional[str] = None, concurrency: int = DEFAULT_CONCURRENCY):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.ollama_url = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/generate")
        self.ollama_model = os.environ.get("OLLAMA_MODEL", "qwen3:4b")
        self.use_ollama = os.environ.get("USE_OLLAMA", "true").lower() == "true"
        self.concurrency = concurrency
        self._client = None
        self._http_client = None

    @property
    def client(self):
        """Lazy-load Anthropic client."""
        if self._client is None:
            try:
                import anthropic
                self._client = anthropic.AsyncAnthropic(api_key=self.api_key)
            except ImportError:
                raise ImportError("anthropic package required for summarization")
        return self._client

    async def _get_http_client(self):
        """Lazy-load shared async httpx client."""
        if self._http_client is None:
            import httpx
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self._http_client

    async def close(self):
        """Close shared HTTP client."""
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

    async def _ollama_summarize(self, prompt: str, max_tokens: int = 100) -> str:
        """Call local Ollama server for summarization (async)."""
        try:
            client = await self._get_http_client()
            response = await client.post(
                self.ollama_url,
                json={
                    "model": self.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"num_predict": max_tokens},
                },
            )
            response.raise_for_status()
            data = response.json()
            return data.get("response", "").strip()
        except Exception as e:
            logger.warning("Ollama error: %s", e)
            return ""

    async def _anthropic_summarize(self, prompt: str) -> str:
        """Call Anthropic API for summarization (async)."""
        try:
            response = await self.client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=100,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text.strip()
        except Exception as e:
            logger.warning("Anthropic summarization error: %s", e)
            return ""

    async def summarize_section(self, section: Section) -> str:
        """Generate a one-line summary for a section."""
        if not section.content.strip():
            return ""

        # Skip very short sections — no AI needed
        if section.line_count < 3:
            return section.content.strip()[:100]

        prompt = f"""Summarize this documentation section in ONE short sentence (max 15 words).
Focus on what it explains or enables.

Title: {section.title}
Content:
{section.content[:2000]}

One-line summary:"""

        # Try Ollama first, then Anthropic, then fallback
        if self.use_ollama:
            result = await self._ollama_summarize(prompt, max_tokens=100)
            if result:
                return result

        if self.api_key:
            result = await self._anthropic_summarize(prompt)
            if result:
                return result

        return _fallback_summary(section)

    async def summarize_batch(
        self,
        sections: list[Section],
    ) -> list[Section]:
        """
        Generate summaries for multiple sections concurrently.
        Uses a semaphore to limit parallel requests.
        """
        semaphore = asyncio.Semaphore(self.concurrency)

        async def _summarize_one(section: Section) -> None:
            async with semaphore:
                section.summary = await self.summarize_section(section)

        await asyncio.gather(*[_summarize_one(s) for s in sections])

        try:
            await self.close()
        except Exception:
            pass

        return sections


def summarize_sections_simple(sections: list[Section]) -> list[Section]:
    """Simple keyword-based summarization without AI."""
    for section in sections:
        section.summary = _simple_summary(section)
    return sections


def _fallback_summary(section: Section) -> str:
    """Extract first meaningful content line as summary."""
    for line in section.content.split('\n'):
        line = line.strip()
        if line and not line.startswith('#'):
            return line[:100]
    return section.title


def _simple_summary(section: Section) -> str:
    """Generate a simple summary from content."""
    lines = section.content.split('\n')

    # Skip header line and find first content line
    for line in lines:
        line = line.strip()
        if line and not line.startswith('#') and not line.startswith('```'):
            # Truncate and clean
            summary = line[:120]
            if len(line) > 120:
                summary += "..."
            return summary

    return section.title
