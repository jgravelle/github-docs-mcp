"""reStructuredText parsing to extract sections with hierarchy."""

import re
from typing import Optional

from .markdown import Section, slugify, extract_keywords, _content_hash_suffix


# RST underline characters, in common convention order.
# Actual depth is determined by document order of appearance.
RST_UNDERLINE_CHARS = set('=-~^"+`:#\'._*')


def _is_rst_underline(line: str) -> Optional[str]:
    """Check if a line is an RST section underline. Returns the char or None."""
    stripped = line.rstrip()
    if len(stripped) < 2:
        return None
    char = stripped[0]
    if char not in RST_UNDERLINE_CHARS:
        return None
    if all(c == char for c in stripped):
        return char
    return None


def parse_rst_to_sections(content: str, filename: str) -> list[Section]:
    """
    Parse reStructuredText content into sections based on header patterns.

    RST headers are title lines followed (and optionally preceded) by underline
    characters like =, -, ~, ^, etc. The depth is determined by the order
    underline characters first appear in the document.
    """
    from pathlib import Path

    lines = content.split('\n')
    sections: list[Section] = []

    file_prefix = slugify(
        Path(filename).stem + '-' + '-'.join(Path(filename).parts[:-1])
        if '/' in filename
        else Path(filename).stem
    )

    # Map underline characters to depth by order of appearance
    char_to_depth: dict[str, int] = {}

    # First pass: find all headers and their positions
    headers: list[tuple[int, str, int]] = []  # (line_num, title, depth)

    i = 0
    while i < len(lines):
        # Check for overline + title + underline pattern
        if (i + 2 < len(lines)
                and _is_rst_underline(lines[i]) is not None
                and lines[i + 1].strip()
                and _is_rst_underline(lines[i + 2]) is not None
                and _is_rst_underline(lines[i]) == _is_rst_underline(lines[i + 2])
                and len(lines[i].rstrip()) >= len(lines[i + 1].rstrip())):
            char = _is_rst_underline(lines[i])
            overline_char = f"overline-{char}"
            if overline_char not in char_to_depth:
                char_to_depth[overline_char] = len(char_to_depth) + 1
            title = lines[i + 1].strip()
            depth = char_to_depth[overline_char]
            headers.append((i, title, depth))
            i += 3
            continue

        # Check for title + underline pattern
        if (i + 1 < len(lines)
                and lines[i].strip()
                and not lines[i].startswith(' ')
                and _is_rst_underline(lines[i + 1]) is not None
                and len(lines[i + 1].rstrip()) >= len(lines[i].rstrip())):
            char = _is_rst_underline(lines[i + 1])
            if char not in char_to_depth:
                char_to_depth[char] = len(char_to_depth) + 1
            title = lines[i].strip()
            depth = char_to_depth[char]
            headers.append((i, title, depth))
            i += 2
            continue

        i += 1

    if not headers:
        # No headers found — treat as single section
        section_id = f"{file_prefix}-root"
        return [Section(
            id=section_id,
            file=filename,
            path=filename,
            title=filename,
            depth=0,
            parent=None,
            content=content,
            keywords=extract_keywords(content),
            line_count=len(lines),
            byte_offset=0,
            byte_length=len(content.encode('utf-8')),
        )]

    # Build sections from headers
    parent_stack: list[str] = []

    # Content before first header
    if headers[0][0] > 0:
        pre_lines = lines[:headers[0][0]]
        if any(l.strip() for l in pre_lines):
            pre_content = '\n'.join(pre_lines)
            section_id = f"{file_prefix}-root"
            sections.append(Section(
                id=section_id,
                file=filename,
                path=filename,
                title=filename,
                depth=0,
                parent=None,
                content=pre_content,
                keywords=extract_keywords(pre_content),
                line_count=len(pre_lines),
                byte_offset=0,
                byte_length=len(pre_content.encode('utf-8')),
            ))
            parent_stack.append(section_id)

    for idx, (line_num, title, depth) in enumerate(headers):
        # Determine end of this section
        if idx + 1 < len(headers):
            end_line = headers[idx + 1][0]
        else:
            end_line = len(lines)

        section_lines = lines[line_num:end_line]
        section_content = '\n'.join(section_lines)

        slug = slugify(title)
        section_id = f"{file_prefix}-{slug}"

        # Ensure unique IDs
        if any(s.id == section_id for s in sections):
            section_id = f"{file_prefix}-{slug}-{_content_hash_suffix(section_content)}"

        # Compute byte offset
        byte_offset = sum(len(l.encode('utf-8')) + 1 for l in lines[:line_num])

        # Find parent
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
            line_count=len(section_lines),
            byte_offset=byte_offset,
            byte_length=len(section_content.encode('utf-8')),
        ))
        parent_stack.append(section_id)

    return sections
