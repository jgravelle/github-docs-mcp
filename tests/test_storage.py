"""Tests for index storage and retrieval."""

import json
import pytest

from jdocmunch_mcp.parser.markdown import parse_markdown_to_sections, Section
from jdocmunch_mcp.storage.index_store import IndexStore, RepoIndex, CURRENT_INDEX_VERSION


class TestIndexStore:
    def test_save_and_load(self, storage_dir):
        store = IndexStore(storage_dir)
        content = "# Hello\n\nWorld.\n\n## Section\n\nContent here.\n"
        sections = parse_markdown_to_sections(content, "README.md")
        raw_files = {"README.md": content}

        index = store.save_index("test", "repo", ["README.md"], sections, raw_files)

        assert index.repo == "test/repo"
        assert index.index_version == CURRENT_INDEX_VERSION
        assert len(index.sections) == len(sections)

        # Load it back
        loaded = store.load_index("test", "repo")
        assert loaded is not None
        assert loaded.repo == "test/repo"
        assert len(loaded.sections) == len(sections)

    def test_save_with_commit_hash(self, storage_dir):
        store = IndexStore(storage_dir)
        content = "# Doc\n\nContent.\n"
        sections = parse_markdown_to_sections(content, "doc.md")

        index = store.save_index(
            "test", "repo", ["doc.md"], sections, {"doc.md": content},
            commit_hash="abc123def456",
            file_hashes={"doc.md": "sha256hash"},
        )

        assert index.commit_hash == "abc123def456"
        assert index.file_hashes == {"doc.md": "sha256hash"}

        loaded = store.load_index("test", "repo")
        assert loaded.commit_hash == "abc123def456"
        assert loaded.file_hashes["doc.md"] == "sha256hash"

    def test_backward_compatible_loading_rejects_old(self, storage_dir):
        """Old-format cache (no index_version) should return None."""
        store = IndexStore(storage_dir)
        # Write a fake old-format index
        index_path = store._index_path("old", "repo")
        old_data = {
            "repo": "old/repo",
            "owner": "old",
            "name": "repo",
            "indexed_at": "2024-01-01T00:00:00",
            "doc_files": ["README.md"],
            "sections": [],
            # No index_version field — should be treated as version 0
        }
        with open(index_path, "w") as f:
            json.dump(old_data, f)

        loaded = store.load_index("old", "repo")
        assert loaded is None  # Old format rejected

    def test_current_version_loads(self, storage_dir):
        """Current-version cache should load correctly."""
        store = IndexStore(storage_dir)
        index_path = store._index_path("current", "repo")
        data = {
            "repo": "current/repo",
            "owner": "current",
            "name": "repo",
            "indexed_at": "2025-01-15T00:00:00",
            "doc_files": ["README.md"],
            "sections": [],
            "index_version": CURRENT_INDEX_VERSION,
            "commit_hash": "abc123",
            "file_hashes": {},
        }
        with open(index_path, "w") as f:
            json.dump(data, f)

        loaded = store.load_index("current", "repo")
        assert loaded is not None
        assert loaded.commit_hash == "abc123"

    def test_line_ending_normalization(self, storage_dir):
        """Raw files should be normalized to \\n line endings."""
        store = IndexStore(storage_dir)
        content_crlf = "# Hello\r\n\r\nWorld.\r\n"
        sections = parse_markdown_to_sections(content_crlf.replace('\r\n', '\n'), "README.md")

        store.save_index("test", "norm", ["README.md"], sections, {"README.md": content_crlf})

        # Read the cached file — should have \n only
        cached = store._content_dir("test", "norm") / "README.md"
        raw = cached.read_bytes()
        assert b"\r\n" not in raw
        assert b"\n" in raw

    def test_get_section_content_byte_offset(self, storage_dir):
        """Byte-offset retrieval should return correct content."""
        store = IndexStore(storage_dir)
        content = "# Hello\n\nIntro paragraph.\n\n## Section Two\n\nSection two content.\n"
        sections = parse_markdown_to_sections(content, "doc.md")

        store.save_index("test", "repo", ["doc.md"], sections, {"doc.md": content})

        for s in sections:
            retrieved = store.get_section_content("test", "repo", s.id)
            assert retrieved is not None
            assert retrieved == s.content

    def test_delete_index(self, storage_dir):
        store = IndexStore(storage_dir)
        content = "# Doc\n\nContent.\n"
        sections = parse_markdown_to_sections(content, "doc.md")
        store.save_index("test", "repo", ["doc.md"], sections, {"doc.md": content})

        assert store.load_index("test", "repo") is not None
        assert store.delete_index("test", "repo") is True
        assert store.load_index("test", "repo") is None

    def test_delete_nonexistent(self, storage_dir):
        store = IndexStore(storage_dir)
        assert store.delete_index("nonexistent", "repo") is False

    def test_list_repos(self, storage_dir):
        store = IndexStore(storage_dir)
        content = "# Doc\n\nContent.\n"
        sections = parse_markdown_to_sections(content, "doc.md")

        store.save_index("owner1", "repo1", ["doc.md"], sections, {"doc.md": content})
        store.save_index("owner2", "repo2", ["doc.md"], sections, {"doc.md": content})

        repos = store.list_repos()
        assert len(repos) == 2
        repo_names = {r["repo"] for r in repos}
        assert "owner1/repo1" in repo_names
        assert "owner2/repo2" in repo_names

    def test_list_repos_includes_new_fields(self, storage_dir):
        store = IndexStore(storage_dir)
        content = "# Doc\n\nContent.\n"
        sections = parse_markdown_to_sections(content, "doc.md")
        store.save_index(
            "test", "repo", ["doc.md"], sections, {"doc.md": content},
            commit_hash="deadbeef",
        )

        repos = store.list_repos()
        assert len(repos) == 1
        assert repos[0]["index_version"] == CURRENT_INDEX_VERSION
        assert repos[0]["commit_hash"] == "deadbeef"

    def test_search(self, storage_dir):
        store = IndexStore(storage_dir)
        content = "# Installation\n\nInstall with pip.\n\n## Configuration\n\nConfigure settings.\n"
        sections = parse_markdown_to_sections(content, "doc.md")
        for s in sections:
            s.summary = f"Summary for {s.title}"

        index = store.save_index("test", "repo", ["doc.md"], sections, {"doc.md": content})
        loaded = store.load_index("test", "repo")

        results = loaded.search("install")
        assert len(results) > 0
        assert results[0]["title"] == "Installation"


