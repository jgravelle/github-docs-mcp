"""
Reproducible benchmark harness for jDocMunch MCP.

Measures:
- Indexing cost (full index)
- Incremental indexing cost (1 file changed)
- Query cost per tool (get_toc, search_sections, get_section)
- Session cost (typical multi-query session)

Usage:
    python benchmarks/run_benchmark.py [--dataset small|medium|large] [--output results.json]
"""

import argparse
import asyncio
import json
import os
import platform
import sys
import tempfile
import time
from pathlib import Path

# Add project src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from jdocmunch_mcp.tools.index_local import index_local
from jdocmunch_mcp.tools.get_toc import get_toc, get_toc_tree, get_document_outline
from jdocmunch_mcp.tools.search_sections import search_sections
from jdocmunch_mcp.tools.get_section import get_section, get_sections
from jdocmunch_mcp.tools.list_repos import list_repos
from jdocmunch_mcp.storage.index_store import IndexStore


def _count_tokens_approx(text: str) -> int:
    """Approximate token count (~4 chars per token for English text)."""
    return len(text) // 4


class BenchmarkResult:
    """Collects benchmark measurements."""

    def __init__(self, dataset_name: str):
        self.dataset = dataset_name
        self.measurements: list[dict] = []
        self.system_info = {
            "platform": platform.system(),
            "platform_version": platform.version(),
            "python_version": platform.python_version(),
            "processor": platform.processor(),
        }

    def record(self, name: str, elapsed_ms: float, token_count: int, **extra):
        self.measurements.append({
            "name": name,
            "elapsed_ms": round(elapsed_ms, 2),
            "token_count": token_count,
            **extra,
        })

    def to_dict(self) -> dict:
        return {
            "dataset": self.dataset,
            "system_info": self.system_info,
            "measurements": self.measurements,
        }

    def to_markdown(self) -> str:
        lines = [
            f"# Benchmark Results: {self.dataset}",
            "",
            f"**Platform**: {self.system_info['platform']} {self.system_info['platform_version']}",
            f"**Python**: {self.system_info['python_version']}",
            "",
            "| Measurement | Time (ms) | Tokens (approx) | Details |",
            "|-------------|-----------|-----------------|---------|",
        ]
        for m in self.measurements:
            extra = {k: v for k, v in m.items() if k not in ("name", "elapsed_ms", "token_count")}
            details = ", ".join(f"{k}={v}" for k, v in extra.items()) if extra else "-"
            lines.append(f"| {m['name']} | {m['elapsed_ms']} | {m['token_count']} | {details} |")
        return "\n".join(lines)


