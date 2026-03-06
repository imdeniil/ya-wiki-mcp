from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

from ya_wiki_mcp import client, converter, prompt_manager, tree_manager
from ya_wiki_mcp.client import WikiAPIError

mcp = FastMCP(
    "ya-wiki",
    instructions=(
        "MCP server for Yandex Wiki API. Manages wiki pages, dynamic tables (grids), and page resources.\n\n"
        "Required env vars: YA_WIKI_TOKEN (OAuth token), YA_WIKI_ORG_ID (organization ID).\n"
        "Optional: YA_WIKI_ORG_TYPE ('cloud' or 'business', default 'cloud').\n\n"
        "Pages can be identified by slug (URL path like 'users/test/page') or numeric ID.\n"
        "Grids (dynamic tables) are identified by UUID. Grid operations use optimistic locking via revision strings.\n"
        "To get page content, pass fields='content' to get_page. Other optional fields: attributes, breadcrumbs, redirect.\n\n"
        "IMPORTANT: Yandex Wiki uses YFM (Yandex Flavored Markdown) syntax which differs from standard Markdown.\n"
        "Before creating or updating page content, read the 'yfm-syntax' resource to learn the correct markup.\n"
        "Key differences: notes use {% note %}, collapsible sections use {% cut %}, "
        "wiki-style tables use #| || |#, colored text uses {color}(text), underline is ++text++."
    ),
)

_SYNTAX_FILE = Path(__file__).parent / "docs" / "yfm-syntax.md"


@mcp.resource("yfm://syntax")
def yfm_syntax() -> str:
    """Yandex Wiki markup (YFM) syntax reference. Read this before creating or editing page content."""
    return _SYNTAX_FILE.read_text(encoding="utf-8")


@mcp.resource("wiki://pages/tree")
def wiki_pages_tree() -> str:
    """Wiki page tree structure. Shows all known sections and their hierarchy. Use this to find where to place new content."""
    tree = tree_manager.load_tree()
    if not tree:
        return "Page tree is empty. Use add_tree_section to populate it."
    return tree_manager.tree_to_text(tree)


def _json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def _error(e: WikiAPIError) -> str:
    parts = [f"Error [{e.error_code}]: {e}"]
    if e.details:
        parts.append(f"Details: {json.dumps(e.details, ensure_ascii=False)}")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------


@mcp.tool()
async def convert_md_to_yfm(markdown: str) -> str:
    """Convert standard Markdown to YFM (Yandex Flavored Markdown) syntax.

    Converts: tables (to wiki-style #||#), callouts (to {% note %}),
    <details> (to {% cut %}), <u> (to ++underline++), <mark> (to ==highlight==),
    <sup>/<sub> (to ^super^/~sub~).

    Use this before create_page or update_page to ensure content renders correctly in Yandex Wiki.

    Args:
        markdown: Standard Markdown text to convert
    """
    return converter.md_to_yfm(markdown)


@mcp.tool()
async def get_page_content(
    slug: str | None = None,
    page_id: int | None = None,
) -> str:
    """Get just the text content of a Yandex Wiki page (no metadata). Convenient for reading pages.

    Args:
        slug: Page slug, e.g. "users/test/page"
        page_id: Page numeric ID (alternative to slug)
    """
    try:
        result = await client.get_page(
            slug=slug, page_id=page_id, fields="content",
        )
        content = result.get("content", "")
        title = result.get("title", "")
        if title:
            return f"# {title}\n\n{content}"
        return content or "(empty page)"
    except WikiAPIError as e:
        return _error(e)


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------


@mcp.tool()
async def get_page(
    slug: str | None = None,
    page_id: int | None = None,
    fields: str | None = None,
    raise_on_redirect: bool = False,
    revision_id: int | None = None,
) -> str:
    """Get a Yandex Wiki page by slug or ID.

    Args:
        slug: Page slug, e.g. "users/test/page"
        page_id: Page numeric ID (alternative to slug)
        fields: Comma-separated additional fields: attributes, breadcrumbs, content, redirect. By default only id/slug/title are returned.
        raise_on_redirect: Raise error if page has redirect
        revision_id: Get specific revision
    """
    try:
        result = await client.get_page(
            slug=slug, page_id=page_id, fields=fields,
            raise_on_redirect=raise_on_redirect, revision_id=revision_id,
        )
        return _json(result)
    except WikiAPIError as e:
        return _error(e)


