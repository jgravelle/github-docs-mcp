# GitHub Docs MCP Server

A token-efficient MCP server for Q&A about any GitHub repository's documentation.

## Features

- **Pre-processes documentation** into a hierarchical index with summaries
- **Lazy-loading** of only relevant sections
- **Efficient navigation** with table of contents and search
- **AI-powered summaries** for quick scanning (optional)

## Installation

```bash
cd github-docs-mcp
pip install -e .
```

### Dependencies

- Python 3.10+
- `mcp` - MCP server framework
- `mistune` - Markdown parsing
- `httpx` - GitHub API access
- `anthropic` - AI summary generation (optional)

## Usage

### As an MCP Server

Add to your Claude Code MCP configuration:

```json
{
  "mcpServers": {
    "github-docs": {
      "command": "python",
      "args": ["-m", "github_docs_mcp.server"],
      "cwd": "/path/to/github-docs-mcp/src"
    }
  }
}
```

Or if installed:

```json
{
  "mcpServers": {
    "github-docs": {
      "command": "github-docs-mcp"
    }
  }
}
```

### Environment Variables

- `GITHUB_TOKEN` - GitHub personal access token (required for private repos)
- `ANTHROPIC_API_KEY` - Anthropic API key (required for AI summaries)

## Tools

| Tool | Description | Token Cost |
|------|-------------|------------|
| `index_repo` | Index a repository's documentation | N/A (setup) |
| `list_repos` | List indexed repositories | ~50 tokens |
| `get_toc` | Get table of contents with summaries | ~500-1500 tokens |
| `get_section` | Get a specific section's content | ~200-2000 tokens |
| `search_sections` | Search for sections by query | ~200-500 tokens |

## Workflow Example

```
User: "How do I set up OAuth in anthropics/claude-code?"

Agent:
1. index_repo("anthropics/claude-code")  # One-time setup
2. get_toc("anthropics/claude-code")     # See all sections
3. search_sections("claude-code", "oauth")  # Find OAuth section
4. get_section("claude-code", "docs-auth-oauth")  # Load just that section
5. Answer user's question from focused content

Total tokens: ~1800 (vs ~50,000 if loading full docs)
```

## Storage

Indexes are stored in `~/.doc-index/`:

```
~/.doc-index/
├── owner-repo.json          # Index with summaries
└── owner-repo/              # Raw documentation files
    ├── README.md
    └── docs/
        └── ...
```

## Architecture

```
┌─────────────────┐     ┌──────────────────────────────────────┐
│  Claude Client  │────▶│           MCP Server                 │
│  (Claude Code)  │◀────│                                      │
└─────────────────┘     │  Tools:                              │
                        │  ├─ index_repo(url)                  │
                        │  ├─ list_repos()                     │
                        │  ├─ get_toc(repo)      ◀── small!    │
                        │  ├─ get_section(repo, path)          │
                        │  └─ search_sections(repo, query)     │
                        └──────────────────────────────────────┘
```

## License

MIT
