"""AI-powered batch summarization of sections."""

import os
from typing import Optional

from ..parser.markdown import Section


class BatchSummarizer:
    """Generate summaries for documentation sections using AI."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
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

    def summarize_section(self, section: Section) -> str:
        """Generate a one-line summary for a section."""
        if not section.content.strip():
            return ""

        # Skip very short sections
        if section.line_count < 3:
            return section.content.strip()[:100]

        try:
            response = self.client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=100,
                messages=[
                    {
                        "role": "user",
                        "content": f"""Summarize this documentation section in ONE short sentence (max 15 words).
Focus on what it explains or enables.

Title: {section.title}
Content:
{section.content[:2000]}

One-line summary:"""
                    }
                ],
            )
            return response.content[0].text.strip()
        except Exception as e:
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

    def _summarize_batch_internal(self, sections: list[Section]) -> list[str]:
        """Summarize a batch of sections in one API call."""
        if not sections:
            return []

        # Build batch prompt
        sections_text = []
        for idx, section in enumerate(sections):
            content_preview = section.content[:500]
            sections_text.append(
                f"[{idx}] Title: {section.title}\nContent: {content_preview}"
            )

        prompt = f"""Summarize each documentation section in ONE short sentence (max 15 words each).
Focus on what each section explains or enables.
Return ONLY numbered summaries, one per line.

Sections:
{"---".join(sections_text)}

Summaries (format: [0] summary text):"""

        try:
            response = self.client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}],
            )

            # Parse response
            response_text = response.content[0].text
            summaries = [""] * len(sections)

            for line in response_text.strip().split('\n'):
                line = line.strip()
                if line.startswith('['):
                    try:
                        bracket_end = line.index(']')
                        idx = int(line[1:bracket_end])
                        summary = line[bracket_end + 1:].strip()
                        if summary.startswith(':'):
                            summary = summary[1:].strip()
                        if 0 <= idx < len(sections):
                            summaries[idx] = summary
                    except (ValueError, IndexError):
                        continue

            # Fill in any missing summaries with fallbacks
            for idx, summary in enumerate(summaries):
                if not summary:
                    summaries[idx] = self._fallback_summary(sections[idx])

            return summaries

        except Exception:
            # Fallback for all sections
            return [self._fallback_summary(s) for s in sections]

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
