"""Tool to index a GitHub repository's documentation."""

import hashlib
import logging
import os
import re
from typing import Optional

import httpx

from ..parser.markdown import parse_markdown_to_sections, Section
from ..security import is_sensitive_filename, scan_content_for_secrets
from ..storage.index_store import IndexStore
from ..summarizer.batch_summarize import BatchSummarizer, summarize_sections_simple

logger = logging.getLogger(__name__)


def parse_github_url(url: str) -> tuple[str, str]:
    """Extract owner and repo name from GitHub URL."""
    patterns = [
        r"github\.com/([^/]+)/([^/]+)",  # https://github.com/owner/repo
        r"^([^/]+)/([^/]+)$",  # owner/repo
    ]

    for pattern in patterns:
        match = re.search(pattern, url.strip().rstrip('/'))
        if match:
            owner = match.group(1)
            repo = match.group(2)
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


async def _fetch_commit_sha(
    owner: str,
    repo: str,
    token: Optional[str] = None,
) -> str:
    """Fetch the HEAD commit SHA from GitHub API."""
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "jdocmunch-mcp",
    }
    if token:
        headers["Authorization"] = f"token {token}"

    url = f"https://api.github.com/repos/{owner}/{repo}/commits/HEAD"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                return data.get("sha", "")
    except Exception:
        pass
    return ""


async def discover_doc_files(
    owner: str,
    repo: str,
    token: Optional[str] = None,
) -> tuple[list[str], dict[str, str]]:
    """
    Discover all markdown files in the entire repository using the Git Trees API.

    Returns:
        Tuple of (doc_files list, blob_shas dict mapping path to git blob SHA)
    """
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "jdocmunch-mcp",
    }
    if token:
        headers["Authorization"] = f"token {token}"

    doc_extensions = (".md", ".markdown", ".mdx", ".rst")

    url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/HEAD?recursive=1"

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        if response.status_code == 404:
            return [], {}
        response.raise_for_status()
        data = response.json()

    doc_files: list[str] = []
    blob_shas: dict[str, str] = {}
    for item in data.get("tree", []):
        if item["type"] == "blob" and item["path"].lower().endswith(doc_extensions):
            path = item["path"]

            # P1-2: Skip sensitive files
            if is_sensitive_filename(path):
                logger.info("Skipping sensitive file: %s", path)
                continue

            doc_files.append(path)
            blob_shas[path] = item.get("sha", "")

    doc_files.sort()
    return doc_files, blob_shas


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
    # P1-6: Block remote indexing in local-only mode
    local_only = os.environ.get('JDOCMUNCH_LOCAL_ONLY', '').lower() in ('true', '1', 'yes')
    if local_only:
        return {
            "success": False,
            "error": "Remote indexing disabled in local-only mode. Set JDOCMUNCH_LOCAL_ONLY=false or unset to enable.",
        }

    # Parse URL
    owner, repo = parse_github_url(url)

    # Get token from env if not provided
    token = github_token or os.environ.get("GITHUB_TOKEN")

    # Discover documentation files (now also returns blob SHAs)
    doc_files, blob_shas = await discover_doc_files(owner, repo, token)

    if not doc_files:
        return {
            "success": False,
            "error": "No documentation files found",
            "repo": f"{owner}/{repo}",
        }

    # P1-4: Fetch commit SHA
    commit_hash = await _fetch_commit_sha(owner, repo, token)

    # Fetch and parse all files
    all_sections: list[Section] = []
    raw_files: dict[str, str] = {}
    file_hashes: dict[str, str] = {}
    skipped_secrets: list[str] = []

    for file_path in doc_files:
        try:
            content = await fetch_file_content(owner, repo, file_path, token)

            # P1-2: Scan content for secrets
            detected = scan_content_for_secrets(content, file_path)
            if detected:
                logger.warning("Secret detected in %s: %s — skipping file", file_path, ', '.join(detected))
                skipped_secrets.append(file_path)
                continue

            raw_files[file_path] = content

            # Use blob SHA from git tree as file hash (more efficient than re-hashing)
            file_hashes[file_path] = blob_shas.get(file_path, hashlib.sha256(content.encode()).hexdigest())

            # Dispatch to correct parser by extension
            from pathlib import Path as _Path
            ext = _Path(file_path).suffix.lower()
            if ext == '.rst':
                from ..parser.rst import parse_rst_to_sections
                sections = parse_rst_to_sections(content, file_path)
            elif ext == '.mdx':
                from ..parser.markdown import preprocess_mdx
                processed = preprocess_mdx(content)
                sections = parse_markdown_to_sections(processed, file_path)
            else:
                sections = parse_markdown_to_sections(content, file_path)
            all_sections.extend(sections)
        except Exception:
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
            all_sections = summarize_sections_simple(all_sections)
    else:
        all_sections = summarize_sections_simple(all_sections)

    # Save index
    store = IndexStore(storage_path)
    index = store.save_index(
        owner, repo, doc_files, all_sections, raw_files,
        commit_hash=commit_hash,
        file_hashes=file_hashes,
    )

    result = {
        "success": True,
        "repo": f"{owner}/{repo}",
        "indexed_at": index.indexed_at,
        "file_count": len(doc_files),
        "section_count": len(all_sections),
        "files": doc_files,
        "commit_hash": commit_hash,
    }
    if skipped_secrets:
        result["skipped_secrets"] = skipped_secrets
    return result
