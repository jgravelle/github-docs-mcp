# JDocMunch MCP Server — User Guide

**Your complete guide to querying documentation with dramatically improved token efficiency.**

---

## Table of Contents

1. Introduction
2. Getting Started
3. Core Concepts
4. Tools Reference
5. Common Workflows
6. Best Practices
7. Troubleshooting
8. Advanced Usage
9. Real-World Examples
10. FAQ

---

## Introduction

### What is JDocMunch MCP?

JDocMunch MCP is a documentation intelligence server that enables AI agents to retrieve **only the documentation sections they actually need**, instead of loading entire repositories into context. Documentation is indexed once and served through precision retrieval tools.

### Why Use It?

**Traditional workflow**

* Load entire documentation sets per query
* High token consumption
* Slow responses
* Repeated API calls

**JDocMunch workflow**

* Index documentation once
* Retrieve only relevant sections
* Minimal token usage per query
* Instant cached responses

Typical workflows see **90–97% token savings** and significantly faster response times.

### Who Should Use It?

* AI coding assistants
* Developer tools integrating documentation search
* Teams with large documentation repositories
* Cost-sensitive LLM deployments
* Multi-agent systems

---

## Getting Started

### Prerequisites

* Python 3.10+
* pip
* Git (recommended)
* Optional:

  * `GITHUB_TOKEN` for private repositories
  * `ANTHROPIC_API_KEY` for AI summaries

### Installation

#### Install from repository

```bash
git clone https://github.com/jgravelle/jdocmunch-mcp.git
cd jdocmunch-mcp
pip install -e .
```

#### Run without installation

```bash
python -m src.jdocmunch_mcp.server
```

### Configure Environment Variables

Linux/macOS:

```bash
export GITHUB_TOKEN="ghp_..."
export ANTHROPIC_API_KEY="sk-ant-..."
```

Windows PowerShell:

```powershell
$env:GITHUB_TOKEN="ghp_..."
$env:ANTHROPIC_API_KEY="sk-ant-..."
```

### Configure MCP Client

Example Claude configuration:

```json
{
  "mcpServers": {
    "jdocmunch": {
      "command": "jdocmunch-mcp"
    }
  }
}
```

Restart the MCP client and confirm tools are listed.

---

## Core Concepts

### Index Phase (one-time per repository)

1. Fetch repository documentation
2. Parse sections
3. Generate summaries (optional)
4. Store index locally (`~/.doc-index/`)

### Query Phase

1. Browse index (`get_toc`)
2. Search (`search_sections`)
3. Load relevant sections (`get_section`)

Typical queries consume **hundreds of tokens**, not tens of thousands.

---

## Tools Reference

### index_repo

Index repository documentation.

| Parameter        | Required | Description              |
| ---------------- | -------- | ------------------------ |
| url              | yes      | GitHub URL or owner/repo |
| use_ai_summaries | no       | Generate summaries       |

---

### list_repos

Return indexed repositories.

---

### get_toc

Return section table of contents (optionally with summaries).

---

### get_toc_tree

Return hierarchical documentation structure.

---

### get_section

Return full content of a section.

---

### get_sections

Batch retrieve multiple sections.

---

### search_sections

Search titles, summaries, and keywords.

---

### get_document_outline

Return section hierarchy for a specific file.

---

### delete_index

Delete cached index for a repository.

---

## Common Workflows

### First-time query

1. `index_repo()`
2. `get_toc()`
3. `get_section()`

---

### Topic search

1. `search_sections()`
2. `get_section()`

---

### Multi-section research

1. `search_sections()`
2. `get_sections()`

---

### Re-index updated documentation

```javascript
index_repo({url:"owner/repo"})
```

---

## Best Practices

* Index once and query repeatedly
* Search before loading content
* Use batch retrieval (`get_sections`)
* Disable summaries if indexing speed is critical
* Periodically re-index repositories with frequent updates

---

## Troubleshooting

### Repository not found

* Verify URL format
* Ensure token permissions for private repos

### No sections indexed

* Confirm README or docs folder exists
* Verify supported file formats

### Search returns no results

* Broaden search terms
* Re-index with AI summaries enabled

### Slow indexing

* Disable summaries
* Ensure authenticated GitHub requests

---

## Advanced Usage

### Programmatic Access

```python
from jdocmunch_mcp.tools.index_repo import index_repo
await index_repo(url="owner/repo")
```

### Parallel indexing

```python
await asyncio.gather(*(index_repo(url=r) for r in repos))
```

### Custom summary models

Modify summarizer configuration in:

```
src/jdocmunch_mcp/summarizer/
```

---

## Real-World Examples

### Documentation chatbot

* Index repo once
* Search per question
* Load top sections
* Generate response

### Code review assistant

* Search API documentation
* Retrieve relevant sections
* Compare against changes

### Multi-repo knowledge search

* Index multiple repositories
* Search each repository
* Rank combined results

---

## FAQ

**Does it work with private repositories?**
Yes, with `GITHUB_TOKEN`.

**Can it run without AI summaries?**
Yes. Summaries are optional.

**How often should indexing run?**
Re-index when documentation meaningfully changes.

**Does it support non-GitHub sources?**
Currently GitHub and local directories.

---

## Environment Variables

| Variable          | Purpose                |
| ----------------- | ---------------------- |
| GITHUB_TOKEN      | GitHub authentication  |
| ANTHROPIC_API_KEY | AI summaries           |
| MCP_DEBUG         | Enable verbose logging |

---

## Storage Layout

```
~/.doc-index/
  owner-repo.json
  owner-repo/
    README.md
    docs/
```

Indexes typically require **100KB–1MB per repository**.

---

## Token Efficiency Overview

| Operation       | Typical Tokens |
| --------------- | -------------- |
| get_toc         | 500-1500       |
| search_sections | 200-500        |
| get_section     | 200-2000       |

Typical full workflow: **1.5k–3k tokens**
Full documentation load: **50k–200k tokens**

---

## Changelog

### v0.2.0

* Security hardening (symlink/path validation)
* Secret detection
* Incremental reindexing
* MDX and RST support
* Cache versioning
* New tools: `get_document_outline`, `delete_index`

### v0.1.0

* Initial release
* Core indexing and retrieval tools

---

## License

MIT License

---

**Maintainer:** [https://github.com/jgravelle](https://github.com/jgravelle)