@mcp.tool()
async def create_page(
    page_type: str,
    title: str,
    slug: str,
    content: str | None = None,
    grid_format: str | None = None,
    cloud_page: dict[str, Any] | None = None,
    fields: str | None = None,
    is_silent: bool = False,
) -> str:
    """Create a new Yandex Wiki page.

    Args:
        page_type: One of: page, grid, cloud_page, wysiwyg, template
        title: Page title (1-255 chars)
        slug: URL path, e.g. "users/test/newpage"
        content: Page body text
        grid_format: Text format for grid pages: yfm, wom, plain
        cloud_page: MS365 cloud page config. Examples:
            - Empty doc: {"method": "empty_doc", "doctype": "docx"}
            - From URL: {"method": "from_url", "url": "https://..."}
        fields: Response fields to include
        is_silent: Silent mode (no notifications)
    """
    try:
        result = await client.create_page(
            page_type=page_type, title=title, slug=slug, content=content,
            grid_format=grid_format, cloud_page=cloud_page, fields=fields, is_silent=is_silent,
        )
        return _json(result)
    except WikiAPIError as e:
        return _error(e)


@mcp.tool()
async def update_page(
    page_id: int,
    title: str | None = None,
    content: str | None = None,
    redirect: dict[str, Any] | None = None,
    allow_merge: bool = False,
    fields: str | None = None,
    is_silent: bool = False,
) -> str:
    """Update an existing Yandex Wiki page.

    Args:
        page_id: Page numeric ID
        title: New title (1-255 chars)
        content: New page content
        redirect: Set redirect, e.g. {"page": {"id": 456}} or {"page": {"slug": "path/to"}}. Pass null to remove redirect.
        allow_merge: Merge simultaneous edits via 3-way-merge
        fields: Additional response fields
        is_silent: Silent mode
    """
    try:
        result = await client.update_page(
            page_id=page_id, title=title, content=content, redirect=redirect,
            allow_merge=allow_merge, fields=fields, is_silent=is_silent,
        )
        return _json(result)
    except WikiAPIError as e:
        return _error(e)


@mcp.tool()
async def delete_page(page_id: int) -> str:
    """Delete a Yandex Wiki page. Returns a recovery_token that can be used to restore it.

    Args:
        page_id: Page numeric ID
    """
    try:
        result = await client.delete_page(page_id=page_id)
        return _json(result)
    except WikiAPIError as e:
        return _error(e)


@mcp.tool()
async def clone_page(
    page_id: int,
    target: str,
    title: str | None = None,
    subscribe_me: bool = False,
) -> str:
    """Clone a Yandex Wiki page to a new location. Returns operation status with status_url to track progress.

    Args:
        page_id: Source page numeric ID
        target: Destination slug, e.g. "users/test/copy"
        title: New title (1-255 chars)
        subscribe_me: Subscribe to changes on the cloned page
    """
    try:
        result = await client.clone_page(
            page_id=page_id, target=target, title=title, subscribe_me=subscribe_me,
        )
        return _json(result)
    except WikiAPIError as e:
        return _error(e)


@mcp.tool()
async def append_content(
    page_id: int,
    content: str,
    body_location: str | None = None,
    section_id: int | None = None,
    section_location: str | None = None,
    anchor_name: str | None = None,
    anchor_fallback: bool = False,
    anchor_regex: bool = False,
    fields: str | None = None,
    is_silent: bool = False,
) -> str:
    """Append content to an existing Yandex Wiki page. Use exactly one of: body_location, section_id, or anchor_name.

    Args:
        page_id: Page numeric ID
        content: Text to append (min 1 char)
        body_location: "top" or "bottom" — append to page body
        section_id: Target section ID (use with section_location)
        section_location: "top" or "bottom" within section
        anchor_name: Anchor reference point, e.g. "#heading"
        anchor_fallback: Enable fallback matching for anchor
        anchor_regex: Treat anchor as regex
        fields: Additional response fields
        is_silent: Silent mode
    """
    try:
        result = await client.append_content(
            page_id=page_id, content=content, body_location=body_location,
            section_id=section_id, section_location=section_location,
            anchor_name=anchor_name, anchor_fallback=anchor_fallback, anchor_regex=anchor_regex,
            fields=fields, is_silent=is_silent,
        )
        return _json(result)
    except WikiAPIError as e:
        return _error(e)


