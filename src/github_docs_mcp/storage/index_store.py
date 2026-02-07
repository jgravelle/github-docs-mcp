"""Index storage and retrieval."""

import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..parser.markdown import Section


@dataclass
class RepoIndex:
    """Index for a repository's documentation."""
    repo: str
    owner: str
    name: str
    indexed_at: str
    doc_files: list[str]
    sections: list[dict]

    def get_section(self, section_id: str) -> Optional[dict]:
        """Get a section by ID."""
        for section in self.sections:
            if section["id"] == section_id:
                return section
        return None

    def search(self, query: str) -> list[dict]:
        """Search sections by query (keywords and title)."""
        query_lower = query.lower()
        query_words = set(query_lower.split())

        results: list[tuple[int, dict]] = []
        for section in self.sections:
            score = 0

            # Title match
            title_lower = section["title"].lower()
            if query_lower in title_lower:
                score += 10
            for word in query_words:
                if word in title_lower:
                    score += 3

            # Keyword match
            keywords = set(section.get("keywords", []))
            matching_keywords = query_words & keywords
            score += len(matching_keywords) * 2

            # Summary match
            summary_lower = section.get("summary", "").lower()
            if query_lower in summary_lower:
                score += 5
            for word in query_words:
                if word in summary_lower:
                    score += 1

            if score > 0:
                results.append((score, section))

        # Sort by score descending
        results.sort(key=lambda x: -x[0])
        return [section for _, section in results]


class IndexStore:
    """Manages storage and retrieval of repo indexes."""

    def __init__(self, base_path: Optional[str] = None):
        if base_path:
            self.base_path = Path(base_path)
        else:
            # Default to ~/.doc-index
            self.base_path = Path.home() / ".doc-index"
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _repo_key(self, owner: str, name: str) -> str:
        """Generate storage key for a repo."""
        return f"{owner}-{name}"

    def _index_path(self, owner: str, name: str) -> Path:
        """Get path to index JSON file."""
        return self.base_path / f"{self._repo_key(owner, name)}.json"

    def _content_dir(self, owner: str, name: str) -> Path:
        """Get path to content directory."""
        return self.base_path / self._repo_key(owner, name)

    def save_index(
        self,
        owner: str,
        name: str,
        doc_files: list[str],
        sections: list[Section],
        raw_files: dict[str, str],
    ) -> RepoIndex:
        """
        Save a repo index and raw content files.

        Args:
            owner: Repository owner
            name: Repository name
            doc_files: List of documentation file paths
            sections: Parsed sections with summaries
            raw_files: Dict mapping file paths to raw content

        Returns:
            The saved RepoIndex
        """
        # Create content directory
        content_dir = self._content_dir(owner, name)
        content_dir.mkdir(parents=True, exist_ok=True)

        # Save raw files
        for file_path, content in raw_files.items():
            file_full_path = content_dir / file_path
            file_full_path.parent.mkdir(parents=True, exist_ok=True)
            file_full_path.write_text(content, encoding="utf-8")

        # Build index
        index = RepoIndex(
            repo=f"{owner}/{name}",
            owner=owner,
            name=name,
            indexed_at=datetime.utcnow().isoformat(),
            doc_files=doc_files,
            sections=[
                {
                    "id": s.id,
                    "file": s.file,
                    "path": s.path,
                    "title": s.title,
                    "depth": s.depth,
                    "parent": s.parent,
                    "summary": s.summary,
                    "keywords": s.keywords,
                    "line_count": s.line_count,
                    "byte_offset": s.byte_offset,
                    "byte_length": s.byte_length,
                }
                for s in sections
            ],
        )

        # Save index JSON
        index_path = self._index_path(owner, name)
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(asdict(index), f, indent=2)

        return index

    def load_index(self, owner: str, name: str) -> Optional[RepoIndex]:
        """Load a repo index if it exists."""
        index_path = self._index_path(owner, name)
        if not index_path.exists():
            return None

        with open(index_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return RepoIndex(**data)

    def get_section_content(
        self,
        owner: str,
        name: str,
        section_id: str,
    ) -> Optional[str]:
        """
        Get the raw content for a specific section.

        Uses byte_offset and byte_length from the index for efficient reads.
        """
        index = self.load_index(owner, name)
        if not index:
            return None

        section = index.get_section(section_id)
        if not section:
            return None

        content_path = self._content_dir(owner, name) / section["file"]
        if not content_path.exists():
            return None

        # Read the full file and extract section
        # For now, we store content in the index during parsing
        # In production, we'd use byte_offset/length for large files
        with open(content_path, "r", encoding="utf-8") as f:
            full_content = f.read()

        # Re-parse to get section content
        # (In production, use byte offsets for efficiency)
        from ..parser.markdown import parse_markdown_to_sections
        sections = parse_markdown_to_sections(full_content, section["file"])
        for s in sections:
            if s.id == section_id:
                return s.content

        return None

    def list_repos(self) -> list[dict]:
        """List all indexed repositories."""
        repos = []
        for index_file in self.base_path.glob("*.json"):
            try:
                with open(index_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                repos.append({
                    "repo": data["repo"],
                    "indexed_at": data["indexed_at"],
                    "section_count": len(data["sections"]),
                    "file_count": len(data["doc_files"]),
                })
            except (json.JSONDecodeError, KeyError):
                continue
        return repos

    def delete_index(self, owner: str, name: str) -> bool:
        """Delete a repo index and its content."""
        import shutil

        index_path = self._index_path(owner, name)
        content_dir = self._content_dir(owner, name)

        deleted = False
        if index_path.exists():
            index_path.unlink()
            deleted = True
        if content_dir.exists():
            shutil.rmtree(content_dir)
            deleted = True

        return deleted
