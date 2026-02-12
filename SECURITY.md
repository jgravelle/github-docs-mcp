# Security Policy

## Threat Model

jDocMunch MCP operates as a local MCP server that indexes documentation from local directories and GitHub repositories. It processes file content and optionally sends section text to external AI services for summarization.

### Trust Boundaries

1. **Local filesystem** -- The server reads files from user-specified directories. It must not escape the base directory via symlinks or path traversal.
2. **GitHub API** -- The server fetches public/private repository content. Credentials (GITHUB_TOKEN) must not leak.
3. **AI summarization** -- Section content (not full files) is sent to Anthropic API or a local Ollama instance for one-line summaries.
4. **MCP clients** -- Any MCP client can invoke tools. The server trusts tool arguments but validates paths.

### Data Flow

```
Local Directory / GitHub API
        |
        v
  Indexer (parse + hash)
        |
        v
  Local Cache (~/.doc-index/)     --->  AI Summarizer (Anthropic / Ollama)
        |                                      |
        v                                      v
  MCP Tool Responses              Section summaries stored in cache
```

## Filesystem Access Controls

### Path Traversal Protection

All file paths are resolved to absolute paths and validated against the base directory using `Path.resolve()` and `is_relative_to()`. Any path that resolves outside the base directory is rejected.

### Symlink Handling

- **Default**: Symlinks are **not followed** (`follow_symlinks=False`).
- When `follow_symlinks=True`, each symlink target is validated to remain within the base directory. Symlinks that escape the base are logged and skipped.

### Directory Exclusions

The following directories are always skipped: `.git`, `node_modules`, `__pycache__`, `venv`, `dist`, `build`, and others (see `SKIP_DIRS` in `index_local.py`).

## Credential & Secret Handling

### Sensitive File Filtering

Files matching known sensitive patterns are **never indexed**:

- **Filenames**: `.env`, `.env.local`, `credentials.json`, `secrets.yaml`, `.npmrc`, `.pypirc`, `.netrc`
- **Glob patterns**: `*.pem`, `*.key`, `*.p12`, `id_rsa*`, `id_ed25519*`

### Content Scanning

After reading file content, the server scans for secret patterns before indexing:

| Pattern | Description |
|---------|-------------|
| `-----BEGIN.*PRIVATE KEY-----` | Private keys |
| `AKIA[0-9A-Z]{16}` | AWS access keys |
| `sk-ant-*` | Anthropic API keys |
| `ghp_*` | GitHub personal access tokens |
| `glpat-*` | GitLab personal access tokens |
| `xox[boaprs]-*` | Slack tokens |

Files containing detected secrets are **skipped** and logged as warnings. The tool response includes a `skipped_secrets` list so the user knows which files were excluded.

### .gitignore Respect

Local indexing respects `.gitignore` rules at the base directory using the `pathspec` library. Users can also pass `extra_ignore_patterns` for additional exclusions.

## Local-Only Mode

Set `JDOCMUNCH_LOCAL_ONLY=true` to restrict the server:

- `index_repo` returns an error (no GitHub API calls).
- AI summarization skips the Anthropic API and uses simple keyword-based summaries only.
- Ollama (local) summarization is still permitted.

This mode is suitable for air-gapped environments or when no data should leave the local machine.

## Data Transmitted to External Services

| Service | When | What is sent |
|---------|------|-------------|
| GitHub API | `index_repo` | Repository file listing, raw file content |
| Anthropic API | Summarization (if enabled) | Section title + first 2000 chars of section content |
| Ollama (local) | Summarization (if enabled) | Same as Anthropic, but to localhost |

**No data is sent during query operations** (`get_toc`, `search_sections`, `get_section`). All queries are answered from the local cache.

## Cache Security

- Cache is stored at `~/.doc-index/` by default (configurable via `storage_path`).
- Cache files are plain JSON indexes and raw markdown files.
- No encryption is applied to cached content (it mirrors the source documentation).
- Cache includes file hashes (SHA256) and commit hashes for integrity verification.
- See [CACHE_SPEC.md](CACHE_SPEC.md) for full schema documentation.

## Environment Variables

| Variable | Purpose | Sensitive? |
|----------|---------|------------|
| `GITHUB_TOKEN` | GitHub API authentication | Yes |
| `ANTHROPIC_API_KEY` | Anthropic API authentication | Yes |
| `OLLAMA_URL` | Ollama server URL | No |
| `OLLAMA_MODEL` | Ollama model name | No |
| `USE_OLLAMA` | Enable Ollama summarization | No |
| `JDOCMUNCH_LOCAL_ONLY` | Restrict to local-only operation | No |

## Vulnerability Reporting

If you discover a security vulnerability, please report it by opening a private issue at:

https://github.com/jgravelle/jdocmunch-mcp/issues

Please include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

We aim to acknowledge reports within 48 hours.
