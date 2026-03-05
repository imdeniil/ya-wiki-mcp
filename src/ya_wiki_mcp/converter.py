"""Markdown → YFM (Yandex Flavored Markdown) converter.

Handles syntax differences between standard Markdown and Yandex Wiki markup.
"""

from __future__ import annotations

import re


def md_to_yfm(text: str) -> str:
    result = text

    # Standard MD tables → Wiki-style tables (more reliable in YFM)
    result = _convert_tables(result)

    # > [!NOTE] / > [!WARNING] etc → {% note %}
    result = _convert_callouts(result)

    # <details><summary> → {% cut %}
    result = _convert_details(result)

    # HTML <u>text</u> → ++text++
    result = re.sub(r"<u>(.*?)</u>", r"++\1++", result, flags=re.DOTALL)

    # HTML <mark>text</mark> → ==text==
    result = re.sub(r"<mark>(.*?)</mark>", r"==\1==", result, flags=re.DOTALL)

    # HTML <sup>text</sup> → text^super^
    result = re.sub(r"<sup>(.*?)</sup>", r"\1^super^", result)

    # HTML <sub>text</sub> → text~sub~
    result = re.sub(r"<sub>(.*?)</sub>", r"\1~sub~", result)

    return result


def _convert_callouts(text: str) -> str:
    """Convert GitHub-style callouts to YFM notes."""
    type_map = {
        "NOTE": "info",
        "TIP": "tip",
        "IMPORTANT": "warning",
        "WARNING": "warning",
        "CAUTION": "alert",
    }

    def replace_callout(m: re.Match) -> str:
        callout_type = m.group(1).upper()
        body = m.group(2).strip()
        # Remove leading "> " from each line
        body = re.sub(r"^> ?", "", body, flags=re.MULTILINE)
        yfm_type = type_map.get(callout_type, "info")
        return f'{{% note {yfm_type} "" %}}\n\n{body}\n\n{{% endnote %}}'

    # > [!NOTE]
    # > content lines
    pattern = r"> \[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]\s*\n((?:> .*\n?)+)"
    return re.sub(pattern, replace_callout, text, flags=re.IGNORECASE)


def _convert_details(text: str) -> str:
    """Convert HTML <details>/<summary> to YFM {% cut %}."""

    def replace_details(m: re.Match) -> str:
        title = m.group(1).strip()
        body = m.group(2).strip()
        return f'{{% cut "{title}" %}}\n\n{body}\n\n{{% endcut %}}'

    pattern = r"<details>\s*<summary>(.*?)</summary>(.*?)</details>"
    return re.sub(pattern, replace_details, text, flags=re.DOTALL)


def _convert_tables(text: str) -> str:
    """Convert Markdown tables to YFM wiki-style tables."""
    lines = text.split("\n")
    result: list[str] = []
    i = 0

    while i < len(lines):
        # Detect MD table: line with |, followed by separator line with |---|
        if (
            i + 1 < len(lines)
            and "|" in lines[i]
            and re.match(r"\s*\|[\s:|-]+\|\s*$", lines[i + 1])
        ):
            table_lines = [lines[i]]
            i += 1
            # Skip separator
            i += 1
            # Collect body rows
            while i < len(lines) and "|" in lines[i] and lines[i].strip().startswith("|"):
                table_lines.append(lines[i])
                i += 1

            result.append(_md_table_to_wiki(table_lines))
        else:
            result.append(lines[i])
            i += 1

    return "\n".join(result)


def _md_table_to_wiki(lines: list[str]) -> str:
    """Convert parsed MD table lines to #| || |# format."""
    rows: list[list[str]] = []
    for line in lines:
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        rows.append(cells)

    parts = ["#|"]
    for idx, row in enumerate(rows):
        if idx == 0:
            # Header row — bold cells
            cells_str = " | ".join(f"**{c}**" for c in row)
        else:
            cells_str = " | ".join(row)
        parts.append(f"|| {cells_str} ||")
    parts.append("|#")
    return "\n".join(parts)
