"""Dynamic prompt manager for ya-wiki MCP server.

Prompts are stored as .md files in the prompts/ directory.
Each file has YAML frontmatter with metadata, followed by the prompt body.

Format:
---
description: What this prompt does
arguments:
  - name: topic
    description: The topic to write about
    required: true
---
Prompt body text here. Use {topic} for argument substitution.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

PROMPTS_DIR = Path(__file__).parent / "prompts"


def _ensure_dir() -> None:
    PROMPTS_DIR.mkdir(exist_ok=True)


def _parse_prompt_file(path: Path) -> dict[str, Any]:
    """Parse a prompt .md file with YAML frontmatter."""
    text = path.read_text(encoding="utf-8")

    # Extract frontmatter
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, re.DOTALL)
    if m:
        meta = yaml.safe_load(m.group(1)) or {}
        body = m.group(2).strip()
    else:
        meta = {}
        body = text.strip()

    return {
        "name": path.stem,
        "description": meta.get("description", ""),
        "arguments": meta.get("arguments", []),
        "body": body,
    }


def list_prompts() -> list[dict[str, Any]]:
    _ensure_dir()
    result = []
    for f in sorted(PROMPTS_DIR.glob("*.md")):
        try:
            p = _parse_prompt_file(f)
            result.append({
                "name": p["name"],
                "description": p["description"],
                "arguments": [a["name"] for a in p["arguments"]],
            })
        except Exception as e:
            result.append({"name": f.stem, "error": str(e)})
    return result


def get_prompt(name: str) -> dict[str, Any] | None:
    _ensure_dir()
    path = PROMPTS_DIR / f"{name}.md"
    if not path.exists():
        return None
    return _parse_prompt_file(path)


def render_prompt(name: str, **kwargs: str) -> str | None:
    """Render a prompt template with arguments."""
    prompt = get_prompt(name)
    if not prompt:
        return None
    body = prompt["body"]
    for key, value in kwargs.items():
        body = body.replace(f"{{{key}}}", value)
    return body


def save_prompt(name: str, content: str) -> Path:
    """Save prompt content to a .md file."""
    _ensure_dir()
    path = PROMPTS_DIR / f"{name}.md"
    path.write_text(content, encoding="utf-8")
    return path


def delete_prompt(name: str) -> bool:
    _ensure_dir()
    path = PROMPTS_DIR / f"{name}.md"
    if path.exists():
        path.unlink()
        return True
    return False
