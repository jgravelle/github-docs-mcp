"""Tests for MCP tool implementations."""

import os
import pytest

from jdocmunch_mcp.parser.markdown import parse_markdown_to_sections
from jdocmunch_mcp.storage.index_store import IndexStore
from jdocmunch_mcp.tools.get_toc import get_toc, get_toc_tree, get_document_outline
from jdocmunch_mcp.tools.get_section import get_section, get_sections
from jdocmunch_mcp.tools.search_sections import search_sections
from jdocmunch_mcp.tools.list_repos import list_repos
from jdocmunch_mcp.tools.index_local import index_local


def _create_test_index(storage_dir: str, owner: str = "test", name: str = "repo"):
    """Helper to create a test index with known content."""
    store = IndexStore(storage_dir)
    content1 = "# Project\n\nWelcome.\n\n## Installation\n\nInstall with pip.\n\n## Usage\n\nUse it.\n"
    content2 = "# API Guide\n\n## Authentication\n\nUse tokens.\n\n## Endpoints\n\n### GET /users\n\nList users.\n"

    sections1 = parse_markdown_to_sections(content1, "README.md")
    sections2 = parse_markdown_to_sections(content2, "docs/api.md")
    all_sections = sections1 + sections2

    # Give sections summaries for search
    for s in all_sections:
        s.summary = f"Summary: {s.title}"

    store.save_index(
        owner, name,
        ["README.md", "docs/api.md"],
        all_sections,
        {"README.md": content1, "docs/api.md": content2},
        commit_hash="abc123",
        file_hashes={"README.md": "h1", "docs/api.md": "h2"},
    )
    return f"{owner}/{name}"


class TestGetToc:
    def test_basic(self, storage_dir):
        repo = _create_test_index(storage_dir)
        result = get_toc(repo=repo, storage_path=storage_dir)
        assert "error" not in result
        assert result["section_count"] > 0
        assert "_meta" in result
        assert result["_meta"]["commit_hash"] == "abc123"

    def test_path_prefix_filter(self, storage_dir):
        repo = _create_test_index(storage_dir)
        result = get_toc(repo=repo, storage_path=storage_dir, path_prefix="docs/")
        assert "error" not in result
        # Only docs/api.md sections
        for section in result["sections"]:
            assert section["file"].startswith("docs/")

    def test_max_depth_filter(self, storage_dir):
        repo = _create_test_index(storage_dir)
        result = get_toc(repo=repo, storage_path=storage_dir, max_depth=1)
        assert "error" not in result
        for section in result["sections"]:
            assert section["depth"] <= 1

    def test_file_pattern_filter(self, storage_dir):
        repo = _create_test_index(storage_dir)
        result = get_toc(repo=repo, storage_path=storage_dir, file_pattern="*.md")
        assert "error" not in result
        assert result["section_count"] > 0

    def test_include_summaries(self, storage_dir):
        repo = _create_test_index(storage_dir)
        result = get_toc(repo=repo, storage_path=storage_dir, include_summaries=True)
        has_summary = any("summary" in s for s in result["sections"])
        assert has_summary

    def test_repo_not_found(self, storage_dir):
        result = get_toc(repo="nonexistent/repo", storage_path=storage_dir)
        assert "error" in result

    def test_byte_offsets_in_response(self, storage_dir):
        repo = _create_test_index(storage_dir)
        result = get_toc(repo=repo, storage_path=storage_dir)
        for section in result["sections"]:
            assert "byte_offset" in section
            assert "byte_length" in section


class TestGetTocTree:
    def test_basic(self, storage_dir):
        repo = _create_test_index(storage_dir)
        result = get_toc_tree(repo=repo, storage_path=storage_dir)
        assert "error" not in result
        assert "tree" in result
        assert len(result["tree"]) > 0
        assert "_meta" in result


class TestGetDocumentOutline:
    def test_single_file(self, storage_dir):
        repo = _create_test_index(storage_dir)
        result = get_document_outline(repo=repo, file_path="docs/api.md", storage_path=storage_dir)
        assert "error" not in result
        assert result["file"] == "docs/api.md"
        assert "outline" in result
        assert len(result["outline"]) > 0

    def test_file_not_found(self, storage_dir):
        repo = _create_test_index(storage_dir)
        result = get_document_outline(repo=repo, file_path="nonexistent.md", storage_path=storage_dir)
        assert "error" in result


class TestGetSection:
    def test_retrieve_section(self, storage_dir):
        repo = _create_test_index(storage_dir)
        # Get TOC to find a section ID
        toc = get_toc(repo=repo, storage_path=storage_dir)
        section_id = toc["sections"][0]["id"]

        result = get_section(repo=repo, section_id=section_id, storage_path=storage_dir)
        assert "error" not in result
        assert "content" in result
        assert result["id"] == section_id
        assert "_meta" in result

    def test_section_not_found(self, storage_dir):
        repo = _create_test_index(storage_dir)
        result = get_section(repo=repo, section_id="nonexistent-id", storage_path=storage_dir)
        assert "error" in result

    def test_byte_offsets_in_response(self, storage_dir):
        repo = _create_test_index(storage_dir)
        toc = get_toc(repo=repo, storage_path=storage_dir)
        section_id = toc["sections"][0]["id"]

        result = get_section(repo=repo, section_id=section_id, storage_path=storage_dir)
        assert "byte_offset" in result
        assert "byte_length" in result


