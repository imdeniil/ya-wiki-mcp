from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

from ya_wiki_mcp import converter, prompt_manager, tree_manager
from ya_wiki_mcp.client import WikiAPIError, create_client

logger = logging.getLogger(__name__)

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
        "wiki-style tables use #| || |#, colored text uses {color}(text), underline is ++text++.\n\n"
        "WORKFLOW for creating documentation:\n"
        "When the user asks to create a wiki page or write documentation, follow these steps:\n"
        "1. PLACEMENT: Call get_tree to show the wiki section tree. Ask the user which section to place the page in. "
        "If unsure, call suggest_placement with a brief description to recommend sections.\n"
        "2. TEMPLATE: Call prompts_list to show available prompt templates. Ask the user which template to use for generating content.\n"
        "3. GENERATE: Call prompts_get with the chosen template and arguments to generate the page content.\n"
        "4. CREATE: Call create_page with the generated content in the chosen section.\n"
        "Always confirm each step with the user before proceeding to the next."
    ),
)

_SYNTAX_FILE = Path(__file__).parent / "docs" / "yfm-syntax.md"

_wiki = None


def _get_wiki():
    global _wiki
    if _wiki is None:
        _wiki = create_client()
    return _wiki


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
    if hasattr(data, "model_dump"):
        data = data.model_dump(exclude_none=True)
    return json.dumps(data, ensure_ascii=False, indent=2)


def _error(e: WikiAPIError) -> str:
    msg = str(e)
    if isinstance(e.detail, dict):
        details = e.detail.get("details")
        if details:
            msg += f"\nDetails: {json.dumps(details, ensure_ascii=False)}"
    return msg


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------


def _cache_add(slug: str, title: str) -> None:
    """Silently add/update a page in the tree cache."""
    try:
        tree_manager.upsert_page(slug, title)
    except Exception:
        logger.debug("tree cache upsert failed for %s", slug, exc_info=True)


def _cache_remove(slug: str) -> None:
    """Silently remove a page from the tree cache."""
    try:
        tree_manager.remove_section(slug)
    except Exception:
        logger.debug("tree cache remove failed for %s", slug, exc_info=True)


async def _fetch_all_descendants(
    root_slug: str,
    *,
    include_self: bool = True,
) -> list[dict[str, str]]:
    """Fetch all descendants with titles from the API. Returns list of {slug, title}."""
    wiki = _get_wiki()

    # 1. Collect all page identities via pagination
    identities = []
    cursor = None
    while True:
        result = await wiki.pages.get_descendants_by_slug(
            root_slug, include_self=include_self, page_size=100, cursor=cursor,
        )
        identities.extend(result.results)
        if not result.next_cursor:
            break
        cursor = result.next_cursor

    # 2. Fetch titles in parallel
    async def _get_title(page_id: int, slug: str) -> dict[str, str]:
        try:
            page = await wiki.pages.get_by_id(page_id)
            return {"slug": slug, "title": page.title or slug.rsplit("/", 1)[-1]}
        except Exception:
            return {"slug": slug, "title": slug.rsplit("/", 1)[-1]}

    pages = await asyncio.gather(
        *[_get_title(p.id, p.slug) for p in identities if p.id and p.slug]
    )
    return list(pages)


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
        wiki = _get_wiki()
        if page_id is not None:
            result = await wiki.pages.get_by_id(page_id, fields="content")
        elif slug is not None:
            result = await wiki.pages.get(slug, fields="content")
        else:
            return "Error: Either slug or page_id must be provided"
        content = result.content or ""
        title = result.title or ""
        if title and not content.lstrip().startswith(f"# {title}"):
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
        wiki = _get_wiki()
        if page_id is not None:
            result = await wiki.pages.get_by_id(
                page_id, fields=fields,
                raise_on_redirect=raise_on_redirect, revision_id=revision_id,
            )
        elif slug is not None:
            result = await wiki.pages.get(
                slug, fields=fields,
                raise_on_redirect=raise_on_redirect, revision_id=revision_id,
            )
        else:
            return "Error: Either slug or page_id must be provided"
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
        wiki = _get_wiki()
        result = await wiki.pages.create(
            page_type=page_type, title=title, slug=slug, content=content,
            grid_format=grid_format, cloud_page=cloud_page, fields=fields, is_silent=is_silent,
        )
        _cache_add(slug, title)
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
        wiki = _get_wiki()
        result = await wiki.pages.update(
            page_id, title=title, content=content, redirect=redirect,
            allow_merge=allow_merge, fields=fields, is_silent=is_silent,
        )
        if title and hasattr(result, "slug") and result.slug:
            _cache_add(result.slug, title)
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
        wiki = _get_wiki()
        # Get slug before deletion for cache update
        slug = None
        try:
            page_info = await wiki.pages.get_by_id(page_id)
            slug = page_info.slug
        except Exception:
            pass
        result = await wiki.pages.delete(page_id)
        if slug:
            _cache_remove(slug)
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
        wiki = _get_wiki()
        # If no title given, fetch from source page
        clone_title = title
        if not clone_title:
            try:
                src = await wiki.pages.get_by_id(page_id)
                clone_title = src.title
            except Exception:
                clone_title = target.rsplit("/", 1)[-1]
        result = await wiki.pages.clone(
            page_id, target=target, title=title, subscribe_me=subscribe_me,
        )
        if clone_title:
            _cache_add(target, clone_title)
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
        wiki = _get_wiki()
        result = await wiki.pages.append_content(
            page_id, content=content, location=body_location,
            section_id=section_id, section_location=section_location,
            anchor_name=anchor_name, anchor_fallback=anchor_fallback, anchor_regex=anchor_regex,
            fields=fields, is_silent=is_silent,
        )
        return _json(result)
    except WikiAPIError as e:
        return _error(e)


