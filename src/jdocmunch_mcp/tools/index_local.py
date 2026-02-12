"""Tool to index a local codebase's documentation."""

import hashlib
import logging
import os
import subprocess
from pathlib import Path
from typing import Optional

from ..parser.markdown import parse_markdown_to_sections, Section
from ..security import is_sensitive_filename, scan_content_for_secrets, validate_path_traversal
from ..storage.index_store import IndexStore
from ..summarizer.batch_summarize import BatchSummarizer, summarize_sections_simple

logger = logging.getLogger(__name__)

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
DOC_EXTENSIONS = ('.md', '.markdown', '.mdx', '.rst')


def is_hidden_path(path: Path) -> bool:
    """Check if any component of the path is hidden (starts with .)."""
    return any(part.startswith('.') for part in path.parts)


def _load_gitignore_spec(base_path: Path):
    """Load .gitignore patterns from the base path if available."""
    gitignore_path = base_path / '.gitignore'
    if not gitignore_path.exists():
        return None
    try:
        import pathspec
        with open(gitignore_path, 'r', encoding='utf-8') as f:
            return pathspec.PathSpec.from_lines('gitignore', f)
    except (ImportError, OSError):
        return None


def _compute_file_hash(file_path: Path) -> str:
    """Compute SHA256 hash of a file's content."""
    h = hashlib.sha256()
    try:
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                h.update(chunk)
    except OSError:
        return ''
    return h.hexdigest()


def _get_local_commit_hash(base_path: Path) -> str:
    """Try to get git HEAD commit hash for a local directory."""
    try:
        result = subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
            cwd=str(base_path),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    return ''


