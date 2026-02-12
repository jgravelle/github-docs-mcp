"""MCP Server for token-efficient GitHub documentation Q&A."""

import asyncio
import json
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from .tools.index_repo import index_repo as do_index_repo, parse_github_url
from .tools.index_local import index_local as do_index_local
from .tools.list_repos import list_repos as do_list_repos
from .tools.get_toc import (
    get_toc as do_get_toc,
    get_toc_tree as do_get_toc_tree,
    get_document_outline as do_get_document_outline,
)
from .tools.get_section import get_section as do_get_section, get_sections as do_get_sections
from .tools.search_sections import search_sections as do_search_sections
from .storage.index_store import IndexStore


# Create MCP server
server = Server("jdocmunch-mcp")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="index_repo",
            description="""Index a GitHub repository's documentation for efficient querying.

This searches the entire repository tree for all documentation files
(.md, .markdown, .mdx, .rst) and preprocesses them into a searchable
index with section summaries. Run this once per repository before using
other tools.

Supports:
- Public repositories (no token needed)
- Private repositories (set GITHUB_TOKEN environment variable)
- Various URL formats: https://github.com/owner/repo, owner/repo
- Blocked in local-only mode (JDOCMUNCH_LOCAL_ONLY=true)""",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "GitHub repository URL or owner/repo string",
                    },
                    "use_ai_summaries": {
                        "type": "boolean",
                        "description": "Use AI to generate section summaries (requires ANTHROPIC_API_KEY)",
                        "default": True,
                    },
                },
                "required": ["url"],
            },
        ),
        Tool(
            name="index_local",
            description="""Index a local directory's documentation for efficient querying.

This crawls a local directory tree for all documentation files
(.md, .markdown, .mdx, .rst) and preprocesses them into a searchable
index with section summaries. Run this once per directory before using
other tools.

Features:
- Respects .gitignore rules
- Skips sensitive files (.env, credentials.json, *.pem, etc.)
- Scans content for secrets (AWS keys, API tokens, private keys)
- Symlink-safe (does not follow symlinks by default)
- Tracks git commit hash and file hashes for incremental reindexing""",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to local directory to index",
                    },
                    "use_ai_summaries": {
                        "type": "boolean",
                        "description": "Use AI to generate section summaries (requires ANTHROPIC_API_KEY or Ollama)",
                        "default": True,
                    },
                    "max_depth": {
                        "type": "integer",
                        "description": "Maximum directory depth to crawl (default: 5)",
                        "default": 5,
                    },
                    "include_hidden": {
                        "type": "boolean",
                        "description": "Whether to include hidden directories (starting with .)",
                        "default": False,
                    },
                    "follow_symlinks": {
                        "type": "boolean",
                        "description": "Whether to follow symbolic links (default: false for safety)",
                        "default": False,
                    },
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="list_repos",
            description="""List all indexed repositories.

Returns repository names, indexing timestamps, section counts,
index version, and commit hashes.
Use this to see what documentation is available for querying.""",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="get_toc",
            description="""Get the table of contents for a repository's documentation.

Returns section titles, summaries, and hierarchy. This is the primary navigation
tool - use it to understand documentation structure before loading full sections.

Supports filtering by path prefix, max depth, and file glob pattern.

Token-efficient: Returns ~500-1500 tokens even for large documentation sets.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Repository identifier (owner/repo or just repo name)",
                    },
                    "include_summaries": {
                        "type": "boolean",
                        "description": "Include one-line summaries for each section",
                        "default": True,
                    },
                    "path_prefix": {
                        "type": "string",
                        "description": "Only include sections from files starting with this prefix (e.g. 'docs/api/')",
                    },
                    "max_depth": {
                        "type": "integer",
                        "description": "Only include sections with heading depth <= this value",
                    },
                    "file_pattern": {
                        "type": "string",
                        "description": "Glob pattern to filter files (e.g. 'docs/*.md')",
                    },
                },
                "required": ["repo"],
            },
        ),
        Tool(
            name="get_toc_tree",
            description="""Get the table of contents as a nested tree structure.

