
# jDocMunch MCP
## Precision Documentation Intelligence for AI Agents

**Stop loading entire documentation sets. Start retrieving exactly what you need.**

jDocMunch MCP transforms large documentation repositories into a structured, queryable intelligence layer for AI agents. Instead of fetching hundreds of files per query, agents retrieve only the relevant documentation sections — dramatically reducing token cost, latency, and API calls.

---

## Why jDocMunch Exists

Large documentation repositories often contain hundreds or thousands of files. Traditional AI workflows repeatedly load entire documentation sets for each query, creating:

- Massive token waste
- Slow responses
- Rate‑limit bottlenecks
- High operational cost

jDocMunch solves this by indexing documentation once and enabling precision retrieval for every subsequent query.

---

## Proven Real‑World Benchmark

**Repository:** openclaw/openclaw  
**Documentation size:** 583 files (~812K tokens)

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

## How It Works

1. Index documentation once
2. Build a structured Table‑of‑Contents index
3. Cache semantic relationships locally
4. Serve precision MCP queries for agents
5. Retrieve only the relevant documentation fragments

After indexing, queries typically consume **~500 tokens instead of hundreds of thousands**.

---

## Key Benefits

- 70–99% token reduction in real workflows
- Near‑instant documentation queries
- Zero repeated API calls after indexing
- Ideal for multi‑agent systems and autonomous workflows
- Works with any local or cloned repository

---

## Installation

```bash
git clone https://github.com/jgravelle/jdocmunch-mcp
cd jdocmunch-mcp
pip install -r requirements.txt
```

Configure your MCP client (Claude Desktop, OpenClaw, etc.) to launch the server and point it to the documentation repository you want indexed.

---

## Vision

jDocMunch provides the **documentation intelligence layer** for the agent era — enabling autonomous systems to reason over large knowledge bases efficiently, cheaply, and reliably.

---

## License
MIT
