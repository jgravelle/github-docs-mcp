# jDocMunch MCP Benchmarks

## Quick Start

```bash
# Generate datasets and run all benchmarks
python benchmarks/run_benchmark.py --generate

# Run specific dataset
python benchmarks/run_benchmark.py --dataset medium

# Save results as JSON
python benchmarks/run_benchmark.py --output results.json
```

## Datasets

| Dataset | Files | Approximate Size | Purpose |
|---------|-------|-----------------|---------|
| small | 5 | ~50 KB | Quick smoke test |
| medium | 50 | ~500 KB | Typical project |
| large | 500 | ~5 MB | Large documentation repo |

Datasets are generated deterministically (seed=42) via `generate_datasets.py`.

## Measurements

| Measurement | Description |
|-------------|-------------|
| `full_index` | Time to index entire dataset from scratch |
| `reindex_no_changes` | Time to re-index when nothing changed |
| `get_toc` | Table of contents retrieval |
| `get_toc_filtered` | TOC with path_prefix filter |
| `get_toc_tree` | Hierarchical tree retrieval |
| `search_sections` | Keyword search across all sections |
| `get_section` | Single section content retrieval |
| `get_sections_batch_3` | Batch retrieval of 3 sections |
| `get_document_outline` | Single file outline |
| `list_repos` | List all indexed repos |
| `session_3_queries` | Simulated session: TOC + 3 search+retrieve cycles |

## Token Counting

Token counts are approximate (~4 characters per token). This is the number of tokens in the JSON response that would be sent to an MCP client.

## Reproducibility

- Datasets are generated with a fixed random seed
- System info (platform, Python version, processor) is recorded in results
- Run on a quiet machine for consistent timing results