class TestUpdateIndex:
    def test_incremental_update(self, storage_dir):
        store = IndexStore(storage_dir)

        # Initial index with 2 files
        content1 = "# File 1\n\nContent one.\n"
        content2 = "# File 2\n\nContent two.\n"
        sections1 = parse_markdown_to_sections(content1, "file1.md")
        sections2 = parse_markdown_to_sections(content2, "file2.md")
        all_sections = sections1 + sections2

        store.save_index(
            "test", "repo",
            ["file1.md", "file2.md"],
            all_sections,
            {"file1.md": content1, "file2.md": content2},
            file_hashes={"file1.md": "hash1", "file2.md": "hash2"},
        )

        # Update: file1 changed, file2 unchanged
        new_content1 = "# File 1 Updated\n\nNew content.\n"
        new_sections1 = parse_markdown_to_sections(new_content1, "file1.md")

        updated = store.update_index(
            "test", "repo",
            changed_files={"file1.md": new_content1},
            deleted_files=[],
            new_sections_by_file={"file1.md": new_sections1},
            new_file_hashes={"file1.md": "hash1_new"},
        )

        assert updated is not None
        assert len(updated.doc_files) == 2
        # File1 sections should be updated
        file1_sections = [s for s in updated.sections if s["file"] == "file1.md"]
        assert len(file1_sections) > 0
        assert file1_sections[0]["title"] == "File 1 Updated"
        # File2 sections should be preserved
        file2_sections = [s for s in updated.sections if s["file"] == "file2.md"]
        assert len(file2_sections) > 0
        # Hash updated
        assert updated.file_hashes["file1.md"] == "hash1_new"
        assert updated.file_hashes["file2.md"] == "hash2"

    def test_delete_file_in_update(self, storage_dir):
        store = IndexStore(storage_dir)

        content1 = "# File 1\n\nContent.\n"
        content2 = "# File 2\n\nContent.\n"
        sections = parse_markdown_to_sections(content1, "file1.md") + \
                   parse_markdown_to_sections(content2, "file2.md")

        store.save_index(
            "test", "repo",
            ["file1.md", "file2.md"],
            sections,
            {"file1.md": content1, "file2.md": content2},
            file_hashes={"file1.md": "h1", "file2.md": "h2"},
        )

        updated = store.update_index(
            "test", "repo",
            changed_files={},
            deleted_files=["file2.md"],
            new_sections_by_file={},
            new_file_hashes={},
        )

        assert updated is not None
        assert "file2.md" not in updated.doc_files
        assert "file2.md" not in updated.file_hashes
        assert all(s["file"] != "file2.md" for s in updated.sections)
