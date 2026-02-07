"""Tool to list indexed repositories."""

from typing import Optional

from ..storage.index_store import IndexStore


def list_repos(storage_path: Optional[str] = None) -> dict:
    """
    List all indexed repositories.

    Args:
        storage_path: Custom storage path (defaults to ~/.doc-index)

    Returns:
        Dict with list of indexed repos and their stats
    """
    store = IndexStore(storage_path)
    repos = store.list_repos()

    return {
        "count": len(repos),
        "repos": repos,
    }