# ---------------------------------------------------------------------------
# Page Resources
# ---------------------------------------------------------------------------


@mcp.tool()
async def get_page_resources(
    page_id: int,
    cursor: str | None = None,
    order_by: str | None = None,
    order_direction: str | None = None,
    page_num: int | None = None,
    page_size: int | None = None,
    q: str | None = None,
    types: str | None = None,
) -> str:
    """Get resources (attachments, grids, sharepoint docs) of a Yandex Wiki page. Supports pagination via cursor.

    Args:
        page_id: Page numeric ID
        cursor: Pagination cursor from previous response (next_cursor/prev_cursor)
        order_by: Sort by "name_title" or "created_at"
        order_direction: "asc" or "desc"
        page_num: Legacy page number (min 1)
        page_size: Results per page (1-50, default 25)
        q: Search by title (max 255 chars)
        types: Filter by type, comma-separated: attachment, sharepoint_resource, grid
    """
    try:
        result = await client.get_page_resources(
            page_id=page_id, cursor=cursor, order_by=order_by, order_direction=order_direction,
            page_num=page_num, page_size=page_size, q=q, types=types,
        )
        return _json(result)
    except WikiAPIError as e:
        return _error(e)


@mcp.tool()
async def get_page_grids(
    page_id: int,
    cursor: str | None = None,
    order_by: str | None = None,
    order_direction: str | None = None,
    page_num: int | None = None,
    page_size: int | None = None,
) -> str:
    """Get grids (dynamic tables) attached to a Yandex Wiki page.

    Args:
        page_id: Page numeric ID
        cursor: Pagination cursor
        order_by: Sort by "title" or "created_at"
        order_direction: "asc" or "desc"
        page_num: Legacy page number (min 1)
        page_size: Results per page (1-50, default 25)
    """
    try:
        result = await client.get_page_grids(
            page_id=page_id, cursor=cursor, order_by=order_by, order_direction=order_direction,
            page_num=page_num, page_size=page_size,
        )
        return _json(result)
    except WikiAPIError as e:
        return _error(e)


# ---------------------------------------------------------------------------
# Grids (Dynamic Tables)
# ---------------------------------------------------------------------------


@mcp.tool()
async def create_grid(
    title: str,
    page_id: int | None = None,
    page_slug: str | None = None,
) -> str:
    """Create a new grid (dynamic table) on a Yandex Wiki page.

    Args:
        title: Grid title (1-255 chars)
        page_id: Parent page ID (takes priority over page_slug)
        page_slug: Parent page slug (alternative to page_id)
    """
    try:
        result = await client.create_grid(title=title, page_id=page_id, page_slug=page_slug)
        return _json(result)
    except WikiAPIError as e:
        return _error(e)


@mcp.tool()
async def get_grid(
    grid_id: str,
    fields: str | None = None,
    filter: str | None = None,
    only_cols: str | None = None,
    only_rows: str | None = None,
    revision: int | None = None,
    sort: str | None = None,
) -> str:
    """Get a grid (dynamic table) by ID with optional filtering and sorting.

    Args:
        grid_id: Grid UUID
        fields: Additional fields, comma-separated
        filter: Row filter expression, e.g. "[name] ~ wiki AND [age]>18"
        only_cols: Return specific columns by slug, comma-separated
        only_rows: Return specific rows by ID, comma-separated
        revision: Load specific grid version
        sort: Sort rows, e.g. "name, -age" (prefix "-" for desc)
    """
    try:
        result = await client.get_grid(
            grid_id=grid_id, fields=fields, filter=filter,
            only_cols=only_cols, only_rows=only_rows, revision=revision, sort=sort,
        )
        return _json(result)
    except WikiAPIError as e:
        return _error(e)


@mcp.tool()
async def update_grid(
    grid_id: str,
    revision: str,
    title: str | None = None,
    default_sort: list[dict[str, str]] | None = None,
) -> str:
    """Update grid title or default sort order. Returns new revision.

    Args:
        grid_id: Grid UUID
        revision: Current revision string (required for optimistic locking)
        title: New title (1-255 chars)
        default_sort: Default sort config, e.g. [{"column_slug": "asc"}]
    """
    try:
        result = await client.update_grid(
            grid_id=grid_id, revision=revision, title=title, default_sort=default_sort,
        )
        return _json(result)
    except WikiAPIError as e:
        return _error(e)


