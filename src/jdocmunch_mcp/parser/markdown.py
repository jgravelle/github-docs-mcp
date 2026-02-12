"""Markdown parsing to extract sections with hierarchy."""

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class Section:
    """A section extracted from markdown."""
    id: str
    file: str
    path: str
    title: str
    depth: int
    parent: Optional[str]
    content: str
    summary: str = ""
    keywords: list[str] = field(default_factory=list)
    line_count: int = 0
    byte_offset: int = 0
    byte_length: int = 0


def slugify(text: str) -> str:
    """Convert text to a URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text


def extract_keywords(content: str) -> list[str]:
    """Extract keywords from content using simple heuristics."""
    # Find code blocks and inline code
    code_pattern = r'`([^`]+)`'
    code_matches = re.findall(code_pattern, content)

    # Find words that look like identifiers (camelCase, snake_case, etc.)
    identifier_pattern = r'\b([a-z]+[A-Z][a-zA-Z]*|[a-z]+_[a-z_]+)\b'
    identifiers = re.findall(identifier_pattern, content)

    # Common technical terms
    tech_terms = []
    term_patterns = [
        r'\b(install|setup|config|api|auth|oauth|token|key|secret)\b',
        r'\b(import|export|module|package|dependency)\b',
        r'\b(error|debug|log|test|build|deploy)\b',
    ]
    for pattern in term_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        tech_terms.extend([m.lower() for m in matches])

    # Combine and dedupe
    all_keywords = set()
    for kw in code_matches + identifiers + tech_terms:
        kw_clean = kw.lower().strip()
        if len(kw_clean) > 2 and len(kw_clean) < 30:
            all_keywords.add(kw_clean)

    return sorted(list(all_keywords))[:20]  # Limit to 20 keywords


def _content_hash_suffix(content: str) -> str:
    """Generate a short hash suffix from content for stable dedup IDs."""
    return hashlib.md5(content[:200].encode('utf-8')).hexdigest()[:6]


def _strip_front_matter(content: str) -> tuple[str, dict]:
    """
    Strip YAML front-matter from content.

    Returns:
        Tuple of (content without front-matter, extracted metadata dict)
    """
    metadata: dict = {}
    if not content.startswith('---'):
        return content, metadata

    # Find closing ---
    end_match = re.search(r'\n---\s*\n', content[3:])
    if not end_match:
        return content, metadata

    front_matter = content[3:3 + end_match.start()]
    rest = content[3 + end_match.end():]

    # Extract title from front-matter
    title_match = re.search(r'^title:\s*["\']?(.+?)["\']?\s*$', front_matter, re.MULTILINE)
    if title_match:
        metadata['title'] = title_match.group(1).strip()

    return rest, metadata


def preprocess_mdx(content: str) -> str:
    """
    Preprocess MDX content to standard markdown.

    Strips:
    - YAML front-matter
    - JSX import statements
    - JSX component tags (preserving text children)
    """
    # Strip front-matter
    content, _ = _strip_front_matter(content)

    # Remove import lines: import Foo from 'bar'
    content = re.sub(r'^import\s+.*$', '', content, flags=re.MULTILINE)

    # Remove export default / export const lines (common in MDX)
    content = re.sub(r'^export\s+(default\s+)?.*$', '', content, flags=re.MULTILINE)

    # Strip self-closing JSX tags: <Component prop="value" />
    content = re.sub(r'<[A-Z][a-zA-Z]*\b[^>]*/>', '', content)

    # Strip opening/closing JSX tags but preserve children text
    # Opening: <Component prop="value">
    content = re.sub(r'<[A-Z][a-zA-Z]*\b[^>]*>', '', content)
    # Closing: </Component>
    content = re.sub(r'</[A-Z][a-zA-Z]*>', '', content)

    return content


def parse_markdown_to_sections(content: str, filename: str) -> list[Section]:
    """
    Parse markdown content into sections based on headers.

    Each header (H1-H6) starts a new section. The section includes
    all content until the next header of equal or lesser depth.

    For headingless files:
    - Uses first non-empty line as title (if < 100 chars)
    - Strips YAML front-matter and uses title: field if present
    - Splits long files (>200 lines) on double-blank-line boundaries
    """
    # Strip front-matter and extract metadata
    stripped_content, metadata = _strip_front_matter(content)

    lines = content.split('\n')
    sections: list[Section] = []

    # P3-1: Use Path.stem for extension stripping (handles .md, .markdown, .mdx, .rst)
    file_prefix = slugify(Path(filename).stem + '-' + '-'.join(Path(filename).parts[:-1]) if '/' in filename else Path(filename).stem)

    # Check if file has any headers
    header_pattern = re.compile(r'^(#{1,6})\s+(.+)$')
    has_headers = any(header_pattern.match(line) for line in lines)

    if not has_headers:
        return _parse_headingless(content, filename, file_prefix, metadata)

    # Track current position
    current_byte_offset = 0
    current_section_start = 0
    current_section_lines: list[str] = []
    current_header: Optional[tuple[int, str, int]] = None  # (depth, title, line_num)
    parent_stack: list[str] = []  # Stack of parent section IDs

    def finalize_section():
        """Create a Section from the current accumulated content."""
        nonlocal current_section_lines, current_header, current_section_start

        if current_header is None:
            # Content before any header - create root section
            if current_section_lines and any(line.strip() for line in current_section_lines):
                section_content = '\n'.join(current_section_lines)
                section_id = f"{file_prefix}-root"
                sections.append(Section(
                    id=section_id,
                    file=filename,
                    path=filename,
                    title=filename,
                    depth=0,
                    parent=None,
                    content=section_content,
                    keywords=extract_keywords(section_content),
                    line_count=len(current_section_lines),
                    byte_offset=current_section_start,
                    byte_length=len(section_content.encode('utf-8')),
                ))
                parent_stack.append(section_id)
        else:
            depth, title, _ = current_header
            section_content = '\n'.join(current_section_lines)
            slug = slugify(title)
            # P3-1: Use content hash for dedup instead of counter
            section_id = f"{file_prefix}-{slug}"

            # Ensure unique IDs using content hash
            if any(s.id == section_id for s in sections):
                section_id = f"{file_prefix}-{slug}-{_content_hash_suffix(section_content)}"

            # Find parent: last section with smaller depth
            parent = None
            while parent_stack:
                parent_section = next((s for s in sections if s.id == parent_stack[-1]), None)
                if parent_section and parent_section.depth < depth:
                    parent = parent_stack[-1]
                    break
                parent_stack.pop()

            sections.append(Section(
                id=section_id,
                file=filename,
                path=f"{filename}#{slug}",
                title=title,
                depth=depth,
                parent=parent,
                content=section_content,
                keywords=extract_keywords(section_content),
                line_count=len(current_section_lines),
                byte_offset=current_section_start,
                byte_length=len(section_content.encode('utf-8')),
            ))
            parent_stack.append(section_id)

        current_section_lines = []

    for line_num, line in enumerate(lines):
        match = header_pattern.match(line)

        if match:
            # Finalize previous section
            finalize_section()

            # Start new section
            depth = len(match.group(1))
            title = match.group(2).strip()
            current_header = (depth, title, line_num)
            current_section_start = current_byte_offset
            current_section_lines = [line]
        else:
            current_section_lines.append(line)

        current_byte_offset += len(line.encode('utf-8')) + 1  # +1 for newline

    # Finalize last section
    finalize_section()

    return sections


def _parse_headingless(
    content: str,
    filename: str,
    file_prefix: str,
    metadata: dict,
) -> list[Section]:
    """
    Parse a markdown file that has no headers.

    Heuristics:
    - Use front-matter title if available
    - Otherwise use first non-empty line as title (if < 100 chars)
    - Split long files (>200 lines) on double-blank-line boundaries
    """
    lines = content.split('\n')

    # Determine title
    title = metadata.get('title', '')
    if not title:
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith('---') and len(stripped) < 100:
                title = stripped
                break
    if not title:
        title = filename

    # For short files, return single section
    if len(lines) <= 200:
        section_id = f"{file_prefix}-root"
        return [Section(
            id=section_id,
            file=filename,
            path=filename,
            title=title,
            depth=0,
            parent=None,
            content=content,
            keywords=extract_keywords(content),
            line_count=len(lines),
            byte_offset=0,
            byte_length=len(content.encode('utf-8')),
        )]

    # Split long files on double-blank-line boundaries
    sections: list[Section] = []
    chunk_lines: list[str] = []
    chunk_start_offset = 0
    current_offset = 0
    blank_count = 0
    chunk_index = 0

    for line in lines:
        line_bytes = len(line.encode('utf-8')) + 1

        if not line.strip():
            blank_count += 1
        else:
            blank_count = 0

        chunk_lines.append(line)

        if blank_count >= 2 and len(chunk_lines) >= 20:
            # Flush chunk
            chunk_content = '\n'.join(chunk_lines)
            # Determine chunk title
            chunk_title = title if chunk_index == 0 else f"{title} (continued {chunk_index + 1})"
            for cl in chunk_lines:
                cs = cl.strip()
                if cs and chunk_index > 0:
                    chunk_title = cs[:80] if len(cs) < 100 else cs[:80] + '...'
                    break

            section_id = f"{file_prefix}-part-{chunk_index}"
            sections.append(Section(
                id=section_id,
                file=filename,
                path=filename,
                title=chunk_title,
                depth=0,
                parent=None,
                content=chunk_content,
                keywords=extract_keywords(chunk_content),
                line_count=len(chunk_lines),
                byte_offset=chunk_start_offset,
                byte_length=len(chunk_content.encode('utf-8')),
            ))

            chunk_lines = []
            chunk_start_offset = current_offset + line_bytes
            chunk_index += 1
            blank_count = 0

        current_offset += line_bytes

    # Flush remaining
    if chunk_lines and any(l.strip() for l in chunk_lines):
        chunk_content = '\n'.join(chunk_lines)
        chunk_title = title if chunk_index == 0 else f"{title} (continued {chunk_index + 1})"
        section_id = f"{file_prefix}-part-{chunk_index}"
        sections.append(Section(
            id=section_id,
            file=filename,
            path=filename,
            title=chunk_title,
            depth=0,
            parent=None,
            content=chunk_content,
            keywords=extract_keywords(chunk_content),
            line_count=len(chunk_lines),
            byte_offset=chunk_start_offset,
            byte_length=len(chunk_content.encode('utf-8')),
        ))

    return sections if sections else [Section(
        id=f"{file_prefix}-root",
        file=filename,
        path=filename,
        title=title,
        depth=0,
        parent=None,
        content=content,
        keywords=extract_keywords(content),
        line_count=len(lines),
        byte_offset=0,
        byte_length=len(content.encode('utf-8')),
    )]
