"""Generate standardized benchmark datasets for jDocMunch MCP."""

import os
import random
from pathlib import Path

DATASETS_DIR = Path(__file__).parent / "datasets"

LOREM = (
    "Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
    "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. "
    "Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris. "
)

TECH_WORDS = [
    "install", "configure", "deploy", "authenticate", "authorize",
    "database", "migration", "endpoint", "middleware", "controller",
    "component", "template", "routing", "caching", "logging",
    "testing", "debugging", "profiling", "monitoring", "scaling",
]


def _generate_md_file(title: str, num_sections: int = 5, lines_per_section: int = 10) -> str:
    """Generate a realistic markdown file."""
    lines = [f"# {title}\n"]
    lines.append(f"{LOREM}\n")

    for i in range(num_sections):
        heading = f"## {random.choice(TECH_WORDS).title()} {random.choice(TECH_WORDS).title()}"
        lines.append(f"\n{heading}\n")
        for _ in range(lines_per_section):
            word1 = random.choice(TECH_WORDS)
            word2 = random.choice(TECH_WORDS)
            lines.append(f"The `{word1}` module handles {word2} operations. {LOREM}")

        # Add a subsection
        sub_heading = f"### {random.choice(TECH_WORDS).title()} Details"
        lines.append(f"\n{sub_heading}\n")
        for _ in range(lines_per_section // 2):
            lines.append(f"- Configuration for `{random.choice(TECH_WORDS)}`: {LOREM[:80]}")

    return "\n".join(lines)


def generate_small():
    """Generate small dataset: 5 files."""
    out = DATASETS_DIR / "small"
    out.mkdir(parents=True, exist_ok=True)

    for i in range(5):
        content = _generate_md_file(f"Document {i+1}", num_sections=3, lines_per_section=5)
        (out / f"doc_{i+1}.md").write_text(content, encoding="utf-8")

    print(f"Small dataset: 5 files in {out}")


def generate_medium():
    """Generate medium dataset: 50 files in subdirectories."""
    out = DATASETS_DIR / "medium"
    out.mkdir(parents=True, exist_ok=True)

    dirs = ["docs", "guides", "api", "tutorials", "reference"]
    for d in dirs:
        (out / d).mkdir(exist_ok=True)

    for i in range(50):
        subdir = dirs[i % len(dirs)]
        content = _generate_md_file(f"Document {i+1}", num_sections=5, lines_per_section=8)
        (out / subdir / f"doc_{i+1}.md").write_text(content, encoding="utf-8")

    print(f"Medium dataset: 50 files in {out}")


def generate_large():
    """Generate large dataset: 500 files in subdirectories."""
    out = DATASETS_DIR / "large"
    out.mkdir(parents=True, exist_ok=True)

    dirs = ["docs", "guides", "api", "tutorials", "reference",
            "concepts", "howto", "changelog", "faq", "troubleshooting"]
    for d in dirs:
        (out / d).mkdir(exist_ok=True)

    for i in range(500):
        subdir = dirs[i % len(dirs)]
        content = _generate_md_file(f"Document {i+1}", num_sections=6, lines_per_section=10)
        (out / subdir / f"doc_{i+1}.md").write_text(content, encoding="utf-8")

    print(f"Large dataset: 500 files in {out}")


if __name__ == "__main__":
    random.seed(42)  # Reproducible
    generate_small()
    generate_medium()
    generate_large()
    print("All datasets generated.")
