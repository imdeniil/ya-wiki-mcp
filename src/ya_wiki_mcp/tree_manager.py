"""Wiki page tree manager.

Stores the wiki section tree as a YAML file.
Each node has: slug, title, and optional children.

Format:
- slug: jummy
  title: Jummy
  children:
    - slug: jummy/razrabotka
      title: Разработка
      children:
        - slug: jummy/razrabotka/jandekswiki
          title: Яндекс Вики
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

TREE_FILE = Path(__file__).parent / "tree.yaml"


def _ensure_file() -> None:
    if not TREE_FILE.exists():
        TREE_FILE.write_text("# Wiki page tree\n[]\n", encoding="utf-8")


def load_tree() -> list[dict[str, Any]]:
    _ensure_file()
    data = yaml.safe_load(TREE_FILE.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else []


def save_tree(tree: list[dict[str, Any]]) -> Path:
    TREE_FILE.write_text(
        yaml.dump(tree, allow_unicode=True, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )
    return TREE_FILE


def tree_to_text(tree: list[dict[str, Any]], indent: int = 0) -> str:
    """Render tree as indented text for display."""
    lines: list[str] = []
    for node in tree:
        prefix = "  " * indent
        lines.append(f"{prefix}- {node['title']} ({node['slug']})")
        children = node.get("children", [])
        if children:
            lines.append(tree_to_text(children, indent + 1))
    return "\n".join(lines)


def flat_sections(tree: list[dict[str, Any]], path: str = "") -> list[dict[str, str]]:
    """Flatten tree into a list of {slug, title, path} for matching."""
    result: list[dict[str, str]] = []
    for node in tree:
        current_path = f"{path} / {node['title']}" if path else node["title"]
        result.append({
            "slug": node["slug"],
            "title": node["title"],
            "path": current_path,
        })
        children = node.get("children", [])
        if children:
            result.extend(flat_sections(children, current_path))
    return result


def _find_parent(tree: list[dict[str, Any]], parent_slug: str) -> dict[str, Any] | None:
    """Find a node by slug in the tree."""
    for node in tree:
        if node["slug"] == parent_slug:
            return node
        children = node.get("children", [])
        if children:
            found = _find_parent(children, parent_slug)
            if found:
                return found
    return None


def add_section(
    slug: str,
    title: str,
    parent_slug: str | None = None,
) -> list[dict[str, Any]]:
    """Add a new section to the tree. Returns updated tree."""
    tree = load_tree()
    new_node: dict[str, Any] = {"slug": slug, "title": title, "children": []}

    if parent_slug:
        parent = _find_parent(tree, parent_slug)
        if parent is None:
            raise ValueError(f"Parent section '{parent_slug}' not found in tree")
        parent.setdefault("children", []).append(new_node)
    else:
        tree.append(new_node)

    save_tree(tree)
    return tree


def remove_section(slug: str) -> list[dict[str, Any]]:
    """Remove a section from the tree by slug. Returns updated tree."""
    tree = load_tree()
    _remove_from(tree, slug)
    save_tree(tree)
    return tree


def _remove_from(nodes: list[dict[str, Any]], slug: str) -> bool:
    for i, node in enumerate(nodes):
        if node["slug"] == slug:
            nodes.pop(i)
            return True
        children = node.get("children", [])
        if children and _remove_from(children, slug):
            return True
    return False