@mcp.tool()
async def delete_grid(grid_id: str) -> str:
    """Delete a grid (dynamic table). This action cannot be undone.

    Args:
        grid_id: Grid UUID
    """
    try:
        await client.delete_grid(grid_id=grid_id)
        return "Grid deleted successfully"
    except WikiAPIError as e:
        return _error(e)


@mcp.tool()
async def add_rows(
    grid_id: str,
    rows: list[dict[str, Any]],
    revision: str | None = None,
    position: int | None = None,
    after_row_id: str | None = None,
) -> str:
    """Add rows to a grid. Returns new revision and created row IDs.

    Args:
        grid_id: Grid UUID
        rows: List of row objects keyed by column slug, e.g. [{"name": "Alice", "age": 30}]
        revision: Current revision string
        position: Insert at position (0-based)
        after_row_id: Insert after this row ID
    """
    try:
        result = await client.add_rows(
            grid_id=grid_id, rows=rows, revision=revision,
            position=position, after_row_id=after_row_id,
        )
        return _json(result)
    except WikiAPIError as e:
        return _error(e)


@mcp.tool()
async def delete_rows(
    grid_id: str,
    row_ids: list[str],
    revision: str | None = None,
) -> str:
    """Delete rows from a grid. Returns new revision.

    Args:
        grid_id: Grid UUID
        row_ids: List of row IDs to delete
        revision: Current revision string
    """
    try:
        result = await client.delete_rows(grid_id=grid_id, row_ids=row_ids, revision=revision)
        return _json(result)
    except WikiAPIError as e:
        return _error(e)


@mcp.tool()
async def add_columns(
    grid_id: str,
    columns: list[dict[str, Any]],
    revision: str | None = None,
    position: int | None = None,
) -> str:
    """Add columns to a grid. Returns new revision.

    Each column must have: "title" (str), "type" (str), "slug" (str), "required" (bool).

    Column types: string, number, date, select, staff, checkbox, ticket, ticket_field.
    Optional fields: width (int), width_units ("%" or "px"), pinned ("left"/"right"),
    color (blue/yellow/pink/red/green/mint/grey/orange/magenta/purple/copper/ocean),
    multiple (bool, for select/staff), format ("yfm"/"wom"/"plain", for string),
    select_options (list[str], for select), mark_rows (bool, for checkbox), description (str).

    Example: [{"title": "Name", "type": "string", "slug": "name", "required": true}]

    Args:
        grid_id: Grid UUID
        columns: List of column definitions (see above)
        revision: Current revision string
        position: Insert at position (0-based)
    """
    try:
        result = await client.add_columns(
            grid_id=grid_id, columns=columns, revision=revision, position=position,
        )
        return _json(result)
    except WikiAPIError as e:
        return _error(e)


@mcp.tool()
async def delete_columns(
    grid_id: str,
    column_slugs: list[str],
    revision: str | None = None,
) -> str:
    """Delete columns from a grid. Returns new revision.

    Args:
        grid_id: Grid UUID
        column_slugs: List of column slugs to delete
        revision: Current revision string
    """
    try:
        result = await client.delete_columns(
            grid_id=grid_id, column_slugs=column_slugs, revision=revision,
        )
        return _json(result)
    except WikiAPIError as e:
        return _error(e)


@mcp.tool()
async def update_cells(
    grid_id: str,
    cells: list[dict[str, Any]],
    revision: str | None = None,
) -> str:
    """Update cell values in a grid. Returns new revision and updated cells.

    Each cell: {"row_id": int, "column_slug": "col", "value": <any>}.
    Values can be: string, number, boolean, string[] (for select/multiple), or
    user objects [{"uid": "123"}] (for staff columns).

    Args:
        grid_id: Grid UUID
        cells: List of cell updates
        revision: Current revision string
    """
    try:
        result = await client.update_cells(grid_id=grid_id, cells=cells, revision=revision)
        return _json(result)
    except WikiAPIError as e:
        return _error(e)


