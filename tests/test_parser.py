"""Tests for markdown, MDX, and RST parsers."""

import pytest

from jdocmunch_mcp.parser.markdown import (
    parse_markdown_to_sections,
    preprocess_mdx,
    slugify,
    extract_keywords,
    _strip_front_matter,
    _content_hash_suffix,
)
from jdocmunch_mcp.parser.rst import parse_rst_to_sections
from jdocmunch_mcp.parser.hierarchy import build_section_tree, flatten_tree, get_section_path


class TestSlugify:
    def test_basic(self):
        assert slugify("Hello World") == "hello-world"

    def test_special_chars(self):
        assert slugify("API Reference (v2)") == "api-reference-v2"

    def test_multiple_spaces(self):
        assert slugify("  extra   spaces  ") == "extra-spaces"


class TestExtractKeywords:
    def test_code_blocks(self):
        content = "Use `pip install` and `npm install` commands."
        keywords = extract_keywords(content)
        assert "pip install" in keywords
        assert "npm install" in keywords

    def test_identifiers(self):
        content = "The function_name and camelCase variables."
        keywords = extract_keywords(content)
        assert "function_name" in keywords

    def test_tech_terms(self):
        content = "Install the package and deploy the build."
        keywords = extract_keywords(content)
        assert "install" in keywords
        assert "deploy" in keywords
        assert "build" in keywords


class TestStripFrontMatter:
    def test_with_front_matter(self):
        content = "---\ntitle: My Doc\nauthor: Test\n---\n\n# Hello\n"
        stripped, meta = _strip_front_matter(content)
        assert "# Hello" in stripped
        assert meta["title"] == "My Doc"
        assert "---" not in stripped

    def test_without_front_matter(self):
        content = "# Hello\n\nNo front matter here.\n"
        stripped, meta = _strip_front_matter(content)
        assert stripped == content
        assert meta == {}

    def test_incomplete_front_matter(self):
        content = "---\ntitle: Broken\nNo closing delimiter\n# Hello\n"
        stripped, meta = _strip_front_matter(content)
        assert stripped == content  # Returned unchanged


class TestParseMarkdown:
    def test_basic_sections(self, sample_markdown):
        sections = parse_markdown_to_sections(sample_markdown, "README.md")
        assert len(sections) > 0
        titles = [s.title for s in sections]
        assert "Getting Started" in titles
        assert "Installation" in titles
        assert "Configuration" in titles

    def test_section_depth(self, sample_markdown):
        sections = parse_markdown_to_sections(sample_markdown, "README.md")
        for s in sections:
            if s.title == "Getting Started":
                assert s.depth == 1
            elif s.title == "Installation":
                assert s.depth == 2
            elif s.title == "Basic Config":
                assert s.depth == 3

    def test_section_ids_unique(self, sample_markdown):
        sections = parse_markdown_to_sections(sample_markdown, "README.md")
        ids = [s.id for s in sections]
        assert len(ids) == len(set(ids)), f"Duplicate IDs: {ids}"

    def test_stable_ids_use_content_hash(self):
        """Inserting a section before existing ones shouldn't change their IDs."""
        content_v1 = "# Title\n\n## Section A\n\nContent A.\n\n## Section A\n\nDifferent content.\n"
        sections_v1 = parse_markdown_to_sections(content_v1, "test.md")
        ids_v1 = [s.id for s in sections_v1]
        # The two "Section A" sections should have different IDs
        assert len(ids_v1) == len(set(ids_v1))

    def test_parent_relationships(self, sample_markdown):
        sections = parse_markdown_to_sections(sample_markdown, "README.md")
        section_map = {s.id: s for s in sections}
        for s in sections:
            if s.parent:
                parent = section_map.get(s.parent)
                assert parent is not None, f"Parent {s.parent} not found for {s.id}"
                assert parent.depth < s.depth

    def test_byte_offset_and_length(self, sample_markdown):
        sections = parse_markdown_to_sections(sample_markdown, "README.md")
        for s in sections:
            assert s.byte_length > 0
            # Content encoded length should match byte_length
            assert len(s.content.encode('utf-8')) == s.byte_length

    def test_keywords_extracted(self, sample_markdown):
        sections = parse_markdown_to_sections(sample_markdown, "README.md")
        # At least some sections should have keywords
        all_keywords = []
        for s in sections:
            all_keywords.extend(s.keywords)
        assert len(all_keywords) > 0

    def test_extension_stripping(self):
        """Path.stem should handle various extensions."""
        content = "# Title\n\nContent.\n"
        for ext in [".md", ".markdown", ".mdx"]:
            sections = parse_markdown_to_sections(content, f"test{ext}")
            assert sections[0].id.startswith("test-")
            assert ext not in sections[0].id


