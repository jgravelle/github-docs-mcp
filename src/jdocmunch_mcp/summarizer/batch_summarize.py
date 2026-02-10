"""AI-powered batch summarization of sections."""

import os
import json
from typing import Optional

from ..parser.markdown import Section


class BatchSummarizer:
    """Generate summaries for documentation sections using AI (Anthropic or Ollama)."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.ollama_url = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/generate")
        self.ollama_model = os.environ.get("OLLAMA_MODEL", "qwen3:4b")
        self.use_ollama = os.environ.get("USE_OLLAMA", "true").lower() == "true"
        self._client = None

    @property
    def client(self):
        """Lazy-load Anthropic client."""
        if self._client is None:
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=self.api_key)
            except ImportError:
                raise ImportError("anthropic package required for summarization")
        return self._client

    def _ollama_summarize(self, prompt: str, max_tokens: int = 100) -> str:
        """Call local Ollama server for summarization."""
        try:
            import httpx
            response = httpx.post(
                self.ollama_url,
                json={
                    "model": self.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"num_predict": max_tokens}
                },
                timeout=60.0
            )
            response.raise_for_status()
            data = response.json()
            return data.get("response", "").strip()
        except Exception as e:
            print(f"Ollama error: {e}")
            return ""

    def summarize_section(self, section: Section) -> str:
        """Generate a one-line summary for a section."""
        if not section.content.strip():
            return ""

        # Skip very short sections
        if section.line_count < 3:
            return section.content.strip()[:100]

        prompt = f"""Summarize this documentation section in ONE short sentence (max 15 words).
Focus on what it explains or enables.

Title: {section.title}
Content:
{section.content[:2000]}

One-line summary:"""

        try:
            if self.use_ollama:
                result = self._ollama_summarize(prompt, max_tokens=100)
                if result:
                    return result

            # Try Anthropic as fallback
            if self.api_key:
                response = self.client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=100,
                    messages=[{"role": "user", "content": prompt}],
                )
                return response.content[0].text.strip()
        except Exception as e:
            print(f"Summarization error: {e}")

        # Fallback: use first non-empty line
        for line in section.content.split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                return line[:100]
        return section.title

    def summarize_batch(
        self,
        sections: list[Section],
        batch_size: int = 10,
    ) -> list[Section]:
        """
        Generate summaries for multiple sections.

        Batches requests to reduce API calls.
        """
        # For efficiency, batch multiple sections into single requests
        result_sections = []

        for i in range(0, len(sections), batch_size):
            batch = sections[i:i + batch_size]
            summaries = self._summarize_batch_internal(batch)

            for section, summary in zip(batch, summaries):
                section.summary = summary
                result_sections.append(section)

        return result_sections

    def summarize_batch(
        self,
        sections: list[Section],
        batch_size: int = 5,
    ) -> list[Section]:
        """
        Generate summaries for multiple sections using Ollama.
        Processes individually for better Ollama compatibility.
        """
        result_sections = []

        for section in sections:
            summary = self.summarize_section(section)
            section.summary = summary
            result_sections.append(section)

        return result_sections

    def _summarize_batch_internal(self, sections: list[Section]) -> list[str]:
        """Summarize a batch of sections (individual processing for Ollama)."""
        return [self.summarize_section(s) for s in sections]

    def _fallback_summary(self, section: Section) -> str:
        """Generate a simple fallback summary without AI."""
        # Use first non-header, non-empty line
        for line in section.content.split('\n'):
            line = line.strip()
            if line and not line.startswith('#') and not line.startswith('```'):
                return line[:100]
        return section.title


def summarize_sections_simple(sections: list[Section]) -> list[Section]:
    """Simple keyword-based summarization without AI."""
    for section in sections:
        section.summary = _simple_summary(section)
    return sections


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