# ---------------------------------------------------------------------------
# Page Descendants
# ---------------------------------------------------------------------------


@mcp.tool()
async def get_descendants(
    page_id: int,
    actuality: str | None = None,
    cursor: str | None = None,
    include_self: bool | None = None,
    page_size: int | None = None,
) -> str:
    """Get all descendant pages (subpages at all levels) of a page by its ID. Returns paginated list of page IDs and slugs.

    Args:
        page_id: Page numeric ID
        actuality: Filter by page status: "active" (default), "removed", or "all"
        cursor: Pagination cursor from previous response (next_cursor/prev_cursor)
        include_self: Include the parent page itself in results (default false)
        page_size: Results per page (default 20)
    """
    try:
        wiki = _get_wiki()
        result = await wiki.pages.get_descendants(
            page_id, actuality=actuality, cursor=cursor,
            include_self=include_self, page_size=page_size,
        )
        return _json(result)
    except WikiAPIError as e:
        return _error(e)


@mcp.tool()
async def get_descendants_by_slug(
    slug: str,
    actuality: str | None = None,
    cursor: str | None = None,
    include_self: bool | None = None,
    page_size: int | None = None,
) -> str:
    """Get all descendant pages (subpages at all levels) of a page by its slug. Returns paginated list of page IDs and slugs.

    Args:
        slug: Page slug, e.g. "users/test/page"
        actuality: Filter by page status: "active" (default), "removed", or "all"
        cursor: Pagination cursor from previous response (next_cursor/prev_cursor)
        include_self: Include the parent page itself in results (default false)
        page_size: Results per page (default 20)
    """
    try:
        wiki = _get_wiki()
        result = await wiki.pages.get_descendants_by_slug(
            slug, actuality=actuality, cursor=cursor,
            include_self=include_self, page_size=page_size,
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
        page_size: Results per page (1-50, default 25)
        q: Search by title (max 255 chars)
        types: Filter by type, comma-separated: attachment, sharepoint_resource, grid
    """
    try:
        wiki = _get_wiki()
        result = await wiki.pages.get_resources(
            page_id, cursor=cursor, order_by=order_by, order_direction=order_direction,
            page_size=page_size, q=q, types=types,
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
    page_size: int | None = None,
) -> str:
    """Get grids (dynamic tables) attached to a Yandex Wiki page.

    Args:
        page_id: Page numeric ID
        cursor: Pagination cursor
        order_by: Sort by "title" or "created_at"
        order_direction: "asc" or "desc"
        page_size: Results per page (1-50, default 25)
    """
    try:
        wiki = _get_wiki()
        result = await wiki.pages.get_grids(
            page_id, cursor=cursor, order_by=order_by, order_direction=order_direction,
            page_size=page_size,
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
        wiki = _get_wiki()
        result = await wiki.grids.create(title=title, page_id=page_id, page_slug=page_slug)
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
        wiki = _get_wiki()
        result = await wiki.grids.get(
            grid_id, fields=fields, filter=filter,
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
        wiki = _get_wiki()
        result = await wiki.grids.update(
            grid_id, revision=revision, title=title, default_sort=default_sort,
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
        wiki = _get_wiki()
        await wiki.grids.delete(grid_id)
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
        wiki = _get_wiki()
        result = await wiki.grids.rows.add(
            grid_id, rows=rows, revision=revision,
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
        wiki = _get_wiki()
        result = await wiki.grids.rows.delete(grid_id, row_ids=row_ids, revision=revision)
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
        wiki = _get_wiki()
        result = await wiki.grids.columns.add(
            grid_id, columns=columns, revision=revision, position=position,
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
        wiki = _get_wiki()
        result = await wiki.grids.columns.delete(
            grid_id, column_slugs=column_slugs, revision=revision,
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
        wiki = _get_wiki()
        result = await wiki.grids.cells.update(grid_id, cells=cells, revision=revision)
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
        wiki = _get_wiki()
        result = await wiki.grids.rows.move(
            grid_id, row_id=row_id, revision=revision,
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
        wiki = _get_wiki()
        result = await wiki.grids.columns.move(
            grid_id, column_slug=column_slug, revision=revision,
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
        wiki = _get_wiki()
        result = await wiki.grids.clone(
            grid_id, target=target, title=title, with_data=with_data,
        )
        return _json(result)
    except WikiAPIError as e:
        return _error(e)


# ---------------------------------------------------------------------------
# Page Tree
# ---------------------------------------------------------------------------


@mcp.tool()
async def get_tree(use_cache: bool = True) -> str:
    """Get the wiki page tree structure. Returns all known sections and their hierarchy.

    Use this before creating pages to find the best placement. The tree shows section titles, slugs, and nesting.

    Args:
        use_cache: If true (default), return cached tree from local YAML. If false, fetch fresh tree from API (slower but up-to-date). Requires a root section in cache to know which slug to query.
    """
    if not use_cache:
        # Determine root slug from existing cache
        tree = tree_manager.load_tree()
        if not tree:
            return "Cannot refresh: tree cache is empty — no root slug known. Use refresh_tree_cache(root_slug) to initialize."
        root_slug = tree[0]["slug"]
        try:
            pages = await _fetch_all_descendants(root_slug, include_self=True)
            tree = tree_manager.build_tree_from_pages(pages)
            tree_manager.save_tree(tree)
        except WikiAPIError as e:
            return f"Refresh failed: {_error(e)}\n\nReturning cached tree instead.\n\n{tree_manager.tree_to_text(tree_manager.load_tree())}"

    tree = tree_manager.load_tree()
    if not tree:
        return "Page tree is empty. Use add_tree_section or refresh_tree_cache to populate it."
    text = tree_manager.tree_to_text(tree)
    sections = tree_manager.flat_sections(tree)
    return f"Tree ({('cached' if use_cache else 'fresh from API')}):\n{text}\n\nTotal sections: {len(sections)}"


@mcp.tool()
async def refresh_tree_cache(root_slug: str) -> str:
    """Force refresh the entire wiki page tree cache from the API.

    Fetches all descendant pages under root_slug, retrieves their titles, and rebuilds the tree cache.
    This is slower than get_tree (makes N+1 API calls) but ensures the cache matches the real wiki.

    Args:
        root_slug: Root page slug to start from, e.g. "jummy"
    """
    try:
        pages = await _fetch_all_descendants(root_slug, include_self=True)
        if not pages:
            return f"No pages found under '{root_slug}'."
        tree = tree_manager.build_tree_from_pages(pages)
        tree_manager.save_tree(tree)
        sections = tree_manager.flat_sections(tree)
        return f"Cache refreshed: {len(sections)} sections from '{root_slug}'.\n\n{tree_manager.tree_to_text(tree)}"
    except WikiAPIError as e:
        return _error(e)


@mcp.tool()
async def clear_tree_cache() -> str:
    """Clear the wiki page tree cache. The cache will be empty until refreshed or manually populated."""
    tree_manager.clear_tree()
    return "Tree cache cleared."


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