class TestGetSections:
    def test_batch_retrieve(self, storage_dir):
        repo = _create_test_index(storage_dir)
        toc = get_toc(repo=repo, storage_path=storage_dir)
        ids = [s["id"] for s in toc["sections"][:3]]

        result = get_sections(repo=repo, section_ids=ids, storage_path=storage_dir)
        assert len(result["sections"]) == len(ids)
        assert result["errors"] is None

    def test_partial_errors(self, storage_dir):
        repo = _create_test_index(storage_dir)
        toc = get_toc(repo=repo, storage_path=storage_dir)
        ids = [toc["sections"][0]["id"], "nonexistent-id"]

        result = get_sections(repo=repo, section_ids=ids, storage_path=storage_dir)
        assert len(result["sections"]) == 1
        assert len(result["errors"]) == 1


class TestSearchSections:
    def test_basic_search(self, storage_dir):
        repo = _create_test_index(storage_dir)
        result = search_sections(repo=repo, query="install", storage_path=storage_dir)
        assert "error" not in result
        assert result["result_count"] > 0
        assert "_meta" in result

    def test_max_results(self, storage_dir):
        repo = _create_test_index(storage_dir)
        result = search_sections(repo=repo, query="project", max_results=2, storage_path=storage_dir)
        assert result["result_count"] <= 2

    def test_path_prefix_filter(self, storage_dir):
        repo = _create_test_index(storage_dir)
        result = search_sections(
            repo=repo, query="authentication", storage_path=storage_dir,
            path_prefix="docs/",
        )
        for r in result["results"]:
            assert r["file"].startswith("docs/")

    def test_max_depth_filter(self, storage_dir):
        repo = _create_test_index(storage_dir)
        result = search_sections(
            repo=repo, query="users", storage_path=storage_dir,
            max_depth=2,
        )
        for r in result["results"]:
            assert r["depth"] <= 2

    def test_no_results(self, storage_dir):
        repo = _create_test_index(storage_dir)
        result = search_sections(repo=repo, query="xyznonexistent", storage_path=storage_dir)
        assert result["result_count"] == 0

    def test_result_fields(self, storage_dir):
        repo = _create_test_index(storage_dir)
        result = search_sections(repo=repo, query="install", storage_path=storage_dir)
        if result["results"]:
            r = result["results"][0]
            assert "id" in r
            assert "title" in r
            assert "file" in r
            assert "summary" in r
            assert "byte_offset" in r
            assert "byte_length" in r


class TestListRepos:
    def test_empty(self, storage_dir):
        result = list_repos(storage_path=storage_dir)
        assert result["count"] == 0
        assert result["repos"] == []

    def test_with_repos(self, storage_dir):
        _create_test_index(storage_dir, "owner1", "repo1")
        _create_test_index(storage_dir, "owner2", "repo2")
        result = list_repos(storage_path=storage_dir)
        assert result["count"] == 2


class TestDeleteIndex:
    def test_delete_via_store(self, storage_dir):
        repo = _create_test_index(storage_dir)
        store = IndexStore(storage_dir)
        assert store.delete_index("test", "repo") is True
        result = list_repos(storage_path=storage_dir)
        assert result["count"] == 0


class TestIndexLocal:
    @pytest.mark.asyncio
    async def test_index_local_basic(self, sample_doc_dir, storage_dir):
        result = await index_local(
            path=str(sample_doc_dir),
            use_ai_summaries=False,
            storage_path=storage_dir,
        )
        assert result["success"] is True
        assert result["file_count"] > 0
        assert result["section_count"] > 0
        assert "commit_hash" in result

    @pytest.mark.asyncio
    async def test_index_local_nonexistent_path(self, storage_dir):
        result = await index_local(
            path="/nonexistent/path/that/doesnt/exist",
            use_ai_summaries=False,
            storage_path=storage_dir,
        )
        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_index_local_skips_secrets(self, sample_doc_dir_with_secrets, storage_dir):
        result = await index_local(
            path=str(sample_doc_dir_with_secrets),
            use_ai_summaries=False,
            storage_path=storage_dir,
        )
        assert result["success"] is True
        # config.md has an AWS key pattern, should be skipped
        if "skipped_secrets" in result:
            assert "config.md" in result["skipped_secrets"]

    @pytest.mark.asyncio
    async def test_index_local_respects_gitignore(self, sample_doc_dir, storage_dir):
        result = await index_local(
            path=str(sample_doc_dir),
            use_ai_summaries=False,
            storage_path=storage_dir,
        )
        assert result["success"] is True
        # build/output.md should be excluded by .gitignore
        assert not any("build" in f for f in result["files"])


class TestLocalOnlyMode:
    @pytest.mark.asyncio
    async def test_index_local_works_in_local_only(self, sample_doc_dir, storage_dir, monkeypatch):
        monkeypatch.setenv("JDOCMUNCH_LOCAL_ONLY", "true")
        result = await index_local(
            path=str(sample_doc_dir),
            use_ai_summaries=True,  # Should fallback to simple summaries
            storage_path=storage_dir,
        )
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_index_repo_blocked_in_local_only(self, monkeypatch):
        monkeypatch.setenv("JDOCMUNCH_LOCAL_ONLY", "true")
        from jdocmunch_mcp.tools.index_repo import index_repo
        result = await index_repo(url="owner/repo", use_ai_summaries=False)
        assert result["success"] is False
        assert "local-only" in result["error"].lower()