async def run_benchmark(dataset_path: str, storage_dir: str) -> BenchmarkResult:
    """Run full benchmark suite on a dataset."""
    dataset_name = Path(dataset_path).name
    result = BenchmarkResult(dataset_name)

    # 1. Full indexing
    t0 = time.perf_counter()
    index_result = await index_local(
        path=dataset_path,
        use_ai_summaries=False,
        storage_path=storage_dir,
    )
    t1 = time.perf_counter()

    index_json = json.dumps(index_result, indent=2)
    result.record(
        "full_index",
        (t1 - t0) * 1000,
        _count_tokens_approx(index_json),
        file_count=index_result.get("file_count", 0),
        section_count=index_result.get("section_count", 0),
    )

    repo = index_result.get("repo", "")
    if not repo:
        print(f"  Indexing failed: {index_result.get('error', 'unknown')}")
        return result

    # 2. Incremental reindex (same directory, no changes — should be fast)
    t0 = time.perf_counter()
    reindex_result = await index_local(
        path=dataset_path,
        use_ai_summaries=False,
        storage_path=storage_dir,
    )
    t1 = time.perf_counter()
    result.record(
        "reindex_no_changes",
        (t1 - t0) * 1000,
        _count_tokens_approx(json.dumps(reindex_result)),
    )

    # 3. get_toc
    t0 = time.perf_counter()
    toc_result = get_toc(repo=repo, storage_path=storage_dir)
    t1 = time.perf_counter()
    toc_json = json.dumps(toc_result, indent=2)
    result.record("get_toc", (t1 - t0) * 1000, _count_tokens_approx(toc_json))

    # 4. get_toc with path_prefix filter
    t0 = time.perf_counter()
    toc_filtered = get_toc(repo=repo, storage_path=storage_dir, path_prefix="docs/")
    t1 = time.perf_counter()
    result.record(
        "get_toc_filtered",
        (t1 - t0) * 1000,
        _count_tokens_approx(json.dumps(toc_filtered)),
    )

    # 5. get_toc_tree
    t0 = time.perf_counter()
    tree_result = get_toc_tree(repo=repo, storage_path=storage_dir)
    t1 = time.perf_counter()
    result.record("get_toc_tree", (t1 - t0) * 1000, _count_tokens_approx(json.dumps(tree_result)))

    # 6. search_sections
    t0 = time.perf_counter()
    search_result = search_sections(repo=repo, query="install configure", storage_path=storage_dir)
    t1 = time.perf_counter()
    search_json = json.dumps(search_result, indent=2)
    result.record(
        "search_sections",
        (t1 - t0) * 1000,
        _count_tokens_approx(search_json),
        result_count=search_result.get("result_count", 0),
    )

    # 7. get_section (first result from search)
    if search_result.get("results"):
        section_id = search_result["results"][0]["id"]
        t0 = time.perf_counter()
        section_result = get_section(repo=repo, section_id=section_id, storage_path=storage_dir)
        t1 = time.perf_counter()
        result.record(
            "get_section",
            (t1 - t0) * 1000,
            _count_tokens_approx(json.dumps(section_result)),
        )

    # 8. get_sections (batch of 3)
    if len(search_result.get("results", [])) >= 3:
        ids = [r["id"] for r in search_result["results"][:3]]
        t0 = time.perf_counter()
        batch_result = get_sections(repo=repo, section_ids=ids, storage_path=storage_dir)
        t1 = time.perf_counter()
        result.record(
            "get_sections_batch_3",
            (t1 - t0) * 1000,
            _count_tokens_approx(json.dumps(batch_result)),
        )

    # 9. get_document_outline
    if toc_result.get("files"):
        file_path = toc_result["files"][0]
        t0 = time.perf_counter()
        outline_result = get_document_outline(repo=repo, file_path=file_path, storage_path=storage_dir)
        t1 = time.perf_counter()
        result.record(
            "get_document_outline",
            (t1 - t0) * 1000,
            _count_tokens_approx(json.dumps(outline_result)),
        )

    # 10. list_repos
    t0 = time.perf_counter()
    list_result = list_repos(storage_path=storage_dir)
    t1 = time.perf_counter()
    result.record("list_repos", (t1 - t0) * 1000, _count_tokens_approx(json.dumps(list_result)))

    # 11. Simulated session: toc + 3 searches + 3 section reads
    t0 = time.perf_counter()
    session_tokens = 0

    toc = get_toc(repo=repo, storage_path=storage_dir)
    session_tokens += _count_tokens_approx(json.dumps(toc))

    for query in ["install", "configure deploy", "testing debugging"]:
        sr = search_sections(repo=repo, query=query, max_results=3, storage_path=storage_dir)
        session_tokens += _count_tokens_approx(json.dumps(sr))
        if sr.get("results"):
            sec = get_section(repo=repo, section_id=sr["results"][0]["id"], storage_path=storage_dir)
            session_tokens += _count_tokens_approx(json.dumps(sec))

    t1 = time.perf_counter()
    result.record("session_3_queries", (t1 - t0) * 1000, session_tokens)

    return result


async def main():
    parser = argparse.ArgumentParser(description="jDocMunch MCP Benchmark")
    parser.add_argument("--dataset", choices=["small", "medium", "large", "all"], default="all")
    parser.add_argument("--output", default=None, help="Output JSON file path")
    parser.add_argument("--generate", action="store_true", help="Generate datasets first")
    args = parser.parse_args()

    datasets_dir = Path(__file__).parent / "datasets"

    if args.generate or not datasets_dir.exists():
        print("Generating benchmark datasets...")
        from generate_datasets import generate_small, generate_medium, generate_large
        import random
        random.seed(42)
        generate_small()
        generate_medium()
        generate_large()

    if args.dataset == "all":
        dataset_names = ["small", "medium", "large"]
    else:
        dataset_names = [args.dataset]

    all_results = []

    for name in dataset_names:
        dataset_path = datasets_dir / name
        if not dataset_path.exists():
            print(f"Dataset {name} not found at {dataset_path}. Run with --generate first.")
            continue

        print(f"\nBenchmarking dataset: {name}")
        print("=" * 50)

        with tempfile.TemporaryDirectory() as tmpdir:
            result = await run_benchmark(str(dataset_path), tmpdir)
            all_results.append(result)

            print(result.to_markdown())
            print()

    # Output JSON
    if args.output:
        output_data = [r.to_dict() for r in all_results]
        with open(args.output, "w") as f:
            json.dump(output_data, f, indent=2)
        print(f"\nResults saved to {args.output}")


if __name__ == "__main__":
    asyncio.run(main())