Returns sections organized hierarchically by their header levels.
Useful for understanding the documentation structure at a glance.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Repository identifier (owner/repo or just repo name)",
                    },
                },
                "required": ["repo"],
            },
        ),
        Tool(
            name="get_document_outline",
            description="""Get the hierarchical outline of a single file.

Returns the section structure for one specific file as a nested tree.
Useful for navigating within a large document.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Repository identifier (owner/repo or just repo name)",
                    },
                    "file_path": {
                        "type": "string",
                        "description": "Path of the file within the repo (e.g. 'docs/guide.md')",
                    },
                },
                "required": ["repo", "file_path"],
            },
        ),
        Tool(
            name="get_section",
            description="""Get the full content of a specific documentation section.

Use this after identifying relevant sections via get_toc or search_sections.
Returns only the requested section's content, not the entire document.

Token-efficient: Returns only the specific section (~200-2000 tokens typically).""",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Repository identifier (owner/repo or just repo name)",
                    },
                    "section_id": {
                        "type": "string",
                        "description": "Section ID from get_toc or search_sections",
                    },
                },
                "required": ["repo", "section_id"],
            },
        ),
        Tool(
            name="get_sections",
            description="""Get the full content of multiple sections at once.

Efficient batch retrieval when you need several related sections.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Repository identifier (owner/repo or just repo name)",
                    },
                    "section_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of section IDs to retrieve",
                    },
                },
                "required": ["repo", "section_ids"],
            },
        ),
        Tool(
            name="search_sections",
            description="""Search for sections matching a query.

Searches section titles, keywords, and summaries. Returns matching section IDs
and summaries without loading full content.

Supports filtering by path prefix, max depth, and file glob pattern.

Token-efficient: Returns ~200-500 tokens for search results.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Repository identifier (owner/repo or just repo name)",
                    },
                    "query": {
                        "type": "string",
                        "description": "Search query (matches titles, keywords, summaries)",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 10,
                    },
                    "path_prefix": {
                        "type": "string",
                        "description": "Only search sections from files starting with this prefix",
                    },
                    "max_depth": {
                        "type": "integer",
                        "description": "Only search sections with heading depth <= this value",
                    },
                    "file_pattern": {
                        "type": "string",
                        "description": "Glob pattern to filter files (e.g. 'docs/*.md')",
                    },
                },
                "required": ["repo", "query"],
            },
        ),
        Tool(
            name="delete_index",
            description="""Delete a repository's cached index and content files.

Use this to free disk space or force a full re-index on next use.
This is irreversible — the repository will need to be re-indexed.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Repository identifier (owner/repo or just repo name)",
                    },
                },
                "required": ["repo"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""
    try:
        if name == "index_repo":
            result = await do_index_repo(
                url=arguments["url"],
                use_ai_summaries=arguments.get("use_ai_summaries", True),
            )
        elif name == "index_local":
            result = await do_index_local(
                path=arguments["path"],
                use_ai_summaries=arguments.get("use_ai_summaries", True),
                max_depth=arguments.get("max_depth", 5),
                include_hidden=arguments.get("include_hidden", False),
                follow_symlinks=arguments.get("follow_symlinks", False),
            )
        elif name == "list_repos":
            result = do_list_repos()
        elif name == "get_toc":
            result = do_get_toc(
                repo=arguments["repo"],
                include_summaries=arguments.get("include_summaries", True),
                path_prefix=arguments.get("path_prefix"),
                max_depth=arguments.get("max_depth"),
                file_pattern=arguments.get("file_pattern"),
            )
        elif name == "get_toc_tree":
            result = do_get_toc_tree(repo=arguments["repo"])
        elif name == "get_document_outline":
            result = do_get_document_outline(
                repo=arguments["repo"],
                file_path=arguments["file_path"],
            )
        elif name == "get_section":
            result = do_get_section(
                repo=arguments["repo"],
                section_id=arguments["section_id"],
            )
        elif name == "get_sections":
            result = do_get_sections(
                repo=arguments["repo"],
                section_ids=arguments["section_ids"],
            )
        elif name == "search_sections":
            result = do_search_sections(
                repo=arguments["repo"],
                query=arguments["query"],
                max_results=arguments.get("max_results", 10),
                path_prefix=arguments.get("path_prefix"),
                max_depth=arguments.get("max_depth"),
                file_pattern=arguments.get("file_pattern"),
            )
        elif name == "delete_index":
            result = _handle_delete_index(arguments["repo"])
        else:
            result = {"error": f"Unknown tool: {name}"}

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        error_result = {"error": str(e)}
        return [TextContent(type="text", text=json.dumps(error_result, indent=2))]


def _handle_delete_index(repo: str) -> dict:
    """Handle delete_index tool call."""
    store = IndexStore()

    if "/" in repo:
        owner, name = repo.split("/", 1)
    else:
        repos = store.list_repos()
        matching = [r for r in repos if r["repo"].endswith(f"/{repo}")]
        if not matching:
            return {"error": f"Repository not found: {repo}"}
        owner, name = matching[0]["repo"].split("/", 1)

    deleted = store.delete_index(owner, name)
    if deleted:
        return {"success": True, "message": f"Index deleted for {owner}/{name}"}
    else:
        return {"success": False, "error": f"No index found for {owner}/{name}"}


async def run_server():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def main():
    """Entry point for the MCP server."""
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
