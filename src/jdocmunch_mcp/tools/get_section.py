"""Tool to get a specific section's content."""

from typing import Optional

from ..storage.index_store import IndexStore


def get_section(
    repo: str,
    section_id: str,
    storage_path: Optional[str] = None,
) -> dict:
    """
    Get the full content of a specific section.

    Args:
        repo: Repository identifier (owner/name or just name)
        section_id: The section ID to retrieve
        storage_path: Custom storage path (defaults to ~/.doc-index)

    Returns:
        Dict with section content and metadata
    """
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

    # Find section metadata
    section_meta = index.get_section(section_id)
    if not section_meta:
        return {"error": f"Section not found: {section_id}"}

    # Get content
    content = store.get_section_content(owner, name, section_id)
    if content is None:
        return {"error": f"Could not load section content: {section_id}"}

    return {
        "id": section_meta["id"],
        "title": section_meta["title"],
        "file": section_meta["file"],
        "path": section_meta["path"],
        "depth": section_meta["depth"],
        "parent": section_meta.get("parent"),
        "line_count": section_meta["line_count"],
        "byte_offset": section_meta.get("byte_offset", 0),
        "byte_length": section_meta.get("byte_length", 0),
        "content": content,
        "_meta": {
            "index_version": getattr(index, "index_version", 0),
            "indexed_at": index.indexed_at,
            "commit_hash": getattr(index, "commit_hash", ""),
        },
    }


def get_sections(
    repo: str,
    section_ids: list[str],
    storage_path: Optional[str] = None,
) -> dict:
    """
    Get the full content of multiple sections.

    Args:
        repo: Repository identifier (owner/name or just name)
        section_ids: List of section IDs to retrieve
        storage_path: Custom storage path (defaults to ~/.doc-index)

    Returns:
        Dict with sections content and any errors
    """
    results = []
    errors = []

    for section_id in section_ids:
        result = get_section(repo, section_id, storage_path)
        if "error" in result:
            errors.append({"id": section_id, "error": result["error"]})
        else:
            results.append(result)

    return {
        "sections": results,
        "errors": errors if errors else None,
    }
