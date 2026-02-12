"""Index storage and retrieval."""

import json
import os
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..parser.markdown import Section

# Increment this when the index schema changes in a backward-incompatible way.
# Old caches with a lower version will be discarded and re-indexed.
CURRENT_INDEX_VERSION = 1


@dataclass
class RepoIndex:
    """Index for a repository's documentation."""
    repo: str
    owner: str
    name: str
    indexed_at: str
    doc_files: list[str]
    sections: list[dict]
    # P1-4: New fields for cache correctness
    index_version: int = CURRENT_INDEX_VERSION
    commit_hash: str = ""
    file_hashes: dict[str, str] = field(default_factory=dict)

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
        commit_hash: str = "",
        file_hashes: Optional[dict[str, str]] = None,
    ) -> RepoIndex:
        """
        Save a repo index and raw content files.

        Args:
            owner: Repository owner
            name: Repository name
            doc_files: List of documentation file paths
            sections: Parsed sections with summaries
            raw_files: Dict mapping file paths to raw content
            commit_hash: Git commit SHA at time of indexing
            file_hashes: Dict mapping file paths to content hashes

        Returns:
            The saved RepoIndex
        """
        # Create content directory
        content_dir = self._content_dir(owner, name)
        content_dir.mkdir(parents=True, exist_ok=True)

        # Save raw files — normalize line endings to \n for consistent byte offsets
        for file_path, content in raw_files.items():
            normalized = content.replace('\r\n', '\n')
            file_full_path = content_dir / file_path
            file_full_path.parent.mkdir(parents=True, exist_ok=True)
            file_full_path.write_text(normalized, encoding="utf-8", newline='')

        # Build index
        index = RepoIndex(
            repo=f"{owner}/{name}",
            owner=owner,
            name=name,
            indexed_at=datetime.now(tz=None).isoformat(),
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
            index_version=CURRENT_INDEX_VERSION,
            commit_hash=commit_hash,
            file_hashes=file_hashes or {},
        )

        # Save index JSON
        index_path = self._index_path(owner, name)
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(asdict(index), f, indent=2)

        return index

    def load_index(self, owner: str, name: str) -> Optional[RepoIndex]:
        """Load a repo index if it exists. Returns None for outdated indexes."""
        index_path = self._index_path(owner, name)
        if not index_path.exists():
            return None

        with open(index_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # P1-5: Backward-compatible cache loading
        stored_version = data.get("index_version", 0)
        if stored_version < CURRENT_INDEX_VERSION:
            # Old format — force re-index
            return None

        # Apply defaults for any missing new fields
        data.setdefault("index_version", CURRENT_INDEX_VERSION)
        data.setdefault("commit_hash", "")
        data.setdefault("file_hashes", {})

        return RepoIndex(**data)

    def get_section_content(
        self,
        owner: str,
        name: str,
        section_id: str,
    ) -> Optional[str]:
        """
        Get the raw content for a specific section.

        Uses byte_offset and byte_length for efficient O(1) reads.
        Falls back to re-parse if byte offsets are unavailable.
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

        byte_offset = section.get("byte_offset", 0)
        byte_length = section.get("byte_length", 0)

        # P2-4: Use byte-offset retrieval when available
        if byte_length > 0:
            try:
                with open(content_path, "rb") as f:
                    f.seek(byte_offset)
                    content = f.read(byte_length).decode("utf-8")
                return content
            except (OSError, UnicodeDecodeError):
                pass  # Fall through to re-parse

        # Fallback: Re-parse to get section content
        with open(content_path, "r", encoding="utf-8") as f:
            full_content = f.read()

        from ..parser.markdown import parse_markdown_to_sections
        sections = parse_markdown_to_sections(full_content, section["file"])
        for s in sections:
            if s.id == section_id:
                return s.content

        return None

    def update_index(
        self,
        owner: str,
        name: str,
        changed_files: dict[str, str],
        deleted_files: list[str],
        new_sections_by_file: dict[str, list[Section]],
        new_file_hashes: dict[str, str],
        commit_hash: str = "",
    ) -> Optional[RepoIndex]:
        """
        Incrementally update an existing index.

        Args:
            owner: Repository owner
            name: Repository name
            changed_files: Dict of changed file paths to new raw content
            deleted_files: List of deleted file paths
            new_sections_by_file: Dict of file path to new parsed sections
            new_file_hashes: Updated file hashes for changed/new files
            commit_hash: New commit hash

        Returns:
            Updated RepoIndex or None if no existing index
        """
        index = self.load_index(owner, name)
        if not index:
            return None

        content_dir = self._content_dir(owner, name)

        # Remove sections and files for deleted files
        affected_files = set(deleted_files) | set(changed_files.keys())
        remaining_sections = [
            s for s in index.sections if s["file"] not in affected_files
        ]
        remaining_doc_files = [
            f for f in index.doc_files if f not in set(deleted_files)
        ]

        # Remove cached raw files for deleted files
        for file_path in deleted_files:
            cached = content_dir / file_path
            if cached.exists():
                cached.unlink()
            index.file_hashes.pop(file_path, None)

        # Write changed file content and add new sections
        for file_path, content in changed_files.items():
            normalized = content.replace('\r\n', '\n')
            file_full_path = content_dir / file_path
            file_full_path.parent.mkdir(parents=True, exist_ok=True)
            file_full_path.write_text(normalized, encoding="utf-8", newline='')

            if file_path not in remaining_doc_files:
                remaining_doc_files.append(file_path)

        # Add new sections for changed files
        for file_path, sections in new_sections_by_file.items():
            for s in sections:
                remaining_sections.append({
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
                })

        # Update file hashes
        updated_hashes = dict(index.file_hashes)
        updated_hashes.update(new_file_hashes)
        for f in deleted_files:
            updated_hashes.pop(f, None)

        remaining_doc_files.sort()

        # Build updated index
        updated_index = RepoIndex(
            repo=index.repo,
            owner=owner,
            name=name,
            indexed_at=datetime.now(tz=None).isoformat(),
            doc_files=remaining_doc_files,
            sections=remaining_sections,
            index_version=CURRENT_INDEX_VERSION,
            commit_hash=commit_hash or index.commit_hash,
            file_hashes=updated_hashes,
        )

        # Save
        index_path = self._index_path(owner, name)
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(asdict(updated_index), f, indent=2)

        return updated_index

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
                    "index_version": data.get("index_version", 0),
                    "commit_hash": data.get("commit_hash", ""),
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
