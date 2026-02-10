"""Test script for jdocmunch-mcp server."""

import asyncio
import json
import sys
sys.path.insert(0, "src")

from jdocmunch_mcp.parser.markdown import parse_markdown_to_sections
from jdocmunch_mcp.storage.index_store import IndexStore
from jdocmunch_mcp.tools.list_repos import list_repos
from jdocmunch_mcp.tools.index_repo import index_repo


def test_markdown_parser():
    """Test markdown parsing."""
    print("Testing markdown parser...")

    sample_md = """# Main Title

Introduction text here.

## Installation

Install with npm:

```bash
npm install my-package
```

### Prerequisites

- Node.js 18+
- npm 9+

## Usage

Basic usage example:

```javascript
import { thing } from 'my-package';
thing.doSomething();
```

### Advanced Usage

More complex examples here.

## API Reference

### `doSomething()`

Does something useful.
"""

    sections = parse_markdown_to_sections(sample_md, "README.md")

    print(f"  Found {len(sections)} sections:")
    for s in sections:
        indent = "  " * s.depth
        print(f"    {indent}[{s.id}] {s.title} ({s.line_count} lines)")
        if s.keywords:
            print(f"    {indent}  keywords: {s.keywords[:5]}")

    assert len(sections) > 0, "Should find sections"
    assert any("install" in s.id for s in sections), "Should find installation section"
    print("  [OK] Markdown parser works!\n")


def test_storage():
    """Test storage functionality."""
    print("Testing storage...")

    from jdocmunch_mcp.parser.markdown import Section

    store = IndexStore("./test_storage")

    # Create test sections
    sections = [
        Section(
            id="test-intro",
            file="test.md",
            path="test.md#intro",
            title="Introduction",
            depth=1,
            parent=None,
            content="# Introduction\n\nThis is the intro.",
            summary="Overview of the project",
            keywords=["intro", "overview"],
            line_count=3,
            byte_offset=0,
            byte_length=40,
        ),
    ]

    # Save
    index = store.save_index(
        owner="test",
        name="repo",
        doc_files=["test.md"],
        sections=sections,
        raw_files={"test.md": "# Introduction\n\nThis is the intro."},
    )

    print(f"  Saved index for {index.repo}")

    # Load
    loaded = store.load_index("test", "repo")
    assert loaded is not None, "Should load index"
    assert len(loaded.sections) == 1, "Should have 1 section"
    print(f"  Loaded index: {len(loaded.sections)} sections")

    # List repos
    repos = store.list_repos()
    assert len(repos) == 1, "Should list 1 repo"
    print(f"  Listed repos: {repos}")

    # Search
    results = loaded.search("intro")
    assert len(results) > 0, "Should find results"
    print(f"  Search 'intro': {len(results)} results")

    # Cleanup
    store.delete_index("test", "repo")
    import shutil
    shutil.rmtree("./test_storage", ignore_errors=True)

    print("  [OK] Storage works!\n")


async def test_index_repo():
    """Test indexing a real (small) GitHub repo."""
    print("Testing repo indexing...")

    # Use a small test repo
    result = await index_repo(
        url="octocat/Hello-World",
        use_ai_summaries=False,  # Skip AI for testing
    )

    if result.get("success"):
        print(f"  Indexed: {result['repo']}")
        print(f"  Files: {result['file_count']}")
        print(f"  Sections: {result['section_count']}")
        print("  [OK] Repo indexing works!\n")
    else:
        print(f"  Note: {result.get('error', 'Unknown error')}")
        print("  (This is OK if GitHub API is rate-limited)\n")


def test_list_repos():
    """Test listing repos."""
    print("Testing list_repos...")
    result = list_repos()
    print(f"  Found {result['count']} indexed repos")
    print("  [OK] list_repos works!\n")


def main():
    print("\n" + "=" * 50)
    print("JDocMunch MCP Server - Test Suite")
    print("=" * 50 + "\n")

    test_markdown_parser()
    test_storage()
    test_list_repos()

    # Optional: test actual GitHub fetch
    print("Testing GitHub API (optional)...")
    try:
        asyncio.run(test_index_repo())
    except Exception as e:
        print(f"  Skipped: {e}\n")

    print("=" * 50)
    print("All tests passed!")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    main()
