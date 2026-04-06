# ya-wiki-mcp

MCP server for Yandex Wiki API. Works with Claude Code, Claude Desktop, and any MCP client.

Built on [ya-wiki-api](https://pypi.org/project/ya-wiki-api/) Python client.

## Quick Start

```bash
# Add to Claude Code
claude mcp add ya-wiki \
  -e YA_WIKI_TOKEN=your-token \
  -e YA_WIKI_ORG_ID=your-org-id \
  -- uvx ya-wiki-mcp

# Or run directly
uvx ya-wiki-mcp
```

### Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "ya-wiki": {
      "command": "uvx",
      "args": ["ya-wiki-mcp"],
      "env": {
        "YA_WIKI_TOKEN": "your-token",
        "YA_WIKI_ORG_ID": "your-org-id"
      }
    }
  }
}
```

## Features

- **36 tools** — full CRUD for pages, dynamic tables (grids), resources, and tree navigation
- **Page tree cache** — local tree cache with auto-sync on page create/update/delete/clone, plus full refresh from API
- **YFM reference** — built-in Yandex Flavored Markdown syntax guide
- **Markdown to YFM converter** — automatically converts standard Markdown to Wiki format
- **Prompt templates** — manage reusable page templates directly from chat

## Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `YA_WIKI_TOKEN` | Yes | OAuth token. Get one at https://oauth.yandex.ru/ |
| `YA_WIKI_ORG_ID` | Yes | Organization ID |
| `YA_WIKI_ORG_TYPE` | No | `cloud` (default) or `business` |

You can set these in a `.env` file or pass via `-e` flags.

### Getting a Token

1. Go to https://oauth.yandex.ru/ and create an app
2. Select "For API access or debugging"
3. Add scopes: `wiki:write` (full access) or `wiki:read` (read-only)
4. Get your token: `https://oauth.yandex.ru/authorize?response_type=token&client_id=<ClientID>`

## Tools

### Pages
| Tool | Description |
|------|-------------|
| `get_page` | Get a page by slug or ID |
| `get_page_content` | Get page text only (no metadata) |
| `create_page` | Create a page (wysiwyg, page, grid, template). Auto-updates tree cache. |
| `update_page` | Update title, content, or redirect. Auto-updates tree cache on title change. |
| `delete_page` | Delete a page (returns recovery token). Auto-removes from tree cache. |
| `clone_page` | Clone a page to a new location. Auto-adds clone to tree cache. |
| `append_content` | Append text to a page (top, bottom, section, or anchor) |
| `get_descendants` | Get all subpages (all levels) by page ID |
| `get_descendants_by_slug` | Get all subpages (all levels) by slug |

### Resources
| Tool | Description |
|------|-------------|
| `get_page_resources` | Get attachments, grids, and SharePoint docs for a page |
| `get_page_grids` | List grids attached to a page |

### Dynamic Tables (Grids)
| Tool | Description |
|------|-------------|
| `create_grid` | Create a table on a page |
| `get_grid` | Get a table with filtering and sorting |
| `update_grid` | Update title or sort order |
| `delete_grid` | Delete a table |
| `add_rows` | Add rows |
| `delete_rows` | Delete rows |
| `add_columns` | Add columns |
| `delete_columns` | Delete columns |
| `update_cells` | Update cell values |
| `move_rows` | Move rows |
| `move_columns` | Move columns |
| `clone_grid` | Clone a table to another page |

### Page Tree Cache
| Tool | Description |
|------|-------------|
| `get_tree` | Get tree from cache (default) or fresh from API (`use_cache=false`) |
| `refresh_tree_cache` | Full rebuild of tree cache from API by root slug |
| `clear_tree_cache` | Clear tree cache |
| `suggest_placement` | Suggest where to place a new page based on description |
| `add_tree_section` | Manually add a section to the tree |
| `remove_tree_section` | Manually remove a section from the tree |
| `set_tree` | Replace entire tree from YAML |

### Utilities
| Tool | Description |
|------|-------------|
| `convert_md_to_yfm` | Convert Markdown to YFM (tables, callouts, details, underline, highlight) |

### Prompt Manager
| Tool | Description |
|------|-------------|
| `prompts_list` | List all saved templates |
| `prompts_get` | Get and render a template with arguments |
| `prompts_add` | Create a template from chat |
| `prompts_add_from_file` | Load a template from a file |
| `prompts_remove` | Delete a template |

## Page Tree Cache

The server maintains a local tree cache (`tree.yaml`) that maps your wiki's section hierarchy. This cache is used by `get_tree` and `suggest_placement` to help with page navigation and placement.

**Auto-sync**: The cache updates automatically when you create, update, delete, or clone pages through the MCP tools.

**Manual refresh**: Use `refresh_tree_cache("root-slug")` to rebuild the cache from the API. This fetches all descendant pages and their titles.

```
# First time — initialize cache from your wiki root
refresh_tree_cache("your-root-slug")

# Quick check — read from cache (instant)
get_tree()

# Force fresh — bypass cache and fetch from API
get_tree(use_cache=false)

# Reset — clear and re-fetch
clear_tree_cache()
refresh_tree_cache("your-root-slug")
```

## Markdown to YFM Converter

Yandex Wiki uses YFM (Yandex Flavored Markdown), which differs from standard Markdown. The converter handles:

| Markdown | YFM |
|----------|-----|
| `\| H1 \| H2 \|` tables | `#\| \|\| \|#` wiki tables |
| `> [!NOTE]` callouts | `{% note info %}` |
| `<details><summary>` | `{% cut "Title" %}` |
| `<u>text</u>` | `++text++` |
| `<mark>text</mark>` | `==text==` |
| `<sup>text</sup>` | `text^super^` |
| `<sub>text</sub>` | `text~sub~` |

## License

MIT