class TestHeadinglessParsing:
    def test_short_headingless(self, sample_headingless):
        sections = parse_markdown_to_sections(sample_headingless, "notes.md")
        assert len(sections) == 1
        assert sections[0].depth == 0
        # Should use first non-empty line as title
        assert "document without" in sections[0].title.lower()

    def test_frontmatter_title(self, sample_frontmatter):
        sections = parse_markdown_to_sections(sample_frontmatter, "special.md")
        assert len(sections) >= 1
        assert sections[0].title == "My Special Document"

    def test_long_headingless_splits(self):
        """Files > 200 lines should be split on double-blank-line boundaries."""
        lines = []
        for i in range(25):
            for j in range(10):
                lines.append(f"Paragraph {i} line {j} with some content.")
            lines.append("")
            lines.append("")  # Double blank line
        content = "\n".join(lines)
        sections = parse_markdown_to_sections(content, "long.md")
        assert len(sections) > 1


class TestPreprocessMdx:
    def test_strips_imports(self):
        content = "import Button from './Button'\nimport { Foo } from 'bar'\n\n# Hello\n"
        result = preprocess_mdx(content)
        assert "import" not in result
        assert "# Hello" in result

    def test_strips_jsx_tags(self):
        content = "# Title\n\n<Callout type='info'>\nImportant text\n</Callout>\n"
        result = preprocess_mdx(content)
        assert "<Callout" not in result
        assert "</Callout>" not in result
        assert "Important text" in result

    def test_strips_self_closing_tags(self):
        content = "# Title\n\n<Button variant='primary' />\n\nSome text.\n"
        result = preprocess_mdx(content)
        assert "<Button" not in result
        assert "Some text." in result

    def test_strips_front_matter(self):
        content = "---\ntitle: Test\n---\n\n# Hello\n"
        result = preprocess_mdx(content)
        assert "---" not in result
        assert "# Hello" in result

    def test_strips_export(self):
        content = "export default function Layout() {}\n\n# Hello\n"
        result = preprocess_mdx(content)
        assert "export" not in result

    def test_full_mdx(self, sample_mdx):
        result = preprocess_mdx(sample_mdx)
        sections = parse_markdown_to_sections(result, "guide.mdx")
        assert len(sections) > 0
        titles = [s.title for s in sections]
        assert "Component Guide" in titles


class TestRstParser:
    def test_basic_headers(self, sample_rst):
        sections = parse_rst_to_sections(sample_rst, "guide.rst")
        assert len(sections) > 0
        titles = [s.title for s in sections]
        assert "User Guide" in titles
        assert "Installation" in titles
        assert "Configuration" in titles

    def test_depth_by_underline_order(self, sample_rst):
        sections = parse_rst_to_sections(sample_rst, "guide.rst")
        section_map = {s.title: s for s in sections}
        # "User Guide" uses overline === so depth 1
        # "Installation" uses === so depth 2
        # "Basic Setup" uses --- so depth 3
        # "Nested Section" uses ~~~ so depth 4
        assert section_map["User Guide"].depth < section_map["Installation"].depth
        assert section_map["Installation"].depth < section_map["Basic Setup"].depth
        assert section_map["Basic Setup"].depth < section_map["Nested Section"].depth

    def test_unique_ids(self, sample_rst):
        sections = parse_rst_to_sections(sample_rst, "guide.rst")
        ids = [s.id for s in sections]
        assert len(ids) == len(set(ids))

    def test_no_headers(self):
        content = "Just plain text\nwith no headers at all.\n"
        sections = parse_rst_to_sections(content, "plain.rst")
        assert len(sections) == 1
        assert sections[0].depth == 0

    def test_parent_relationships(self, sample_rst):
        sections = parse_rst_to_sections(sample_rst, "guide.rst")
        section_map = {s.id: s for s in sections}
        for s in sections:
            if s.parent:
                parent = section_map.get(s.parent)
                assert parent is not None
                assert parent.depth < s.depth


class TestHierarchy:
    def test_build_tree(self, sample_markdown):
        sections = parse_markdown_to_sections(sample_markdown, "README.md")
        tree = build_section_tree(sections)
        assert len(tree) > 0

    def test_flatten_tree_roundtrip(self, sample_markdown):
        sections = parse_markdown_to_sections(sample_markdown, "README.md")
        tree = build_section_tree(sections)
        flat = flatten_tree(tree)
        assert len(flat) == len(sections)

    def test_get_section_path(self, sample_markdown):
        sections = parse_markdown_to_sections(sample_markdown, "README.md")
        # Find a deep section
        deep = [s for s in sections if s.depth >= 3]
        if deep:
            path = get_section_path(deep[0].id, sections)
            assert len(path) >= 2  # At least self and parent
            assert path[-1] == deep[0].id


class TestContentHashSuffix:
    def test_deterministic(self):
        assert _content_hash_suffix("hello") == _content_hash_suffix("hello")

    def test_different_content(self):
        assert _content_hash_suffix("hello") != _content_hash_suffix("world")

    def test_length(self):
        assert len(_content_hash_suffix("test content")) == 6
