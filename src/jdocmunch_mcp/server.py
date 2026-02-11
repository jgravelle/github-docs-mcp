"""MCP Server for token-efficient GitHub documentation Q&A."""

import asyncio
import json
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from .tools.index_repo import index_repo as do_index_repo
from .tools.index_local import index_local as do_index_local
from .tools.list_repos import list_repos as do_list_repos
from .tools.get_toc import get_toc as do_get_toc, get_toc_tree as do_get_toc_tree
from .tools.get_section import get_section as do_get_section, get_sections as do_get_sections
from .tools.search_sections import search_sections as do_search_sections


# Create MCP server
server = Server("jdocmunch-mcp")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="index_repo",
            description="""Index a GitHub repository's documentation for efficient querying.

This searches the entire repository tree for all markdown files (.md, .markdown)
and preprocesses them into a searchable index with section summaries.
Run this once per repository before using other tools.

Supports:
- Public repositories (no token needed)
- Private repositories (set GITHUB_TOKEN environment variable)
- Various URL formats: https://github.com/owner/repo, owner/repo""",
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

This crawls a local directory tree for all markdown files (.md, .markdown)
and preprocesses them into a searchable index with section summaries.
Run this once per directory before using other tools.

Automatically skips common non-documentation directories like .git,
node_modules, __pycache__, venv, dist, build, etc.""",
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
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="list_repos",
            description="""List all indexed repositories.

Returns repository names, indexing timestamps, and section counts.
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

Use this when you know what topic you're looking for but don't know which section
contains it. Then use get_section to load the relevant content.

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
                },
                "required": ["repo", "query"],
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
            )
        elif name == "list_repos":
            result = do_list_repos()
        elif name == "get_toc":
            result = do_get_toc(
                repo=arguments["repo"],
                include_summaries=arguments.get("include_summaries", True),
            )
        elif name == "get_toc_tree":
            result = do_get_toc_tree(repo=arguments["repo"])
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
            )
        else:
            result = {"error": f"Unknown tool: {name}"}

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        error_result = {"error": str(e)}
        return [TextContent(type="text", text=json.dumps(error_result, indent=2))]


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
