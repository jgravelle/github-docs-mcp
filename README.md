
# jDocMunch MCP
## Precision Documentation Intelligence for AI Agents

![License](https://img.shields.io/badge/license-MIT-blue)
![MCP](https://img.shields.io/badge/MCP-compatible-purple)
![Local-first](https://img.shields.io/badge/local--first-yes-brightgreen)

**Stop loading entire documentation sets. Start retrieving exactly what you need.**

jDocMunch MCP transforms large documentation repositories into a structured, queryable intelligence layer for AI agents. Instead of fetching hundreds of files per query, agents retrieve only the relevant documentation sections — dramatically reducing token cost, latency, and API calls.

> **Part of the Munch Trio** — see [The Munch Trio](#the-munch-trio) below for the full ecosystem including code indexing and unified orchestration.

---

## Architecture

```
MCP Client (Claude Desktop, OpenClaw, etc.)
    |
    v
+-----------------------------------+
|  jDocMunch MCP Server              |
|                                    |
|  Tools:                            |
|    index_repo / index_local        |
|    get_toc / get_toc_tree          |
|    get_document_outline            |
|    search_sections                 |
|    get_section / get_sections      |
|    list_repos / delete_index       |
|                                    |
|  +----------+  +---------------+   |
|  | Parser   |  | Summarizer    |   |
|  | md/mdx   |  | Anthropic API |   |
|  | rst      |  | Ollama (local)|   |
|  +----------+  +---------------+   |
|        |                           |
|  +----------+                      |
|  | Storage  | (~/.doc-index/)      |
|  | JSON idx |                      |
|  | raw files|                      |
|  +----------+                      |
+-----------------------------------+
    |                |
    v                v
GitHub API      Local Filesystem
```

---

## Why jDocMunch Exists

Large documentation repositories often contain hundreds or thousands of files. Traditional AI workflows repeatedly load entire documentation sets for each query, creating:

- Massive token waste
- Slow responses
- Rate-limit bottlenecks
- High operational cost

jDocMunch solves this by indexing documentation once and enabling precision retrieval for every subsequent query.

---

## Proven Real-World Benchmark

**Repository:** openclaw/openclaw
**Documentation size:** 583 files (~812K tokens)

### Cost Breakdown

| Phase | Tokens | Frequency |
|-------|--------|-----------|
| **Indexing (one-time)** | ~708K | Once per repo |
| **Per-query (cached)** | ~500 | Every subsequent query |
| **Incremental reindex** | Varies | Only changed files |

### Session Results

| Query | Without MCP | With MCP | Savings |
|------|-------------|----------|---------|
| 1st query | 811,756 tokens | 708,794 tokens | 12.7% |
| 2nd query | 811,756 tokens | 534 tokens | 99.9% |
| 3rd query | 811,756 tokens | 542 tokens | 99.9% |

**Session Total:**
- Without MCP: 2,435,268 tokens + 1,752 API calls
- With MCP: 709,870 tokens + 0 API calls
- **Savings:** 70.9%

---

## Scale Economics

| Monthly Queries | Without MCP | With MCP | Savings |
|-----------------|------------|----------|---------|
| 20 queries | 16M tokens | 716K tokens | 95.6% |
| 100 queries | 81M tokens | 741K tokens | 99.1% |
| 1,000 queries | 812M tokens | 1.2M tokens | 99.8% |

As query volume increases, cost savings approach **two orders of magnitude**.

---

## Installation

### Prerequisites

- **Python 3.10+**
- **pip** (or any Python package manager)

### Install

```bash
pip install git+https://github.com/jgravelle/jdocmunch-mcp.git
```

Verify:

```bash
jdocmunch-mcp --help 2>&1 | head -1   # should not error
```

### Configure MCP Client

#### Claude Code / Claude Desktop (claude_desktop_config.json)

**macOS/Linux** — `~/.config/claude/claude_desktop_config.json`
**Windows** — `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "jdocmunch": {
      "command": "jdocmunch-mcp",
      "env": {
        "GITHUB_TOKEN": "ghp_...",
        "ANTHROPIC_API_KEY": "sk-ant-..."
      }
    }
  }
}
```

Both env vars are optional:
- **GITHUB_TOKEN** — enables private repos + higher GitHub API rate limits
- **ANTHROPIC_API_KEY** — enables AI-generated section summaries (falls back to keyword extraction without it)

#### Other MCP clients

Any MCP client that supports stdio transport can use jdocmunch-mcp. Point it at the `jdocmunch-mcp` command with the environment variables above.

### Verify

Once configured, ask your MCP client to list tools. You should see 8 tools.

---

## Quickstart

### Example Session

```
1. index_local(path="/path/to/my/project")
   -> Indexes 50 markdown files, 200 sections

2. get_toc(repo="my-project")
   -> Returns structured TOC with summaries (~800 tokens)

3. search_sections(repo="my-project", query="authentication setup")
   -> Returns 5 matching sections with summaries (~300 tokens)

4. get_section(repo="my-project", section_id="readme-authentication")
   -> Returns exact section content (~500 tokens)
```

### Tool Reference

```
index_repo:        { "url": "owner/repo" }
index_local:       { "path": "/path/to/docs" }

get_toc:           { "repo": "owner/repo" }
get_toc_tree:      { "repo": "owner/repo" }
search_sections:   { "repo": "owner/repo", "query": "authentication" }
get_section:       { "repo": "owner/repo", "section_id": "readme-md--installation" }
get_sections:      { "repo": "owner/repo", "section_ids": ["readme-md--installation", "docs/api-md--endpoints"] }
```

---

## Tools (8)

| Tool | Purpose |
|------|---------|
| `index_repo` | Index a GitHub repository's documentation |
| `index_local` | Index a local directory's documentation |
| `list_repos` | List all indexed repositories |
| `get_toc` | Get table of contents with section summaries |
| `get_toc_tree` | Get table of contents as nested tree structure |
| `get_section` | Get full content of a specific section |
| `get_sections` | Batch retrieve multiple sections |
| `search_sections` | Search sections by title, keywords, and summaries |

---

## Features

- **Multi-format support**: Markdown (.md), MDX (.mdx), reStructuredText (.rst)
- **Security hardened**: symlink protection, secret detection, .gitignore respect
- **Incremental reindexing**: only re-parses changed files
- **Local-only mode**: `JDOCMUNCH_LOCAL_ONLY=true` for air-gapped environments
- **AI summaries**: via Anthropic API or local Ollama
- **Cache versioning**: automatic invalidation on schema changes

---

## Key Benefits

- 70-99% token reduction in real workflows
- Near-instant documentation queries
- Zero repeated API calls after indexing
- Ideal for multi-agent systems and autonomous workflows
- Works with any local or cloned repository

---

## How It Works

1. Index documentation once (supports GitHub repos and local directories)
2. Build a structured Table-of-Contents index with AI summaries
3. Cache locally (~100KB-1MB per repo)
4. Serve precision MCP queries for agents
5. Retrieve only the relevant documentation fragments

After indexing, queries typically consume **~500 tokens instead of hundreds of thousands**.

---

## Environment Variables

| Variable | Purpose | Required |
|----------|---------|----------|
| `GITHUB_TOKEN` | GitHub API auth (higher rate limits, private repos) | No |
| `ANTHROPIC_API_KEY` | AI-powered section summarization | No |
| `JDOCMUNCH_LOCAL_ONLY` | Disable GitHub fetching for air-gapped environments | No |

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| Rate limits on GitHub API | No token configured | Set `GITHUB_TOKEN` for higher limits |
| Summaries are generic keywords only | No API key configured | Set `ANTHROPIC_API_KEY` for AI summaries |
| `jdocmunch-mcp` command not found | Package not installed or not on PATH | Re-run `pip install` and check `which jdocmunch-mcp` |
| Index seems stale | Documentation changed since indexing | Re-run `index_repo` or `index_local` |

---

## The Munch Trio

jDocMunch is part of a three-package ecosystem for giving AI agents structured access to both code and documentation:

| Package | Purpose | Repo |
|---------|---------|------|
| [jcodemunch-mcp](https://github.com/jgravelle/jcodemunch-mcp) | Token-efficient code symbol indexing via tree-sitter AST parsing | 11 tools |
| **jdocmunch-mcp** (this repo) | Token-efficient documentation section indexing | 8 tools |
| [jcontextmunch-mcp](https://github.com/jgravelle/jcontextmunch-mcp) | Unified orchestration — hybrid search, context assembly, cross-references | 9 tools |

**Using all three?** You only need to configure [jcontextmunch-mcp](https://github.com/jgravelle/jcontextmunch-mcp) in your MCP client — it spawns jcodemunch-mcp and jdocmunch-mcp as subprocesses automatically. See the [jcontextmunch-mcp installation guide](https://github.com/jgravelle/jcontextmunch-mcp#full-installation-guide) for details.

---

## Documentation

- [USER_GUIDE.md](USER_GUIDE.md) — Comprehensive usage guide
- [SECURITY.md](SECURITY.md) — Threat model, secret handling, access controls
- [CACHE_SPEC.md](CACHE_SPEC.md) — Cache schema, versioning, invalidation
- [TOKEN_COMPARISON.md](TOKEN_COMPARISON.md) — Detailed token usage analysis
- [TOKEN_SAVINGS_COMPARISON.md](TOKEN_SAVINGS_COMPARISON.md) — Cost impact analysis

---

## Vision

jDocMunch provides the **documentation intelligence layer** for the agent era — enabling autonomous systems to reason over large knowledge bases efficiently, cheaply, and reliably.

---

## License
MIT
