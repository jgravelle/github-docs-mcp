"""Tool to search sections within a repository."""

from typing import Optional

from ..storage.index_store import IndexStore


def search_sections(
    repo: str,
    query: str,
    max_results: int = 10,
    storage_path: Optional[str] = None,
) -> dict:
    """
    Search for sections matching a query.

    Args:
        repo: Repository identifier (owner/name or just name)
        query: Search query (matches against titles, keywords, summaries)
        max_results: Maximum number of results to return
        storage_path: Custom storage path (defaults to ~/.doc-index)

    Returns:
        Dict with matching sections (IDs and summaries only)
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

    # Search
    matches = index.search(query)[:max_results]

    return {
        "repo": index.repo,
        "query": query,
        "result_count": len(matches),
        "results": [
            {
                "id": m["id"],
                "title": m["title"],
                "file": m["file"],
                "summary": m.get("summary", ""),
                "line_count": m["line_count"],
                "keywords": m.get("keywords", [])[:5],  # Limit keywords
            }
            for m in matches
        ],
    }