@mcp.tool()
async def move_rows(
    grid_id: str,
    row_id: str,
    revision: str,
    position: int | None = None,
    after_row_id: str | None = None,
    rows_count: int = 1,
) -> str:
    """Move rows within a grid. Returns new revision.

    Args:
        grid_id: Grid UUID
        row_id: First row ID to move
        revision: Current revision string
        position: Target position (0-based)
        after_row_id: Place after this row
        rows_count: Number of consecutive rows to move (default 1)
    """
    try:
        result = await client.move_rows(
            grid_id=grid_id, row_id=row_id, revision=revision,
            position=position, after_row_id=after_row_id, rows_count=rows_count,
        )
        return _json(result)
    except WikiAPIError as e:
        return _error(e)


@mcp.tool()
async def move_columns(
    grid_id: str,
    column_slug: str,
    revision: str,
    position: int | None = None,
    columns_count: int = 1,
) -> str:
    """Move columns within a grid. Returns new revision.

    Args:
        grid_id: Grid UUID
        column_slug: Column slug to move
        revision: Current revision string
        position: Target position (0-based)
        columns_count: Number of consecutive columns to move (default 1)
    """
    try:
        result = await client.move_columns(
            grid_id=grid_id, column_slug=column_slug, revision=revision,
            position=position, columns_count=columns_count,
        )
        return _json(result)
    except WikiAPIError as e:
        return _error(e)


@mcp.tool()
async def clone_grid(
    grid_id: str,
    target: str,
    title: str | None = None,
    with_data: bool = False,
) -> str:
    """Clone a grid to another page. Returns operation status with status_url to track progress.

    Args:
        grid_id: Source grid UUID
        target: Destination page slug (creates page if needed)
        title: New grid title (1-255 chars)
        with_data: Copy row data too (default false, copies only structure)
    """
    try:
        result = await client.clone_grid(
            grid_id=grid_id, target=target, title=title, with_data=with_data,
        )
        return _json(result)
    except WikiAPIError as e:
        return _error(e)


# ---------------------------------------------------------------------------
# Page Tree
# ---------------------------------------------------------------------------


@mcp.tool()
async def get_tree() -> str:
    """Get the wiki page tree structure. Returns all known sections and their hierarchy.

    Use this before creating pages to find the best placement. The tree shows section titles, slugs, and nesting.
    """
    tree = tree_manager.load_tree()
    if not tree:
        return "Page tree is empty. Use add_tree_section to add root sections first."
    text = tree_manager.tree_to_text(tree)
    sections = tree_manager.flat_sections(tree)
    return f"Tree:\n{text}\n\nTotal sections: {len(sections)}"


@mcp.tool()
async def suggest_placement(description: str) -> str:
    """Suggest where to place a new page in the wiki tree based on its description.

    Returns a ranked list of existing sections that best match the content,
    plus a suggestion for creating a new section if none fit well.
    Use this to help the user decide where to put new documentation.

    Args:
        description: Brief description of the page content to be placed
    """
    tree = tree_manager.load_tree()
    if not tree:
        return "Page tree is empty. Use add_tree_section to add root sections first, then retry."

    sections = tree_manager.flat_sections(tree)
    section_list = "\n".join(
        f"  {i+1}. {s['path']} (slug: {s['slug']})"
        for i, s in enumerate(sections)
    )
    return (
        f"Content to place: {description}\n\n"
        f"Available sections:\n{section_list}\n\n"
        "Based on the content description above, suggest the best matching section "
        "from the list. If none fit well, propose a new section name and parent slug."
    )


@mcp.tool()
async def add_tree_section(
    slug: str,
    title: str,
    parent_slug: str | None = None,
) -> str:
    """Add a new section to the wiki page tree.

    Args:
        slug: Section slug (URL path), e.g. "jummy/razrabotka/new-section"
        title: Section display title, e.g. "New Section"
        parent_slug: Parent section slug to nest under. If not provided, adds as root section.
    """
    try:
        tree = tree_manager.add_section(slug=slug, title=title, parent_slug=parent_slug)
        return f"Section '{title}' added. Updated tree:\n{tree_manager.tree_to_text(tree)}"
    except ValueError as e:
        return f"Error: {e}"


