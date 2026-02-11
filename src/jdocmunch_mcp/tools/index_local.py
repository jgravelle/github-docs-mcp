"""Tool to index a local codebase's documentation."""

import os
from pathlib import Path
from typing import Optional

from ..parser.markdown import parse_markdown_to_sections, Section
from ..storage.index_store import IndexStore
from ..summarizer.batch_summarize import BatchSummarizer, summarize_sections_simple


# Directories to skip during crawling
SKIP_DIRS = {
    '.git',
    'node_modules',
    '__pycache__',
    '.venv',
    'venv',
    '.env',
    'env',
    'dist',
    'build',
    'target',
    '.idea',
    '.vscode',
    '.pytest_cache',
    '.mypy_cache',
    '.tox',
    'coverage',
    'htmlcov',
    '.coverage',
    '.next',
    'out',
    'public',
    'vendor',
    'bin',
    'obj',
}

# File patterns to consider as documentation
DOC_EXTENSIONS = ('.md', '.markdown')


def is_hidden_path(path: Path) -> bool:
    """Check if any component of the path is hidden (starts with .)."""
    return any(part.startswith('.') for part in path.parts)


def discover_local_doc_files(
    base_path: str,
    max_depth: int = 5,
    include_hidden: bool = False,
) -> list[str]:
    """
    Discover all markdown documentation files in a local directory.

    Args:
        base_path: Root directory to start crawling from
        max_depth: Maximum directory depth to crawl
        include_hidden: Whether to include hidden directories (starting with .)

    Returns:
        List of relative paths to markdown files
    """
    base = Path(base_path).resolve()
    if not base.exists():
        raise ValueError(f"Path does not exist: {base_path}")
    if not base.is_dir():
        raise ValueError(f"Path is not a directory: {base_path}")

    doc_files: list[str] = []

    def should_skip_dir(dir_path: Path) -> bool:
        """Check if a directory should be skipped."""
        name = dir_path.name
        if name in SKIP_DIRS:
            return True
        if not include_hidden and is_hidden_path(dir_path.relative_to(base)):
            return True
        return False

    def crawl_directory(current_path: Path, current_depth: int) -> None:
        """Recursively crawl directory for markdown files."""
        if current_depth > max_depth:
            return

        try:
            for item in current_path.iterdir():
                try:
                    if item.is_file() and item.suffix.lower() in DOC_EXTENSIONS:
                        # Store relative path from base
                        rel_path = item.relative_to(base).as_posix()
                        doc_files.append(rel_path)
                    elif item.is_dir() and not should_skip_dir(item):
                        crawl_directory(item, current_depth + 1)
                except (OSError, PermissionError):
                    # Skip items we can't access
                    continue
        except (OSError, PermissionError):
            # Skip directories we can't access
            pass

    crawl_directory(base, 0)

    # Sort for consistent ordering
    doc_files.sort()
    return doc_files


def parse_local_repo_name(base_path: str) -> str:
    """Generate a repo identifier from a local path."""
    path = Path(base_path).resolve()
    # Use the directory name as the repo name
    return path.name


async def index_local(
    path: str,
    use_ai_summaries: bool = True,
    storage_path: Optional[str] = None,
    max_depth: int = 5,
    include_hidden: bool = False,
) -> dict:
    """
    Index a local codebase's documentation.

    Args:
        path: Path to local directory to index
        use_ai_summaries: Whether to use AI for generating summaries
        storage_path: Custom storage path (defaults to ~/.doc-index)
        max_depth: Maximum directory depth to crawl
        include_hidden: Whether to include hidden directories

    Returns:
        Dict with indexing statistics
    """
    base_path = Path(path).resolve()

    # Validate path
    if not base_path.exists():
        return {
            "success": False,
            "error": f"Path does not exist: {path}",
            "path": str(base_path),
        }

    if not base_path.is_dir():
        return {
            "success": False,
            "error": f"Path is not a directory: {path}",
            "path": str(base_path),
        }

    # Generate repo identifier
    repo_name = parse_local_repo_name(path)
    # Use 'local' as the owner for local paths
    owner = "local"

    # Discover documentation files
    try:
        doc_files = discover_local_doc_files(
            str(base_path),
            max_depth=max_depth,
            include_hidden=include_hidden,
        )
    except ValueError as e:
        return {
            "success": False,
            "error": str(e),
            "path": str(base_path),
        }

    if not doc_files:
        return {
            "success": False,
            "error": "No documentation files found",
            "path": str(base_path),
            "searched_depth": max_depth,
        }

    # Read and parse all files
    all_sections: list[Section] = []
    raw_files: dict[str, str] = {}

    for file_path in doc_files:
        full_path = base_path / file_path
        try:
            content = full_path.read_text(encoding='utf-8', errors='replace')
            raw_files[file_path] = content
            sections = parse_markdown_to_sections(content, file_path)
            all_sections.extend(sections)
        except (OSError, UnicodeDecodeError) as e:
            # Skip files that fail to read
            continue

    if not all_sections:
        return {
            "success": False,
            "error": "No sections extracted from documentation",
            "path": str(base_path),
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
    index = store.save_index(owner, repo_name, doc_files, all_sections, raw_files)

    return {
        "success": True,
        "repo": f"{owner}/{repo_name}",
        "path": str(base_path),
        "indexed_at": index.indexed_at,
        "file_count": len(doc_files),
        "section_count": len(all_sections),
        "files": doc_files,
    }
