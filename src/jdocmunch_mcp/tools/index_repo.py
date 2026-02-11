"""Tool to index a GitHub repository's documentation."""

import re
import os
from typing import Optional
import httpx

from ..parser.markdown import parse_markdown_to_sections, Section
from ..storage.index_store import IndexStore
from ..summarizer.batch_summarize import BatchSummarizer, summarize_sections_simple


def parse_github_url(url: str) -> tuple[str, str]:
    """Extract owner and repo name from GitHub URL."""
    # Handle various GitHub URL formats
    patterns = [
        r"github\.com/([^/]+)/([^/]+)",  # https://github.com/owner/repo
        r"^([^/]+)/([^/]+)$",  # owner/repo
    ]

    for pattern in patterns:
        match = re.search(pattern, url.strip().rstrip('/'))
        if match:
            owner = match.group(1)
            repo = match.group(2)
            # Clean up repo name (remove .git suffix)
            repo = repo.replace('.git', '')
            return owner, repo

    raise ValueError(f"Could not parse GitHub URL: {url}")


async def fetch_file_content(
    owner: str,
    repo: str,
    path: str,
    token: Optional[str] = None,
) -> str:
    """Fetch raw content of a file from GitHub."""
    headers = {
        "Accept": "application/vnd.github.v3.raw",
        "User-Agent": "jdocmunch-mcp",
    }
    if token:
        headers["Authorization"] = f"token {token}"

    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        return response.text


async def discover_doc_files(
    owner: str,
    repo: str,
    token: Optional[str] = None,
) -> list[str]:
    """Discover all markdown files in the entire repository using the Git Trees API."""
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "jdocmunch-mcp",
    }
    if token:
        headers["Authorization"] = f"token {token}"

    doc_extensions = (".md", ".markdown")

    # Use the Git Trees API with recursive flag to get the full file tree in one call
    url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/HEAD?recursive=1"

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        if response.status_code == 404:
            return []
        response.raise_for_status()
        data = response.json()

    doc_files: list[str] = []
    for item in data.get("tree", []):
        if item["type"] == "blob" and item["path"].lower().endswith(doc_extensions):
            doc_files.append(item["path"])

    doc_files.sort()
    return doc_files


async def index_repo(
    url: str,
    use_ai_summaries: bool = True,
    github_token: Optional[str] = None,
    storage_path: Optional[str] = None,
) -> dict:
    """
    Index a GitHub repository's documentation.

    Args:
        url: GitHub repository URL or owner/repo string
        use_ai_summaries: Whether to use AI for generating summaries
        github_token: GitHub personal access token (for private repos)
        storage_path: Custom storage path (defaults to ~/.doc-index)

    Returns:
        Dict with indexing statistics
    """
    # Parse URL
    owner, repo = parse_github_url(url)

    # Get token from env if not provided
    token = github_token or os.environ.get("GITHUB_TOKEN")

    # Discover documentation files
    doc_files = await discover_doc_files(owner, repo, token)

    if not doc_files:
        return {
            "success": False,
            "error": "No documentation files found",
            "repo": f"{owner}/{repo}",
        }

    # Fetch and parse all files
    all_sections: list[Section] = []
    raw_files: dict[str, str] = {}

    for file_path in doc_files:
        try:
            content = await fetch_file_content(owner, repo, file_path, token)
            raw_files[file_path] = content
            sections = parse_markdown_to_sections(content, file_path)
            all_sections.extend(sections)
        except Exception as e:
            # Skip files that fail to fetch
            continue

    if not all_sections:
        return {
            "success": False,
            "error": "No sections extracted from documentation",
            "repo": f"{owner}/{repo}",
        }

    # Generate summaries
    if use_ai_summaries:
        try:
            summarizer = BatchSummarizer()
            all_sections = summarizer.summarize_batch(all_sections)
        except Exception:
            # Fallback to simple summaries
            all_sections = summarize_sections_simple(all_sections)
    else:
        all_sections = summarize_sections_simple(all_sections)

    # Save index
    store = IndexStore(storage_path)
    index = store.save_index(owner, repo, doc_files, all_sections, raw_files)

    return {
        "success": True,
        "repo": f"{owner}/{repo}",
        "indexed_at": index.indexed_at,
        "file_count": len(doc_files),
        "section_count": len(all_sections),
        "files": doc_files,
    }
