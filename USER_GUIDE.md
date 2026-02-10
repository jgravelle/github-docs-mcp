# JDocMunch MCP Server - User Guide

**Your complete guide to querying GitHub documentation with 97% token efficiency.**

---

## Table of Contents

1. [Introduction](#introduction)
2. [Getting Started](#getting-started)
3. [Core Concepts](#core-concepts)
4. [Tools Reference](#tools-reference)
5. [Common Workflows](#common-workflows)
6. [Best Practices](#best-practices)
7. [Troubleshooting](#troubleshooting)
8. [Advanced Usage](#advanced-usage)
9. [Real-World Examples](#real-world-examples)
10. [FAQ](#faq)

---

## Introduction

### What is JDocMunch MCP?

JDocMunch MCP is an intelligent documentation server that allows AI agents (like Claude) to access GitHub repository documentation efficiently. Instead of loading entire documentation files (costing thousands of tokens), it intelligently indexes, summarizes, and delivers only the sections you need.

### Why Use It?

**The Problem:**
When AI agents need to answer questions about a codebase's documentation, the naive approach is to load all documentation files into context. For a typical project, this can cost 50,000+ tokens per query—expensive and slow.

**The Solution:**
JDocMunch MCP pre-processes documentation into a searchable index with AI-generated summaries. It loads only relevant sections on demand, reducing token usage by ~97%.

**Real-World Impact:**
- **Cost Savings**: $0.03 per query instead of $0.75
- **Speed**: Faster responses with smaller context windows
- **Scale**: Handle 30x more queries for the same budget

### Who Should Use This?

- Developers building AI coding assistants
- Teams with large documentation sets
- Cost-conscious API users
- Anyone doing repeated documentation queries

---

## Getting Started

### Prerequisites

Before you begin, ensure you have:

- **Python 3.10 or higher**
- **pip** (Python package manager)
- **Git** (to clone the repository)
- **(Optional)** GitHub personal access token for private repos
- **(Optional)** Anthropic API key for AI-generated summaries

### Installation

#### Option 1: Install from Source

```bash
# Clone the repository
git clone https://github.com/jgravelle/jdocmunch-mcp.git
cd jdocmunch-mcp

# Install in development mode
pip install -e .
```

#### Option 2: Quick Test (No Installation)

```bash
# Run directly from source
cd jdocmunch-mcp
python -m src.jdocmunch_mcp.server
```

### Configuration

#### 1. Set Up Environment Variables

For private repositories and AI summaries, configure these environment variables:

**Linux/Mac:**
```bash
# Add to ~/.bashrc or ~/.zshrc
export GITHUB_TOKEN="ghp_your_token_here"
export ANTHROPIC_API_KEY="sk-ant-your_key_here"
```

**Windows (PowerShell):**
```powershell
# Add to PowerShell profile
$env:GITHUB_TOKEN="ghp_your_token_here"
$env:ANTHROPIC_API_KEY="sk-ant-your_key_here"
```

**Windows (Command Prompt):**
```cmd
setx GITHUB_TOKEN "ghp_your_token_here"
setx ANTHROPIC_API_KEY "sk-ant-your_key_here"
```

#### 2. Configure Claude Code

Add the server to your Claude Code MCP configuration at `~/.claude/mcp.json`:

**If Installed:**
```json
{
  "mcpServers": {
    "github-docs": {
      "command": "jdocmunch-mcp"
    }
  }
}
```

**If Running from Source:**
```json
{
  "mcpServers": {
    "github-docs": {
      "command": "python",
      "args": ["-m", "jdocmunch_mcp.server"],
      "cwd": "/absolute/path/to/jdocmunch-mcp/src"
    }
  }
}
```

#### 3. Verify Installation

Restart Claude Code and verify the server is connected:

1. Open Claude Code
2. Look for the MCP server indicator
3. Try: "List available MCP tools"

You should see the GitHub Docs tools listed.

---

## Core Concepts

### How It Works

#### 1. **Indexing Phase** (One-Time Per Repo)

When you index a repository:

1. **Fetch**: Downloads README.md and docs/ folder from GitHub
2. **Parse**: Extracts sections using markdown heading structure
3. **Summarize**: Generates AI summaries for each section (optional)
4. **Store**: Saves the index locally at `~/.doc-index/`

**Token Cost**: Varies by documentation size, but this is a one-time cost.

#### 2. **Query Phase** (Ongoing)

When answering questions:

1. **Browse**: Use `get_toc` to see section summaries (~1000 tokens)
2. **Search**: Use `search_sections` to find relevant topics (~300 tokens)
3. **Load**: Use `get_section` to load specific content (~500 tokens)

**Total Token Cost**: ~1,800 tokens vs 50,000+ tokens for full docs.

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│  Your Workflow                                              │
│  1. Index repo (once)                                       │
│  2. Browse table of contents                                │
│  3. Search or navigate to relevant section                  │
│  4. Load only what you need                                 │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  JDocMunch MCP Server                                       │
│  • Maintains local index cache                              │
│  • Provides lazy-loading tools                              │
│  • Returns only requested data                              │
└─────────────────────────────────────────────────────────────┘
                           │
              ┌────────────┴────────────┐
              │                         │
              ▼                         ▼
    ┌──────────────────┐      ┌──────────────────┐
    │  Local Cache     │      │  GitHub API      │
    │  ~/.doc-index/   │      │  (on-demand)     │
    └──────────────────┘      └──────────────────┘
```

### Data Storage

All indexed data is stored locally:

```
~/.doc-index/
├── anthropics-claude-code.json       # Index with summaries
├── anthropics-claude-code/           # Raw documentation
│   ├── README.md
│   └── docs/
│       ├── getting-started.md
│       ├── api-reference.md
│       └── ...
├── facebook-react.json
└── facebook-react/
    └── ...
```

**Storage Considerations:**
- Indexes are typically 100KB-1MB per repo
- Raw docs mirror the repo's docs folder
- No automatic cleanup—manage manually if needed

---

## Tools Reference

### 1. `index_repo`

**Purpose**: Index a repository's documentation for the first time.

**When to Use**:
- Before querying a new repository
- When documentation has been significantly updated
- To enable AI-generated summaries

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `url` | string | Yes | - | GitHub URL or `owner/repo` format |
| `use_ai_summaries` | boolean | No | `true` | Generate AI summaries (requires ANTHROPIC_API_KEY) |

**Supported URL Formats**:
- `https://github.com/owner/repo`
- `owner/repo`
- `github.com/owner/repo`

**Example Usage**:

```javascript
// Index a public repository with AI summaries
index_repo({
  url: "anthropics/claude-code",
  use_ai_summaries: true
})

// Index without AI summaries (faster, no API key needed)
index_repo({
  url: "https://github.com/facebook/react",
  use_ai_summaries: false
})
```

**Returns**:
```json
{
  "status": "success",
  "repo": "anthropics-claude-code",
  "sections": 47,
  "indexed_at": "2024-01-15T10:30:00Z",
  "has_summaries": true
}
```

**Performance**:
- Public repos: ~30-60 seconds
- Private repos: Similar (requires GITHUB_TOKEN)
- With AI summaries: Adds ~20-40 seconds

**Errors**:
- `Repository not found`: Check URL and GITHUB_TOKEN
- `API rate limit exceeded`: Wait or use authenticated requests
- `No documentation found`: Repo has no README or docs/ folder

---

### 2. `list_repos`

**Purpose**: View all indexed repositories.

**When to Use**:
- Check what documentation is available
- Verify a repository was indexed successfully
- See when repositories were last indexed

**Parameters**: None

**Example Usage**:

```javascript
list_repos()
```

**Returns**:
```json
{
  "repositories": [
    {
      "name": "anthropics-claude-code",
      "indexed_at": "2024-01-15T10:30:00Z",
      "section_count": 47,
      "has_summaries": true
    },
    {
      "name": "facebook-react",
      "indexed_at": "2024-01-14T15:20:00Z",
      "section_count": 156,
      "has_summaries": false
    }
  ]
}
```

**Token Cost**: ~50 tokens

---

### 3. `get_toc`

**Purpose**: Get the table of contents with section summaries.

**When to Use**:
- First step after indexing
- Understand documentation structure
- Find relevant sections without loading full content

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `repo` | string | Yes | - | Repository identifier |
| `include_summaries` | boolean | No | `true` | Include AI-generated summaries |

**Example Usage**:

```javascript
// Get TOC with summaries
get_toc({
  repo: "anthropics-claude-code",
  include_summaries: true
})

// Get TOC without summaries (faster, fewer tokens)
get_toc({
  repo: "claude-code",
  include_summaries: false
})
```

**Returns**:
```json
{
  "repo": "anthropics-claude-code",
  "sections": [
    {
      "id": "readme-getting-started",
      "title": "Getting Started",
      "level": 2,
      "file": "README.md",
      "summary": "Installation instructions and quick start guide"
    },
    {
      "id": "docs-api-reference",
      "title": "API Reference",
      "level": 1,
      "file": "docs/api-reference.md",
      "summary": "Complete API documentation for all methods"
    }
  ]
}
```

**Token Cost**:
- With summaries: ~500-1500 tokens
- Without summaries: ~200-400 tokens

**Pro Tips**:
- Use `include_summaries: false` if you already know which section you need
- Section IDs can be used with `get_section` to load full content

---

### 4. `get_toc_tree`

**Purpose**: Get the table of contents as a hierarchical tree.

**When to Use**:
- Visualize documentation structure
- Understand section relationships
- Navigate complex documentation hierarchies

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `repo` | string | Yes | - | Repository identifier |

**Example Usage**:

```javascript
get_toc_tree({
  repo: "anthropics-claude-code"
})
```

**Returns**:
```json
{
  "repo": "anthropics-claude-code",
  "tree": {
    "README.md": {
      "children": [
        {
          "id": "readme-introduction",
          "title": "Introduction",
          "level": 1,
          "children": [...]
        }
      ]
    },
    "docs/": {
      "children": [...]
    }
  }
}
```

**Token Cost**: ~400-800 tokens

---

### 5. `get_section`

**Purpose**: Load the full content of a specific section.

**When to Use**:
- After identifying relevant sections via `get_toc` or `search_sections`
- When you need the actual documentation content
- Loading targeted information

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `repo` | string | Yes | - | Repository identifier |
| `section_id` | string | Yes | - | Section ID from TOC or search |

**Example Usage**:

```javascript
get_section({
  repo: "anthropics-claude-code",
  section_id: "docs-api-authentication"
})
```

**Returns**:
```json
{
  "section_id": "docs-api-authentication",
  "title": "Authentication",
  "file": "docs/api-reference.md",
  "content": "# Authentication\n\nTo authenticate with the API...",
  "level": 2
}
```

**Token Cost**: ~200-2000 tokens (depends on section length)

**Pro Tips**:
- Load multiple related sections with `get_sections` (batch operation)
- Section content is returned as markdown

---

### 6. `get_sections`

**Purpose**: Load multiple sections at once.

**When to Use**:
- Loading several related sections
- Batch operations for efficiency
- When you need content from multiple parts of docs

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `repo` | string | Yes | - | Repository identifier |
| `section_ids` | array | Yes | - | List of section IDs to retrieve |

**Example Usage**:

```javascript
get_sections({
  repo: "anthropics-claude-code",
  section_ids: [
    "docs-api-authentication",
    "docs-api-rate-limits",
    "docs-api-errors"
  ]
})
```

**Returns**:
```json
{
  "sections": [
    {
      "section_id": "docs-api-authentication",
      "title": "Authentication",
      "content": "...",
      "level": 2
    },
    {
      "section_id": "docs-api-rate-limits",
      "title": "Rate Limits",
      "content": "...",
      "level": 2
    }
  ]
}
```

**Token Cost**: Varies (sum of all sections, typically 500-5000 tokens)

---

### 7. `search_sections`

**Purpose**: Search for sections by topic or keyword.

**When to Use**:
- Finding relevant documentation without browsing
- When you know what you're looking for but not where it is
- Quick topic discovery

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `repo` | string | Yes | - | Repository identifier |
| `query` | string | Yes | - | Search query |
| `max_results` | integer | No | `10` | Maximum results to return |

**Search Behavior**:
- Searches section titles, summaries, and keywords
- Case-insensitive matching
- Ranked by relevance

**Example Usage**:

```javascript
// Search for authentication docs
search_sections({
  repo: "anthropics-claude-code",
  query: "authentication oauth",
  max_results: 5
})

// Broad search
search_sections({
  repo: "react",
  query: "hooks"
})
```

**Returns**:
```json
{
  "query": "authentication oauth",
  "results": [
    {
      "section_id": "docs-auth-oauth",
      "title": "OAuth Authentication",
      "summary": "How to authenticate using OAuth 2.0",
      "score": 0.95,
      "file": "docs/authentication.md"
    },
    {
      "section_id": "docs-auth-tokens",
      "title": "API Tokens",
      "summary": "Using API tokens for authentication",
      "score": 0.72,
      "file": "docs/authentication.md"
    }
  ]
}
```

**Token Cost**: ~200-500 tokens

**Pro Tips**:
- Use specific keywords for better results
- Combine with `get_section` to load relevant content
- Limit results with `max_results` to save tokens

---

## Common Workflows

### Workflow 1: First-Time Repository Query

**Scenario**: You need to answer questions about a repo you've never indexed.

**Steps**:

```javascript
// 1. Index the repository
index_repo({
  url: "anthropics/claude-code",
  use_ai_summaries: true
})
// Result: Repository indexed with 47 sections

// 2. Browse the table of contents
get_toc({
  repo: "claude-code",
  include_summaries: true
})
// Result: See all 47 sections with summaries

// 3. Identify relevant section from TOC
// Section ID: "docs-getting-started-installation"

// 4. Load the specific section
get_section({
  repo: "claude-code",
  section_id: "docs-getting-started-installation"
})
// Result: Full installation documentation

// 5. Answer the user's question using the loaded content
```

**Token Usage**: ~1,800 tokens (vs ~50,000 for full docs)

---

### Workflow 2: Quick Topic Search

**Scenario**: You know what topic you're looking for but don't know where it is.

**Steps**:

```javascript
// 1. Search for the topic
search_sections({
  repo: "claude-code",
  query: "rate limits api quota",
  max_results: 3
})
// Result: 3 relevant sections found

// 2. Load the most relevant section
get_section({
  repo: "claude-code",
  section_id: "docs-api-rate-limits"
})
// Result: Full rate limits documentation

// 3. Answer the question
```

**Token Usage**: ~700 tokens

---

### Workflow 3: Comprehensive Research

**Scenario**: You need to understand a complex topic across multiple sections.

**Steps**:

```javascript
// 1. Search for the main topic
search_sections({
  repo: "react",
  query: "state management hooks",
  max_results: 10
})
// Result: 10 relevant sections identified

// 2. Review summaries and select relevant sections
// Selected IDs: ["docs-hooks-state", "docs-hooks-effect", "docs-hooks-context"]

// 3. Batch load all relevant sections
get_sections({
  repo: "react",
  section_ids: [
    "docs-hooks-state",
    "docs-hooks-effect",
    "docs-hooks-context"
  ]
})
// Result: All related documentation loaded

// 4. Synthesize information and answer
```

**Token Usage**: ~3,000 tokens (vs ~150,000 for full React docs)

---

### Workflow 4: Exploring a New Codebase

**Scenario**: You're learning about a new project and want to understand its structure.

**Steps**:

```javascript
// 1. Index the repository
index_repo({
  url: "vercel/next.js",
  use_ai_summaries: true
})

// 2. Get the hierarchical TOC
get_toc_tree({
  repo: "next.js"
})
// Result: See complete documentation structure

// 3. Start with high-level overview
get_section({
  repo: "next.js",
  section_id: "readme-introduction"
})

// 4. Dive into specific areas as needed
search_sections({
  repo: "next.js",
  query: "routing"
})

get_section({
  repo: "next.js",
  section_id: "docs-routing-basics"
})
```

**Token Usage**: ~2,500 tokens for comprehensive overview

---

### Workflow 5: Re-indexing Updated Documentation

**Scenario**: Documentation has been updated and you need fresh content.

**Steps**:

```javascript
// 1. Re-index the repository (overwrites old index)
index_repo({
  url: "anthropics/claude-code",
  use_ai_summaries: true
})
// Result: Fresh index created

// 2. Continue with normal workflow
```

**Note**: Re-indexing completely replaces the old index. There's no automatic update checking.

---

## Best Practices

### Optimization Tips

#### 1. **Index Once, Query Many**
- Indexing has upfront cost; maximize value with multiple queries
- Re-index only when documentation significantly changes

#### 2. **Use Summaries First**
- Always start with `get_toc` to see summaries
- Only load full sections when needed
- Summaries often contain enough information to answer questions

#### 3. **Search Before Browsing**
- Use `search_sections` when you know what you're looking for
- More efficient than browsing the entire TOC

#### 4. **Batch Related Sections**
- Use `get_sections` (plural) instead of multiple `get_section` calls
- Reduces overhead and improves efficiency

#### 5. **Disable AI Summaries for Speed**
- If you don't need summaries, set `use_ai_summaries: false`
- Faster indexing, no API key required
- You can still navigate by section titles

### Token Efficiency Strategies

#### Start Small, Expand as Needed
```javascript
// Good: Progressive loading
1. get_toc() → See all sections (~1000 tokens)
2. search_sections() → Find relevant ones (~300 tokens)
3. get_section() → Load only what you need (~500 tokens)
Total: ~1,800 tokens

// Bad: Load everything upfront
1. get_sections([all_section_ids]) → (~50,000 tokens)
```

#### Use Search Effectively
```javascript
// Good: Specific query
search_sections({
  repo: "react",
  query: "useEffect cleanup function",
  max_results: 3
})

// Less effective: Generic query
search_sections({
  repo: "react",
  query: "hooks"
})
```

#### Leverage Section Hierarchies
- Parent sections often provide context
- Child sections contain specific details
- Navigate hierarchically for better understanding

### Managing Storage

#### Check Storage Usage
```bash
# See total storage used
du -sh ~/.doc-index/

# List all indexed repos
ls -lh ~/.doc-index/*.json
```

#### Clean Up Old Indexes
```bash
# Remove specific repository
rm -rf ~/.doc-index/owner-repo*

# Clean everything (be careful!)
rm -rf ~/.doc-index/
```

#### Storage Considerations
- Each repo index: ~100KB-1MB
- Raw documentation: varies by repo size
- Consider cleaning up repos you no longer query

### Error Handling

#### Graceful Degradation
```javascript
// Always handle errors in your code
try {
  result = search_sections({repo: "unknown-repo", query: "test"})
} catch (error) {
  // Fallback: Try listing available repos
  repos = list_repos()
  // Inform user of available options
}
```

#### Common Error Patterns
1. **Repository not indexed**: Always check with `list_repos()` first
2. **Invalid section ID**: Use `get_toc()` to get valid IDs
3. **Rate limiting**: Implement exponential backoff for indexing

---

## Troubleshooting

### Common Issues

#### Issue 1: "Repository not found"

**Symptoms**: Error when trying to index a repository

**Causes**:
- Incorrect URL format
- Repository is private (needs GITHUB_TOKEN)
- Repository doesn't exist
- Typo in owner/repo name

**Solutions**:
```bash
# Verify the repository exists
curl https://api.github.com/repos/owner/repo

# For private repos, set GITHUB_TOKEN
export GITHUB_TOKEN="ghp_your_token_here"

# Try different URL formats
index_repo({url: "owner/repo"})
index_repo({url: "https://github.com/owner/repo"})
```

---

#### Issue 2: "No documentation found"

**Symptoms**: Repository indexes but shows 0 sections

**Causes**:
- Repository has no README.md or docs/ folder
- Documentation is in a non-standard location
- Documentation uses non-standard file extensions

**Solutions**:
```javascript
// Check what was indexed
list_repos()

// Verify repository structure on GitHub
// Currently, only README.md and docs/*.md are indexed
```

**Workaround**: Currently not supported. Future versions may allow custom paths.

---

#### Issue 3: Search returns no results

**Symptoms**: `search_sections` returns empty results

**Causes**:
- Query doesn't match any section titles/summaries
- Repository indexed without AI summaries
- Search terms too specific

**Solutions**:
```javascript
// Try broader search terms
search_sections({repo: "react", query: "state"})  // vs "useState hook implementation"

// Check TOC for actual section titles
get_toc({repo: "react", include_summaries: true})

// Re-index with AI summaries
index_repo({url: "react", use_ai_summaries: true})
```

---

#### Issue 4: Slow indexing

**Symptoms**: `index_repo` takes several minutes

**Causes**:
- Large documentation set
- AI summary generation enabled
- Slow internet connection
- GitHub API rate limiting

**Solutions**:
```javascript
// Disable AI summaries for faster indexing
index_repo({
  url: "large-repo",
  use_ai_summaries: false
})

// For rate limiting, use authenticated requests
export GITHUB_TOKEN="your_token"  // Higher rate limit

// Be patient with large repos (e.g., React, TypeScript)
// They may have 200+ sections
```

---

#### Issue 5: API rate limit exceeded

**Symptoms**: Error during indexing or when using AI summaries

**Causes**:
- Too many requests to GitHub API (unauthenticated: 60/hour)
- Too many requests to Anthropic API

**Solutions**:
```bash
# For GitHub: Use authenticated requests (5000/hour)
export GITHUB_TOKEN="your_token"

# For Anthropic: Wait or upgrade API tier
# Check your rate limits:
curl -H "x-api-key: $ANTHROPIC_API_KEY" https://api.anthropic.com/v1/rate-limits
```

---

#### Issue 6: Section content is truncated

**Symptoms**: `get_section` returns incomplete content

**Causes**:
- Section is extremely long
- Content contains special characters
- Parsing error

**Solutions**:
```javascript
// Check the raw file
// Content is stored in ~/.doc-index/owner-repo/path/to/file.md

// Try loading parent/child sections
get_toc_tree({repo: "your-repo"})
get_section({repo: "your-repo", section_id: "parent-section"})
```

---

### Debugging Tips

#### Enable Verbose Logging

```bash
# Set environment variable for detailed logs
export MCP_DEBUG=1

# Run the server
python -m jdocmunch_mcp.server
```

#### Check Index Files

```bash
# Inspect the index JSON
cat ~/.doc-index/owner-repo.json | jq '.sections[] | {id, title}'

# Check raw documentation
ls -la ~/.doc-index/owner-repo/
```

#### Test Tools Directly

```python
# Test in Python REPL
from jdocmunch_mcp.tools.search_sections import search_sections

result = search_sections(repo="claude-code", query="test", max_results=5)
print(result)
```

---

## Advanced Usage

### Custom Integration

#### Using with Other MCP Clients

The server works with any MCP-compatible client:

```json
// Generic MCP client configuration
{
  "servers": {
    "github-docs": {
      "transport": "stdio",
      "command": "jdocmunch-mcp"
    }
  }
}
```

#### Programmatic Access

```python
# Direct Python usage (without MCP)
from jdocmunch_mcp.tools.index_repo import index_repo
from jdocmunch_mcp.tools.search_sections import search_sections

# Index a repository
await index_repo(url="owner/repo", use_ai_summaries=True)

# Search
results = search_sections(repo="owner-repo", query="authentication")
print(results)
```

### Performance Tuning

#### Parallel Indexing

```python
# Index multiple repositories concurrently
import asyncio
from jdocmunch_mcp.tools.index_repo import index_repo

async def index_multiple(repos):
    tasks = [index_repo(url=repo, use_ai_summaries=True) for repo in repos]
    return await asyncio.gather(*tasks)

# Usage
repos = ["react", "vue", "angular"]
await index_multiple(repos)
```

#### Custom Summary Models

```python
# Modify summarizer to use different models
# Edit: src/jdocmunch_mcp/summarizer/batch_summarize.py

# Change model from claude-haiku to claude-sonnet for better summaries
client = anthropic.Anthropic(api_key=api_key)
response = client.messages.create(
    model="claude-sonnet-4.5",  # Changed from claude-haiku
    max_tokens=100,
    messages=[...]
)
```

### Extending Functionality

#### Index Custom Paths

```python
# Currently, only README.md and docs/ are indexed
# To index custom paths, modify:
# src/jdocmunch_mcp/tools/index_repo.py

# Example: Add "wiki/" to indexed paths
paths_to_index = [
    "README.md",
    "docs/",
    "wiki/"  # Add custom path
]
```

#### Custom Search Ranking

```python
# Modify search algorithm
# Edit: src/jdocmunch_mcp/tools/search_sections.py

def search_sections(repo, query, max_results=10):
    # Add custom ranking logic
    # E.g., boost recent sections, prioritize specific files, etc.
    ...
```

---

## Real-World Examples

### Example 1: Building a Documentation Chatbot

**Goal**: Create a chatbot that answers questions about Next.js documentation.

**Implementation**:

```javascript
// Setup phase (run once)
index_repo({
  url: "vercel/next.js",
  use_ai_summaries: true
})

// Chat loop
function answerQuestion(userQuestion) {
  // 1. Search for relevant sections
  const searchResults = search_sections({
    repo: "next.js",
    query: userQuestion,
    max_results: 5
  })

  // 2. Load top 3 results
  const topSections = searchResults.results.slice(0, 3).map(r => r.section_id)
  const sections = get_sections({
    repo: "next.js",
    section_ids: topSections
  })

  // 3. Use sections as context to answer
  return generateAnswer(sections, userQuestion)
}

// Example usage
answerQuestion("How do I use dynamic routes in Next.js?")
// Loads: docs-routing-dynamic, docs-routing-catch-all
// Returns: Concise answer with code examples
```

**Token Savings**: ~2,000 tokens per question vs ~150,000 for full docs

---

### Example 2: Code Review Assistant

**Goal**: Help reviewers understand API changes by referencing documentation.

**Implementation**:

```javascript
function explainAPIChange(fileName, changedFunction) {
  // 1. Index the repository
  index_repo({
    url: "anthropics/anthropic-sdk-python",
    use_ai_summaries: true
  })

  // 2. Search for the function documentation
  const results = search_sections({
    repo: "anthropic-sdk-python",
    query: `${changedFunction} API reference`,
    max_results: 3
  })

  // 3. Load relevant documentation
  const docs = get_section({
    repo: "anthropic-sdk-python",
    section_id: results.results[0].section_id
  })

  // 4. Generate explanation
  return compareWithDocs(docs, fileName, changedFunction)
}

// Usage in PR review
explainAPIChange("client.py", "messages.create")
```

---

### Example 3: Multi-Repository Knowledge Base

**Goal**: Answer questions across multiple codebases.

**Implementation**:

```javascript
// Index multiple repositories
const repos = [
  "anthropics/claude-code",
  "anthropics/anthropic-sdk-python",
  "anthropics/anthropic-sdk-typescript"
]

repos.forEach(repo => {
  index_repo({url: repo, use_ai_summaries: true})
})

// Search across all indexed repos
function searchAllRepos(query) {
  const allRepos = list_repos().repositories

  const results = allRepos.flatMap(repo => {
    const repoResults = search_sections({
      repo: repo.name,
      query: query,
      max_results: 3
    })
    return repoResults.results.map(r => ({...r, repo: repo.name}))
  })

  // Sort by relevance across all repos
  return results.sort((a, b) => b.score - a.score).slice(0, 10)
}

// Usage
const results = searchAllRepos("authentication methods")
// Returns top 10 results across all Anthropic repos
```

---

### Example 4: Documentation Diff Checker

**Goal**: Compare old vs new documentation versions.

**Implementation**:

```javascript
// Index old version (using git tag or commit)
// Note: Requires manual process to fetch old docs
index_repo({
  url: "facebook/react",  // Current version
  use_ai_summaries: true
})

// Later: Manually create old-version index
// Then compare sections

function compareDocVersions(sectionId) {
  const currentDocs = get_section({
    repo: "react",
    section_id: sectionId
  })

  const oldDocs = get_section({
    repo: "react-v17",  // Manually indexed old version
    section_id: sectionId
  })

  return {
    current: currentDocs.content,
    old: oldDocs.content,
    diff: computeDiff(oldDocs.content, currentDocs.content)
  }
}
```

---

### Example 5: Learning Path Generator

**Goal**: Create a structured learning path for a framework.

**Implementation**:

```javascript
// Index the repository
index_repo({
  url: "vuejs/core",
  use_ai_summaries: true
})

// Get full documentation structure
const tree = get_toc_tree({repo: "core"})

// Analyze structure to create learning path
function generateLearningPath(tree) {
  const learningPath = [
    // Beginner
    findSections(tree, ["introduction", "getting started", "basics"]),
    // Intermediate
    findSections(tree, ["components", "reactivity", "routing"]),
    // Advanced
    findSections(tree, ["composition", "advanced", "performance"])
  ]

  // Load content for each step
  return learningPath.map(sections =>
    get_sections({repo: "core", section_ids: sections})
  )
}
```

---

## FAQ

### General Questions

**Q: Does this work with private repositories?**

A: Yes! Set your `GITHUB_TOKEN` environment variable with a personal access token that has repo access.

```bash
export GITHUB_TOKEN="ghp_your_token_here"
```

---

**Q: Can I use this without an Anthropic API key?**

A: Yes! Disable AI summaries during indexing:

```javascript
index_repo({
  url: "owner/repo",
  use_ai_summaries: false
})
```

You can still search and navigate by section titles, just without AI-generated summaries.

---

**Q: How much does AI summary generation cost?**

A: It depends on documentation size. For a typical repo with 50 sections:
- Cost: ~$0.05-0.10 using Claude Haiku
- Time: ~30-60 seconds
- One-time cost per repository

---

**Q: Can I index non-GitHub repositories?**

A: Not currently. The server is designed specifically for GitHub. Support for other Git hosting platforms (GitLab, Bitbucket) may be added in future versions.

---

**Q: Does it support languages other than English?**

A: Yes! The markdown parser works with any language. AI summaries will be generated in the language of the documentation (Claude is multilingual).

---

### Technical Questions

**Q: How are section IDs generated?**

A: Section IDs are created from the file path and heading text:
- Format: `{file}-{heading-slug}`
- Example: `docs-api-reference` for "API Reference" in docs/api.md
- Slugs are lowercase, spaces become hyphens, special characters removed

---

**Q: What happens if documentation changes?**

A: The index doesn't automatically update. Re-run `index_repo()` to refresh:

```javascript
// This will overwrite the existing index
index_repo({url: "owner/repo", use_ai_summaries: true})
```

---

**Q: Can I search within section content, not just titles?**

A: Currently, `search_sections` only searches titles, summaries, and extracted keywords. Full-text search of section content is not yet supported but is planned for a future release.

---

**Q: What markdown features are supported?**

A: The parser handles:
- Headings (H1-H6)
- Code blocks
- Lists (ordered/unordered)
- Links and images
- Tables
- Blockquotes

Not parsed as separate sections: footnotes, HTML, embedded components.

---

**Q: How do I contribute to the project?**

A: The project is open source! Visit [github.com/jgravelle/jdocmunch-mcp](https://github.com/jgravelle/jdocmunch-mcp) to:
- Report issues
- Submit pull requests
- Request features
- Improve documentation

---

### Troubleshooting Questions

**Q: Why is indexing so slow?**

A: Several factors affect speed:
1. **Documentation size**: Large repos (200+ sections) take longer
2. **AI summaries**: Adds 20-40 seconds
3. **Network speed**: Downloading from GitHub
4. **Rate limiting**: GitHub API throttling

**Solutions**:
- Disable AI summaries for faster indexing
- Use authenticated GitHub requests (higher rate limit)
- Be patient with large repos

---

**Q: Why can't I find a section I know exists?**

A: Check these possibilities:
1. Section is in a file outside README.md or docs/
2. Documentation uses non-standard markdown (HTML, custom components)
3. Search query doesn't match title/summary
4. Section wasn't properly parsed (check index file)

**Debug**:
```bash
# Check what was indexed
cat ~/.doc-index/owner-repo.json | jq '.sections'
```

---

**Q: Can I use this in production?**

A: Yes, with considerations:
- **Caching**: Indexes are local, so each instance needs to index
- **Updates**: No automatic refresh; implement periodic re-indexing
- **Rate limits**: Plan for GitHub/Anthropic API limits at scale
- **Storage**: Monitor disk usage for many repositories

---

**Q: Does this work with monorepos?**

A: Yes! Each directory with docs can be treated as a separate "repository". However, you'll need to index the entire monorepo (e.g., `owner/monorepo`), which will include all subdirectories' documentation.

For more granular control, future versions may support subdirectory indexing.

---

## Getting Help

### Support Channels

- **GitHub Issues**: [Report bugs or request features](https://github.com/jgravelle/jdocmunch-mcp/issues)
- **Discussions**: Share use cases and ask questions
- **Documentation**: This guide and the README

### Providing Feedback

When reporting issues, please include:
1. Your environment (OS, Python version)
2. Command/tool that failed
3. Error messages
4. Steps to reproduce

Example:
```
Environment: macOS 14, Python 3.11
Tool: index_repo
Error: "Repository not found"
Steps:
1. Set GITHUB_TOKEN
2. Run: index_repo({url: "private/repo"})
3. Error occurs
```

---

## Appendix

### Environment Variables Reference

| Variable | Required | Purpose |
|----------|----------|---------|
| `GITHUB_TOKEN` | Optional | Access private repos, higher rate limits |
| `ANTHROPIC_API_KEY` | Optional | Enable AI-generated summaries |
| `MCP_DEBUG` | Optional | Enable verbose logging |

### File Structure Reference

```
~/.doc-index/
├── {owner}-{repo}.json          # Index with metadata
│   ├── repo: string              # Repository identifier
│   ├── indexed_at: timestamp     # When it was indexed
│   ├── sections: array           # All sections
│   │   ├── id: string            # Section identifier
│   │   ├── title: string         # Section title
│   │   ├── level: number         # Heading level (1-6)
│   │   ├── file: string          # Source file path
│   │   ├── summary: string       # AI summary (optional)
│   │   └── content_start: number # Position in file
│   └── has_summaries: boolean    # Whether AI summaries exist
│
└── {owner}-{repo}/               # Raw documentation files
    ├── README.md
    └── docs/
        └── *.md
```

### Token Estimation Guide

| Operation | Typical Token Cost |
|-----------|-------------------|
| `list_repos()` | ~50 |
| `get_toc()` with summaries | 500-1500 |
| `get_toc()` without summaries | 200-400 |
| `get_toc_tree()` | 400-800 |
| `search_sections()` | 200-500 |
| `get_section()` | 200-2000 |
| `get_sections()` (3 sections) | 600-6000 |

**Comparison**:
- Full documentation load: 50,000-200,000 tokens
- Typical MCP workflow: 1,500-3,000 tokens
- **Savings: 94-97%**

---

## Changelog

### Version 1.0.0 (Current)
- Initial release
- Core tools: index, list, TOC, sections, search
- AI-powered summaries
- Local caching
- GitHub API integration

### Planned Features
- Full-text content search
- Automatic re-indexing on changes
- Support for other Git platforms
- Custom path configuration
- Webhook integration for live updates

---

## License

MIT License - See LICENSE file for details

---

**Last Updated**: 2024-01-15
**Version**: 1.0.0
**Maintainer**: [jgravelle](https://github.com/jgravelle)

---

*Need more help? Open an issue on [GitHub](https://github.com/jgravelle/jdocmunch-mcp/issues)!*
