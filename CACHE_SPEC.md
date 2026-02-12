# Cache Specification

## Overview

jDocMunch MCP stores indexed documentation in a local cache directory. This document describes the cache structure, JSON schema, versioning rules, and invalidation policy.

## Storage Location

- **Default**: `~/.doc-index/`
- **Override**: Pass `storage_path` parameter to any tool, or set programmatically via `IndexStore(base_path=...)`.

## Directory Layout

```
~/.doc-index/
  ├── {owner}-{name}.json          # Index JSON for each repo
  ├── {owner}-{name}/              # Raw content directory
  │   ├── README.md                # Cached raw files (line-ending normalized)
  │   ├── docs/
  │   │   ├── guide.md
  │   │   └── api.md
  │   └── ...
  └── ...
```

### Cache Key

The cache key for a repository is `{owner}-{name}`:

- **GitHub repos**: `owner` is the GitHub user/org, `name` is the repo name. E.g., `facebook-react`.
- **Local directories**: `owner` is always `local`, `name` is the directory basename. E.g., `local-my-project`.

## Index JSON Schema

```json
{
  "repo": "owner/name",
  "owner": "owner",
  "name": "name",
  "indexed_at": "2025-01-15T10:30:00.000000",
  "index_version": 1,
  "commit_hash": "abc123def456...",
  "file_hashes": {
    "README.md": "sha256hex...",
    "docs/guide.md": "sha256hex..."
  },
  "doc_files": [
    "README.md",
    "docs/guide.md"
  ],
  "sections": [
    {
      "id": "readme-installation",
      "file": "README.md",
      "path": "README.md#installation",
      "title": "Installation",
      "depth": 2,
      "parent": "readme-root",
      "summary": "How to install the package via pip or npm",
      "keywords": ["install", "pip", "npm", "setup"],
      "line_count": 15,
      "byte_offset": 1024,
      "byte_length": 512
    }
  ]
}
```

### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `repo` | string | Full repo identifier (`owner/name`) |
| `owner` | string | Repository owner or `local` |
| `name` | string | Repository name |
| `indexed_at` | string | ISO 8601 UTC timestamp of indexing |
| `index_version` | int | Schema version number (current: 1) |
| `commit_hash` | string | Git commit SHA at time of indexing (empty if unavailable) |
| `file_hashes` | object | Map of file path to content hash (SHA256 for local, git blob SHA for GitHub) |
| `doc_files` | array | Ordered list of all indexed file paths |
| `sections` | array | Parsed section metadata (see below) |

### Section Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique section identifier (stable across re-indexes if content unchanged) |
| `file` | string | Source file path relative to repo root |
| `path` | string | Navigation path (`file#slug` for headed sections, `file` for root) |
| `title` | string | Section heading text |
| `depth` | int | Heading depth (1-6 for markdown, document-order for RST, 0 for root) |
| `parent` | string? | Parent section ID or null for top-level sections |
| `summary` | string | One-line AI or keyword-based summary |
| `keywords` | array | Extracted technical keywords (max 20) |
| `line_count` | int | Number of lines in the section |
| `byte_offset` | int | Byte offset from start of file to section content |
| `byte_length` | int | Byte length of section content |

## Section ID Algorithm

Section IDs are generated as follows:

1. **File prefix**: `slugify(Path(filename).stem)` — strips extension using `Path.stem` (handles `.md`, `.markdown`, `.mdx`, `.rst`).
2. **Section slug**: `slugify(heading_text)` — converts heading to URL-friendly form.
3. **Full ID**: `{file_prefix}-{slug}`.
4. **Dedup**: If the ID already exists, append `-{md5(content[:200])[:6]}` — a 6-char content hash. This ensures IDs are stable even when sections are inserted before existing ones (unlike a counter).
5. **Root sections** (content before first heading): `{file_prefix}-root`.
6. **Headingless file chunks**: `{file_prefix}-part-{index}`.

## Versioning Rules

- The `index_version` field tracks the cache schema version.
- The current version is defined by `CURRENT_INDEX_VERSION` in `storage/index_store.py`.
- When loading a cache, if `index_version < CURRENT_INDEX_VERSION`, the cache is treated as **stale** and `load_index()` returns `None`, forcing a re-index.
- New fields are added with `setdefault()` for forward compatibility within the same version.

### When to Increment Version

Increment `CURRENT_INDEX_VERSION` when:
- Removing or renaming fields in the sections array.
- Changing the section ID generation algorithm.
- Changing the meaning of existing fields.

Do **not** increment when:
- Adding new optional fields (use `setdefault()` on load).
- Adding new top-level metadata fields.

## Invalidation Triggers

| Trigger | Behavior |
|---------|----------|
| `index_version` mismatch | Cache discarded, full re-index required |
| `delete_index` tool called | Cache files and content directory deleted |
| Manual file deletion | User deletes `{owner}-{name}.json` and/or `{owner}-{name}/` |
| Incremental reindex | Only changed files re-parsed (via `file_hashes` comparison) |

## Incremental Reindexing

When re-indexing a previously indexed repo:

1. Load existing index and its `file_hashes`.
2. Compare current file hashes against stored hashes.
3. **Changed files**: Re-parse all sections, replace in index.
4. **New files**: Parse and add to index.
5. **Deleted files**: Remove sections and cached content.
6. **Unchanged files**: Carry forward existing sections.

This is implemented via `IndexStore.update_index()`.

## Line Ending Normalization

Raw files saved to the cache directory are **normalized to `\n` line endings** regardless of the source platform. This ensures byte offsets computed during parsing remain valid on all platforms (including Windows where `\r\n` would otherwise shift offsets).

## Backward Compatibility Policy

- Old caches (version < current) are silently discarded. The user sees an "index not found" response and must re-index.
- The error message from `load_index()` returning `None` is the same as a missing index, keeping the UX simple.
- No automatic migration is performed. A full re-index is always safe and produces a correct cache.
