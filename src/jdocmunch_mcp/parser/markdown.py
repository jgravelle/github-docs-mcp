"""Markdown parsing to extract sections with hierarchy."""

import re
from dataclasses import dataclass, field
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


def parse_markdown_to_sections(content: str, filename: str) -> list[Section]:
    """
    Parse markdown content into sections based on headers.

    Each header (H1-H6) starts a new section. The section includes
    all content until the next header of equal or lesser depth.
    """
    lines = content.split('\n')
    sections: list[Section] = []

    # Track current position
    current_byte_offset = 0
    current_section_start = 0
    current_section_lines: list[str] = []
    current_header: Optional[tuple[int, str, int]] = None  # (depth, title, line_num)
    parent_stack: list[str] = []  # Stack of parent section IDs

    file_prefix = slugify(filename.replace('.md', '').replace('/', '-'))

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
            section_id = f"{file_prefix}-{slug}"

            # Ensure unique IDs
            base_id = section_id
            counter = 1
            while any(s.id == section_id for s in sections):
                section_id = f"{base_id}-{counter}"
                counter += 1

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

    header_pattern = re.compile(r'^(#{1,6})\s+(.+)$')

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
