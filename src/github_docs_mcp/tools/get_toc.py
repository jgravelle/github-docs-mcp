"""Tool to get table of contents for a repository."""

from typing import Optional

from ..storage.index_store import IndexStore
from ..parser.hierarchy import build_section_tree, SectionNode


def get_toc(
    repo: str,
    storage_path: Optional[str] = None,
    include_summaries: bool = True,
) -> dict:
    """
    Get the table of contents for a repository's documentation.

    Args:
        repo: Repository identifier (owner/name or just name)
        storage_path: Custom storage path (defaults to ~/.doc-index)
        include_summaries: Whether to include section summaries

    Returns:
        Dict with hierarchical table of contents
    """
    store = IndexStore(storage_path)

    # Parse repo identifier
    if "/" in repo:
        owner, name = repo.split("/", 1)
    else:
        # Try to find by name only
        repos = store.list_repos()
        matching = [r for r in repos if r["repo"].endswith(f"/{repo}")]
        if not matching:
            return {"error": f"Repository not found: {repo}"}
        owner, name = matching[0]["repo"].split("/", 1)

    index = store.load_index(owner, name)
    if not index:
        return {"error": f"Repository not indexed: {owner}/{name}"}

    # Build hierarchical TOC
    toc_entries = []
    for section in index.sections:
        entry = {
            "id": section["id"],
            "title": section["title"],
            "depth": section["depth"],
            "file": section["file"],
            "line_count": section["line_count"],
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

    # Parse repo identifier
    if "/" in repo:
        owner, name = repo.split("/", 1)
    else:
        repos = store.list_repos()
        matching = [r for r in repos if r["repo"].endswith(f"/{repo}")]
        if not matching:
            return {"error": f"Repository not found: {repo}"}
        owner, name = matching[0]["repo"].split("/", 1)

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
    }