@mcp.tool()
async def remove_tree_section(slug: str) -> str:
    """Remove a section from the wiki page tree.

    Args:
        slug: Section slug to remove
    """
    tree = tree_manager.remove_section(slug)
    if not tree:
        return "Section removed. Tree is now empty."
    return f"Section removed. Updated tree:\n{tree_manager.tree_to_text(tree)}"


@mcp.tool()
async def set_tree(tree_yaml: str) -> str:
    """Replace the entire wiki page tree from YAML. Use this to bulk-import the tree structure.

    Args:
        tree_yaml: YAML string with tree structure. Format:
            - slug: root/section
              title: Section Name
              children:
                - slug: root/section/child
                  title: Child Name
    """
    import yaml
    try:
        data = yaml.safe_load(tree_yaml)
        if not isinstance(data, list):
            return "Error: YAML must be a list of sections"
        tree_manager.save_tree(data)
        return f"Tree updated:\n{tree_manager.tree_to_text(data)}"
    except yaml.YAMLError as e:
        return f"Error parsing YAML: {e}"


# ---------------------------------------------------------------------------
# Prompt Manager
# ---------------------------------------------------------------------------


@mcp.tool()
async def prompts_list() -> str:
    """List all saved Yandex Wiki prompt templates. These are reusable templates for creating wiki page content."""
    prompts = prompt_manager.list_prompts()
    if not prompts:
        return "No prompts saved yet. Use prompts_add to create one."
    return _json(prompts)


@mcp.tool()
async def prompts_get(name: str, arguments: dict[str, str] | None = None) -> str:
    """Get and render a Yandex Wiki prompt template with arguments. Use for generating wiki page content from templates.

    Args:
        name: Prompt name (filename without .md)
        arguments: Key-value pairs for template substitution, e.g. {"topic": "API docs", "date": "2026-03-05"}
    """
    rendered = prompt_manager.render_prompt(name, **(arguments or {}))
    if rendered is None:
        available = prompt_manager.list_prompts()
        names = [p["name"] for p in available]
        return f"Prompt '{name}' not found. Available: {', '.join(names) or 'none'}"
    return rendered


@mcp.tool()
async def prompts_add(
    name: str,
    description: str,
    body: str,
    arguments: list[dict[str, str]] | None = None,
) -> str:
    """Create or update a Yandex Wiki prompt template. Templates are used for generating wiki page content.

    Args:
        name: Prompt name (will be used as filename, no spaces)
        description: What this prompt does
        body: Prompt template text. Use {arg_name} for substitution placeholders.
        arguments: Optional list of arguments, each with "name", "description", and optionally "required" (bool).
            Example: [{"name": "topic", "description": "Page topic", "required": "true"}]
    """
    # Build frontmatter
    meta = {"description": description}
    if arguments:
        meta["arguments"] = arguments

    lines = ["---"]
    lines.append(f"description: {description}")
    if arguments:
        lines.append("arguments:")
        for arg in arguments:
            lines.append(f"  - name: {arg['name']}")
            lines.append(f"    description: {arg.get('description', '')}")
            if arg.get("required"):
                lines.append(f"    required: {arg['required']}")
    lines.append("---")
    lines.append(body)

    content = "\n".join(lines)
    path = prompt_manager.save_prompt(name, content)
    return f"Prompt '{name}' saved to {path}"


@mcp.tool()
async def prompts_add_from_file(name: str, file_path: str) -> str:
    """Load a Yandex Wiki prompt template from an existing file. The file should have YAML frontmatter (---) with description and arguments, followed by the prompt body.

    If the file has no frontmatter, it will be saved as-is with the filename as the prompt name.

    Args:
        name: Prompt name to save as
        file_path: Absolute path to the .md file to load
    """
    path = Path(file_path)
    if not path.exists():
        return f"File not found: {file_path}"

    content = path.read_text(encoding="utf-8")
    save_path = prompt_manager.save_prompt(name, content)
    return f"Prompt '{name}' loaded from {file_path} and saved to {save_path}"


@mcp.tool()
async def prompts_remove(name: str) -> str:
    """Delete a Yandex Wiki prompt template.

    Args:
        name: Prompt name to delete
    """
    if prompt_manager.delete_prompt(name):
        return f"Prompt '{name}' deleted"
    return f"Prompt '{name}' not found"


def main():
    mcp.run()


if __name__ == "__main__":
    main()
