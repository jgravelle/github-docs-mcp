# Security Policy

## Overview

jDocMunch MCP operates as a local MCP server that indexes documentation from local directories and GitHub repositories. It processes documentation content locally and optionally sends section excerpts to external AI services for summarization.

This document defines the system threat model, data boundaries, and the controls implemented to prevent data leakage, path escape, and credential exposure.

---

## Threat Model

### Trust Boundaries

1. **Local filesystem**
   Reads files from user-specified directories. Indexing must never escape the configured base path via path traversal or symlink redirection.

2. **GitHub API**
   Retrieves repository contents using optional credentials (`GITHUB_TOKEN`). Credentials must never be exposed in logs or responses.

3. **AI summarization services**
   Only section excerpts (not full repositories) may be transmitted to Anthropic APIs or a local Ollama instance for summary generation.

4. **MCP clients**
   Tool arguments are user-provided. Paths and inputs are validated before filesystem access.

---

## Data Flow

```
Local Directory / GitHub API
        |
        v
   Indexer (parse + hash)
        |
        v
Local Cache (~/.doc-index/)  --->  AI Summarizer (Anthropic / Ollama)
        |                                   |
        v                                   v
   MCP Tool Responses         Section summaries stored in cache
```

---

## Filesystem Access Controls

### Path Traversal Protection

All file paths are resolved using `Path.resolve()` and validated against the configured base directory. Paths resolving outside the allowed directory are rejected.

### Symlink Handling

* **Default:** Symlinks are not followed.
* When enabled, symlink targets are validated to ensure they remain within the base directory. Escaping links are skipped and logged.

### Directory Exclusions

Common generated or dependency directories are automatically excluded, including:

`.git`, `node_modules`, `__pycache__`, `venv`, `dist`, `build`
(see `SKIP_DIRS` in the indexing module for the full list).

---

## Credential and Secret Protection

### Sensitive File Filtering

Files matching known sensitive patterns are excluded from indexing:

* `.env`, `.env.local`
* `credentials.json`, `secrets.yaml`
* `.npmrc`, `.pypirc`, `.netrc`
* `*.pem`, `*.key`, `*.p12`
* `id_rsa*`, `id_ed25519*`

### Content Secret Scanning

File contents are scanned before indexing. Files containing detected credentials are skipped.

| Pattern                        | Description        |
| ------------------------------ | ------------------ |
| `-----BEGIN.*PRIVATE KEY-----` | Private keys       |
| `AKIA[0-9A-Z]{16}`             | AWS access keys    |
| `sk-ant-*`                     | Anthropic API keys |
| `ghp_*`                        | GitHub tokens      |
| `glpat-*`                      | GitLab tokens      |
| `xox[boaprs]-*`                | Slack tokens       |

Skipped files are logged and returned in the tool response (`skipped_secrets`).

### `.gitignore` Enforcement

Local indexing respects `.gitignore` rules using the `pathspec` library. Additional ignore patterns can be provided at runtime.

---

## Local-Only Mode

Setting `JDOCMUNCH_LOCAL_ONLY=true` enforces local operation:

* GitHub repository indexing disabled
* External summarization APIs disabled
* Local Ollama summarization still permitted

This mode supports air-gapped or privacy-sensitive environments.

---

## External Data Transmission

| Service        | Trigger                  | Data Sent                                  |
| -------------- | ------------------------ | ------------------------------------------ |
| GitHub API     | `index_repo`             | Repository file listings and file contents |
| Anthropic API  | Summarization (optional) | Section title + first ~2000 characters     |
| Ollama (local) | Summarization (optional) | Same content sent locally                  |

No external communication occurs during query operations (`get_toc`, `search_sections`, `get_section`). All query responses are served from the local cache.

---

## Cache Security

* Default cache location: `~/.doc-index/` (configurable)
* Stored data: JSON index metadata and raw documentation files
* No encryption is applied (cache mirrors source documentation)
* File and commit hashes provide integrity verification

See `CACHE_SPEC.md` for schema details.

---

## Environment Variables

| Variable               | Purpose                      | Sensitive |
| ---------------------- | ---------------------------- | --------- |
| `GITHUB_TOKEN`         | GitHub API authentication    | Yes       |
| `ANTHROPIC_API_KEY`    | Anthropic API authentication | Yes       |
| `OLLAMA_URL`           | Local Ollama server URL      | No        |
| `OLLAMA_MODEL`         | Ollama model name            | No        |
| `USE_OLLAMA`           | Enable Ollama summarization  | No        |
| `JDOCMUNCH_LOCAL_ONLY` | Enforce local-only operation | No        |

---

## Vulnerability Reporting

Security vulnerabilities may be reported privately by opening an issue at:

[https://github.com/jgravelle/jdocmunch-mcp/issues](https://github.com/jgravelle/jdocmunch-mcp/issues)

Include:

* Description of the issue
* Steps to reproduce
* Potential impact
* Suggested remediation (if available)

Reports are typically acknowledged within 48 hours.
