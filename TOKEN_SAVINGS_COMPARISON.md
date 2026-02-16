# Token Savings Comparison: jdocmunch-mcp vs Direct API Retrieval

## Test Scenario

* **Query:** “How to configure device tree overlays on Raspberry Pi”
* **Repository:** `raspberrypi/linux` (`rpi-6.12.y/Documentation`)

---

## Without MCP (Direct Retrieval)

### Step 1 — Fetch Documentation Listing

* API: `GET /repos/raspberrypi/linux/contents/Documentation`
* Response size: ~50,000 characters (metadata)
* Tokens consumed: ~12,500

### Step 2 — Fetch Relevant Files

Files retrieved:

* `Documentation/devicetree/overlay-notes.rst` (~5,365 chars)
* `Documentation/devicetree/booting-without-of.txt` (~8,000 chars)
* `Documentation/admin-guide/device-tree.rst` (~6,000 chars)

Total content: ~20,000 characters
Tokens consumed: ~5,000

### Step 3 — Search and Processing

* Local scanning across all downloaded content
* Additional fetches required if matches are incomplete

**Total (without MCP): ~17,500 tokens**

---

## With MCP (Indexed Retrieval)

### Step 1 — Index Repository (one-time)

* Tool: `index_repo`
* Action: Parse documentation, generate summaries, store locally
* Tokens in client context: **0**

### Step 2 — Retrieve Table of Contents

* Tool: `get_toc`
* Response size: ~1,500 characters
* Tokens consumed: ~375

### Step 3 — Search Sections

* Tool: `search_sections(query="device tree overlay")`
* Response size: ~800 characters
* Tokens consumed: ~200

### Step 4 — Retrieve Target Section

* Tool: `get_section(section="devicetree/overlay-notes")`
* Response size: ~5,365 characters
* Tokens consumed: ~1,341

**Total (with MCP): ~1,916 tokens**

---

## Savings Summary

| Metric          | Without MCP       | With MCP               | Savings              |
| --------------- | ----------------- | ---------------------- | -------------------- |
| Tokens consumed | ~17,500           | ~1,916                 | **~89%**             |
| API calls       | 4+                | 3                      | Reduced              |
| Content loaded  | Entire files      | Relevant sections only | **90%+ reduction**   |
| Response time   | Network-dependent | Local retrieval        | Significantly faster |

---

## Cost Impact (Illustrative)

Assuming $0.015 per 1K tokens:

| Scenario    | Cost per Query              |
| ----------- | --------------------------- |
| Without MCP | ~$0.26                      |
| With MCP    | ~$0.03                      |
| **Savings** | **~$0.23 per query (~89%)** |

### At Scale (100 queries/day)

* Without MCP: ~$26.25/day (~$788/month)
* With MCP: ~$2.87/day (~$86/month)
* **Estimated monthly savings:** ~$702

---

## Key Advantages

* **Selective loading:** Only required documentation sections enter context
* **Structured discovery:** Summarized TOC enables rapid navigation
* **Semantic search:** Faster identification of relevant material
* **Local caching:** Queries require no repeated repository downloads
* **Predictable token usage:** Query cost scales with relevance, not repository size

---

## Operational Flow

```
User Query
    |
    v
Indexed MCP Server
    ├── Pre-indexed repository sections
    ├── Local search across summaries
    └── Retrieve only required sections
           |
           v
    Context window receives only relevant material
```

Typical context footprint: ~1,900 tokens instead of ~15,000+.

---

## Cost Separation: Indexing vs Query

| Phase             | Token Impact               | Frequency           |
| ----------------- | -------------------------- | ------------------- |
| Indexing          | External to client context | Once per repository |
| TOC retrieval     | ~375–600 tokens            | Once per session    |
| Search            | ~200–400 tokens            | Per search          |
| Section retrieval | ~200–1,500 tokens          | Per section         |

Indexing costs occur within the MCP server process and do not consume client context tokens.

---

## Reproducing the Benchmark

```bash
python benchmarks/run_benchmark.py --generate --dataset medium
```

Or manually:

1. Index a repository (`index_local` or `index_repo`)
2. Query using `get_toc`, `search_sections`, and `get_section`
3. Compare token counts between indexed retrieval and raw file loading

See `benchmarks/README.md` for methodology details.