def discover_local_doc_files(
    base_path: str,
    max_depth: int = 5,
    include_hidden: bool = False,
    follow_symlinks: bool = False,
    extra_ignore_patterns: Optional[list[str]] = None,
) -> list[str]:
    """
    Discover all markdown documentation files in a local directory.

    Args:
        base_path: Root directory to start crawling from
        max_depth: Maximum directory depth to crawl
        include_hidden: Whether to include hidden directories (starting with .)
        follow_symlinks: Whether to follow symbolic links (default False for safety)
        extra_ignore_patterns: Additional gitignore-style patterns to exclude

    Returns:
        List of relative paths to markdown files
    """
    base = Path(base_path).resolve()
    if not base.exists():
        raise ValueError(f"Path does not exist: {base_path}")
    if not base.is_dir():
        raise ValueError(f"Path is not a directory: {base_path}")

    doc_files: list[str] = []

    # Load .gitignore spec
    gitignore_spec = _load_gitignore_spec(base)

    # Load extra ignore patterns
    extra_spec = None
    if extra_ignore_patterns:
        try:
            import pathspec
            extra_spec = pathspec.PathSpec.from_lines('gitignore', extra_ignore_patterns)
        except ImportError:
            pass

    def should_skip_dir(dir_path: Path) -> bool:
        """Check if a directory should be skipped."""
        name = dir_path.name
        if name in SKIP_DIRS:
            return True
        if not include_hidden and is_hidden_path(dir_path.relative_to(base)):
            return True
        return False

    def is_gitignored(rel_path: str) -> bool:
        """Check if a path is matched by .gitignore or extra patterns."""
        if gitignore_spec and gitignore_spec.match_file(rel_path):
            return True
        if extra_spec and extra_spec.match_file(rel_path):
            return True
        return False

    def crawl_directory(current_path: Path, current_depth: int) -> None:
        """Recursively crawl directory for markdown files."""
        if current_depth > max_depth:
            return

        try:
            for item in current_path.iterdir():
                try:
                    # P1-1: Symlink protection - resolve and validate
                    resolved = item.resolve()
                    if item.is_symlink():
                        if not follow_symlinks:
                            logger.debug("Skipping symlink: %s", item)
                            continue
                        if not validate_path_traversal(resolved, base):
                            logger.warning("Symlink escapes base directory, skipping: %s -> %s", item, resolved)
                            continue

                    if item.is_file():
                        # P1-1: Validate resolved file is within base
                        if not validate_path_traversal(resolved, base):
                            logger.warning("Path traversal detected, skipping: %s", item)
                            continue

                        if item.suffix.lower() in DOC_EXTENSIONS:
                            rel_path = item.relative_to(base).as_posix()

                            # P1-2: Skip sensitive files
                            if is_sensitive_filename(rel_path):
                                logger.info("Skipping sensitive file: %s", rel_path)
                                continue

                            # P1-3: Respect .gitignore
                            if is_gitignored(rel_path):
                                logger.debug("Skipping gitignored file: %s", rel_path)
                                continue

                            doc_files.append(rel_path)

                    elif item.is_dir():
                        # P1-1: Validate resolved directory is within base
                        if not validate_path_traversal(resolved, base):
                            logger.warning("Directory symlink escapes base, skipping: %s", item)
                            continue

                        if not should_skip_dir(item):
                            rel_dir = item.relative_to(base).as_posix()
                            if not is_gitignored(rel_dir + '/'):
                                crawl_directory(item, current_depth + 1)

                except (OSError, PermissionError):
                    continue
        except (OSError, PermissionError):
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
    follow_symlinks: bool = False,
    extra_ignore_patterns: Optional[list[str]] = None,
) -> dict:
    """
    Index a local codebase's documentation.

    Args:
        path: Path to local directory to index
        use_ai_summaries: Whether to use AI for generating summaries
        storage_path: Custom storage path (defaults to ~/.doc-index)
        max_depth: Maximum directory depth to crawl
        include_hidden: Whether to include hidden directories
        follow_symlinks: Whether to follow symbolic links (default False)
        extra_ignore_patterns: Additional gitignore-style patterns to exclude

    Returns:
        Dict with indexing statistics
    """
    # P1-6: Check local-only mode (index_local is allowed, but just check env)
    local_only = os.environ.get('JDOCMUNCH_LOCAL_ONLY', '').lower() in ('true', '1', 'yes')

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
    owner = "local"

    # Discover documentation files
    try:
        doc_files = discover_local_doc_files(
            str(base_path),
            max_depth=max_depth,
            include_hidden=include_hidden,
            follow_symlinks=follow_symlinks,
            extra_ignore_patterns=extra_ignore_patterns,
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

    # P1-4: Compute file hashes and get commit hash
    file_hashes: dict[str, str] = {}
    commit_hash = _get_local_commit_hash(base_path)

    # Read and parse all files
    all_sections: list[Section] = []
    raw_files: dict[str, str] = {}
    skipped_secrets: list[str] = []

    for file_path in doc_files:
        full_path = base_path / file_path
        try:
            content = full_path.read_text(encoding='utf-8', errors='replace')

            # P1-2: Scan content for secrets
            detected = scan_content_for_secrets(content, file_path)
            if detected:
                logger.warning("Secret detected in %s: %s — skipping file", file_path, ', '.join(detected))
                skipped_secrets.append(file_path)
                continue

            raw_files[file_path] = content

            # P1-4: Compute file hash
            file_hashes[file_path] = _compute_file_hash(full_path)

            # Dispatch to correct parser by extension
            ext = Path(file_path).suffix.lower()
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
        except (OSError, UnicodeDecodeError):
            continue

    if not all_sections:
        return {
            "success": False,
            "error": "No sections extracted from documentation",
            "path": str(base_path),
        }

    # Generate summaries
    if use_ai_summaries and not local_only:
        try:
            summarizer = BatchSummarizer()
            all_sections = summarizer.summarize_batch(all_sections)
        except Exception:
            all_sections = summarize_sections_simple(all_sections)
    else:
        # In local-only mode, use simple summaries (no Anthropic API)
        all_sections = summarize_sections_simple(all_sections)

    # Save index
    store = IndexStore(storage_path)
    index = store.save_index(
        owner, repo_name, doc_files, all_sections, raw_files,
        commit_hash=commit_hash,
        file_hashes=file_hashes,
    )

    result = {
        "success": True,
        "repo": f"{owner}/{repo_name}",
        "path": str(base_path),
        "indexed_at": index.indexed_at,
        "file_count": len(doc_files),
        "section_count": len(all_sections),
        "files": doc_files,
        "commit_hash": commit_hash,
    }
    if skipped_secrets:
        result["skipped_secrets"] = skipped_secrets
    return result
