"""Tool to search sections within a repository."""

import fnmatch
from typing import Optional

from ..storage.index_store import IndexStore


def search_sections(
    repo: str,
    query: str,
    max_results: int = 10,
    storage_path: Optional[str] = None,
    path_prefix: Optional[str] = None,
    max_depth: Optional[int] = None,
    file_pattern: Optional[str] = None,
) -> dict:
    """
    Search for sections matching a query.

    Args:
        repo: Repository identifier (owner/name or just name)
        query: Search query (matches against titles, keywords, summaries)
        max_results: Maximum number of results to return
        storage_path: Custom storage path (defaults to ~/.doc-index)
        path_prefix: Only search sections from files starting with this prefix
        max_depth: Only search sections with depth <= this value
        file_pattern: Glob pattern to filter files (e.g. "docs/*.md")

    Returns:
        Dict with matching sections (IDs and summaries only)
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

    # Search
    matches = index.search(query)

    # Apply filters
    if path_prefix:
        matches = [m for m in matches if m["file"].startswith(path_prefix)]
    if max_depth is not None:
        matches = [m for m in matches if m["depth"] <= max_depth]
    if file_pattern:
        matches = [m for m in matches if fnmatch.fnmatch(m["file"], file_pattern)]

    matches = matches[:max_results]

    return {
        "repo": index.repo,
        "query": query,
        "result_count": len(matches),
        "results": [
            {
                "id": m["id"],
                "title": m["title"],
                "file": m["file"],
                "depth": m["depth"],
                "summary": m.get("summary", ""),
                "line_count": m["line_count"],
                "byte_offset": m.get("byte_offset", 0),
                "byte_length": m.get("byte_length", 0),
                "keywords": m.get("keywords", [])[:5],
            }
            for m in matches
        ],
        "_meta": {
            "index_version": getattr(index, "index_version", 0),
            "indexed_at": index.indexed_at,
            "commit_hash": getattr(index, "commit_hash", ""),
        },
    }
