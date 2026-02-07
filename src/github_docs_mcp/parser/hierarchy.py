"""Build hierarchical section tree from flat section list."""

from dataclasses import dataclass, field
from typing import Optional
from .markdown import Section


@dataclass
class SectionNode:
    """A node in the section tree."""
    section: Section
    children: list["SectionNode"] = field(default_factory=list)


def build_section_tree(sections: list[Section]) -> list[SectionNode]:
    """
    Build a tree structure from flat sections.

    Returns a list of root nodes (sections with no parent).
    """
    # Create nodes for all sections
    nodes: dict[str, SectionNode] = {}
    for section in sections:
        nodes[section.id] = SectionNode(section=section)

    # Build parent-child relationships
    roots: list[SectionNode] = []
    for section in sections:
        node = nodes[section.id]
        if section.parent and section.parent in nodes:
            nodes[section.parent].children.append(node)
        else:
            roots.append(node)

    return roots


def flatten_tree(nodes: list[SectionNode], depth: int = 0) -> list[tuple[Section, int]]:
    """
    Flatten tree back to list with indent depth.

    Returns list of (section, indent_depth) tuples.
    """
    result: list[tuple[Section, int]] = []
    for node in nodes:
        result.append((node.section, depth))
        result.extend(flatten_tree(node.children, depth + 1))
    return result


def get_section_path(section_id: str, sections: list[Section]) -> list[str]:
    """Get the path from root to a section (list of section IDs)."""
    section_map = {s.id: s for s in sections}
    path: list[str] = []

    current_id: Optional[str] = section_id
    while current_id:
        path.insert(0, current_id)
        section = section_map.get(current_id)
        current_id = section.parent if section else None

    return path
