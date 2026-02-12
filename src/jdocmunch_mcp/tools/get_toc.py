"""Tool to get table of contents for a repository."""

import fnmatch
from typing import Optional

from ..storage.index_store import IndexStore
from ..parser.hierarchy import build_section_tree, SectionNode


def _resolve_repo(store: IndexStore, repo: str) -> tuple[Optional[str], Optional[str], Optional[dict]]:
    """Parse repo identifier and return (owner, name, error_dict)."""
    if "/" in repo:
        owner, name = repo.split("/", 1)
    else:
        repos = store.list_repos()
        matching = [r for r in repos if r["repo"].endswith(f"/{repo}")]
        if not matching:
            return None, None, {"error": f"Repository not found: {repo}"}
        owner, name = matching[0]["repo"].split("/", 1)
    return owner, name, None


def _filter_sections(
    sections: list[dict],
    path_prefix: Optional[str] = None,
    max_depth: Optional[int] = None,
    file_pattern: Optional[str] = None,
) -> list[dict]:
    """Filter sections by path prefix, depth, and file glob pattern."""
    result = sections
    if path_prefix:
        result = [s for s in result if s["file"].startswith(path_prefix)]
    if max_depth is not None:
        result = [s for s in result if s["depth"] <= max_depth]
    if file_pattern:
        result = [s for s in result if fnmatch.fnmatch(s["file"], file_pattern)]
    return result


def _build_meta(index) -> dict:
    """Build standard _meta envelope from an index."""
    return {
        "index_version": getattr(index, "index_version", 0),
        "indexed_at": index.indexed_at,
        "commit_hash": getattr(index, "commit_hash", ""),
    }


def get_toc(
    repo: str,
    storage_path: Optional[str] = None,
    include_summaries: bool = True,
    path_prefix: Optional[str] = None,
    max_depth: Optional[int] = None,
    file_pattern: Optional[str] = None,
) -> dict:
    """
    Get the table of contents for a repository's documentation.

    Args:
        repo: Repository identifier (owner/name or just name)
        storage_path: Custom storage path (defaults to ~/.doc-index)
        include_summaries: Whether to include section summaries
        path_prefix: Only include sections from files starting with this prefix
        max_depth: Only include sections with depth <= this value
        file_pattern: Glob pattern to filter files (e.g. "docs/api/*.md")

    Returns:
        Dict with hierarchical table of contents
    """
    store = IndexStore(storage_path)
    owner, name, err = _resolve_repo(store, repo)
    if err:
        return err

    index = store.load_index(owner, name)
    if not index:
        return {"error": f"Repository not indexed: {owner}/{name}"}

    # Apply filters
    filtered = _filter_sections(index.sections, path_prefix, max_depth, file_pattern)

    # Build hierarchical TOC
    toc_entries = []
    for section in filtered:
        entry = {
            "id": section["id"],
            "title": section["title"],
            "depth": section["depth"],
            "file": section["file"],
            "line_count": section["line_count"],
            "byte_offset": section.get("byte_offset", 0),
            "byte_length": section.get("byte_length", 0),
        }
        if include_summaries and section.get("summary"):
            entry["summary"] = section["summary"]
        if section.get("parent"):
            entry["parent"] = section["parent"]
        toc_entries.append(entry)

    return {
        "repo": index.repo,
        "indexed_at": index.indexed_at,
        "files": index.doc_files,
        "section_count": len(toc_entries),
        "sections": toc_entries,
        "_meta": _build_meta(index),
    }


def get_toc_tree(
    repo: str,
    storage_path: Optional[str] = None,
) -> dict:
    """
    Get the table of contents as a nested tree structure.

    Args:
        repo: Repository identifier (owner/name or just name)
        storage_path: Custom storage path (defaults to ~/.doc-index)

    Returns:
        Dict with nested tree structure
    """
    from ..parser.markdown import Section

    store = IndexStore(storage_path)
    owner, name, err = _resolve_repo(store, repo)
    if err:
        return err

    index = store.load_index(owner, name)
    if not index:
        return {"error": f"Repository not indexed: {owner}/{name}"}

    # Convert to Section objects for tree building
    sections = [
        Section(
            id=s["id"],
            file=s["file"],
            path=s["path"],
            title=s["title"],
            depth=s["depth"],
            parent=s.get("parent"),
            content="",  # Not loaded
            summary=s.get("summary", ""),
            keywords=s.get("keywords", []),
            line_count=s["line_count"],
            byte_offset=s.get("byte_offset", 0),
            byte_length=s.get("byte_length", 0),
        )
        for s in index.sections
    ]

    tree = build_section_tree(sections)

    def node_to_dict(node: SectionNode) -> dict:
        return {
            "id": node.section.id,
            "title": node.section.title,
            "summary": node.section.summary,
            "line_count": node.section.line_count,
            "children": [node_to_dict(child) for child in node.children],
        }

    return {
        "repo": index.repo,
        "tree": [node_to_dict(node) for node in tree],
        "_meta": _build_meta(index),
    }


def get_document_outline(
    repo: str,
    file_path: str,
    storage_path: Optional[str] = None,
) -> dict:
    """
    Get the hierarchical outline of a single file.

    Args:
        repo: Repository identifier (owner/name or just name)
        file_path: Path of the file within the repo
        storage_path: Custom storage path (defaults to ~/.doc-index)

    Returns:
        Dict with nested tree structure for the specified file
    """
    from ..parser.markdown import Section

    store = IndexStore(storage_path)
    owner, name, err = _resolve_repo(store, repo)
    if err:
        return err

    index = store.load_index(owner, name)
    if not index:
        return {"error": f"Repository not indexed: {owner}/{name}"}

    # Filter to sections from this file only
    file_sections = [s for s in index.sections if s["file"] == file_path]
    if not file_sections:
        return {"error": f"File not found in index: {file_path}"}

    sections = [
        Section(
            id=s["id"],
            file=s["file"],
            path=s["path"],
            title=s["title"],
            depth=s["depth"],
            parent=s.get("parent"),
            content="",
            summary=s.get("summary", ""),
            keywords=s.get("keywords", []),
            line_count=s["line_count"],
            byte_offset=s.get("byte_offset", 0),
            byte_length=s.get("byte_length", 0),
        )
        for s in file_sections
    ]

    tree = build_section_tree(sections)

    def node_to_dict(node: SectionNode) -> dict:
        return {
            "id": node.section.id,
            "title": node.section.title,
            "depth": node.section.depth,
            "summary": node.section.summary,
            "line_count": node.section.line_count,
            "byte_offset": node.section.byte_offset,
            "byte_length": node.section.byte_length,
            "children": [node_to_dict(child) for child in node.children],
        }

    return {
        "repo": index.repo,
        "file": file_path,
        "outline": [node_to_dict(node) for node in tree],
        "_meta": _build_meta(index),
    }
