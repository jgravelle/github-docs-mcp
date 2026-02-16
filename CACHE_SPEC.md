# Cache Specification

## Overview

jDocMunch MCP stores indexed documentation in a local cache to enable fast, deterministic retrieval without repeated parsing or API calls. This document defines the cache layout, JSON schema, versioning rules, and invalidation behavior.

---

## Storage Location

* **Default:** `~/.doc-index/`
* **Override:** Provide a custom path via tool parameters or initialize `IndexStore(base_path=...)`.

---

## Directory Layout

```
~/.doc-index/
  ├── {owner}-{name}.json        # Repository index metadata
  ├── {owner}-{name}/            # Cached raw documentation files
  │   ├── README.md
  │   ├── docs/
  │   │   ├── guide.md
  │   │   └── api.md
  │   └── ...
```

### Cache Key

Each repository uses the key `{owner}-{name}`:

* **GitHub repositories:** `owner` is the GitHub user or organization
  Example: `facebook-react`
* **Local directories:** `owner` is `local`
  Example: `local-my-project`

---

## Index JSON Schema

```json
{
  "repo": "owner/name",
  "owner": "owner",
  "name": "name",
  "indexed_at": "2025-01-15T10:30:00.000000",
  "index_version": 1,
  "commit_hash": "abc123...",
  "file_hashes": {
    "README.md": "sha256...",
    "docs/guide.md": "sha256..."
  },
  "doc_files": [
    "README.md",
    "docs/guide.md"
  ],
  "sections": [...]
}
```

---

## Field Definitions

| Field           | Type    | Description                                        |
| --------------- | ------- | -------------------------------------------------- |
| `repo`          | string  | Repository identifier (`owner/name`)               |
| `owner`         | string  | Repository owner or `local`                        |
| `name`          | string  | Repository name                                    |
| `indexed_at`    | string  | ISO-8601 UTC timestamp                             |
| `index_version` | integer | Cache schema version                               |
| `commit_hash`   | string  | Git commit at indexing time (empty if unavailable) |
| `file_hashes`   | object  | File path → content hash mapping                   |
| `doc_files`     | array   | Ordered list of indexed documentation files        |
| `sections`      | array   | Parsed section metadata entries                    |

---

## Section Schema

| Field         | Type    | Description                                      |
| ------------- | ------- | ------------------------------------------------ |
| `id`          | string  | Stable section identifier                        |
| `file`        | string  | Source file path relative to repo root           |
| `path`        | string  | Navigation path (`file#slug`)                    |
| `title`       | string  | Section heading text                             |
| `depth`       | integer | Heading depth (Markdown 1-6, RST document order) |
| `parent`      | string? | Parent section ID or `null`                      |
| `summary`     | string  | AI or keyword-based summary                      |
| `keywords`    | array   | Extracted keywords (max 20)                      |
| `line_count`  | integer | Section line count                               |
| `byte_offset` | integer | Byte offset from file start                      |
| `byte_length` | integer | Section byte length                              |

---

## Section ID Generation

IDs are generated deterministically:

1. **File prefix:** `slugify(Path(filename).stem)`
2. **Heading slug:** `slugify(heading_text)`
3. **Combined ID:** `{file_prefix}-{slug}`
4. **Collision handling:** append `-{md5(content[:200])[:6]}`
5. **Root section:** `{file_prefix}-root`
6. **Headingless chunks:** `{file_prefix}-part-{index}`

This ensures IDs remain stable across re-indexing when content is unchanged.

---

## Versioning Rules

* `index_version` tracks the schema version (`CURRENT_INDEX_VERSION`).
* If a stored cache version is older than the current version, it is treated as stale and ignored.
* Optional new fields are added using `setdefault()` to preserve forward compatibility.

### Increment the version when:

* Renaming or removing schema fields
* Changing section ID generation
* Changing the meaning of existing fields

### Do not increment when:

* Adding optional fields
* Adding new top-level metadata fields

---

## Invalidation Triggers

| Trigger             | Behavior                               |
| ------------------- | -------------------------------------- |
| Version mismatch    | Cache discarded; full reindex required |
| `delete_index` tool | Cache files removed                    |
| Manual deletion     | Cache missing; reindex required        |
| Incremental reindex | Only changed files re-parsed           |

---

## Incremental Reindexing

During reindex:

1. Load existing `file_hashes`
2. Compare current file hashes
3. Reparse changed files
4. Add new files
5. Remove deleted files
6. Preserve unchanged sections

Implemented via `IndexStore.update_index()`.

---

## Line Ending Normalization

Cached raw files are normalized to `\n` line endings to ensure byte offsets remain valid across platforms, including Windows environments.

---

## Backward Compatibility Policy

* Outdated caches are silently discarded and rebuilt.
* No automatic migrations are performed.
* A full reindex always produces a valid cache.
