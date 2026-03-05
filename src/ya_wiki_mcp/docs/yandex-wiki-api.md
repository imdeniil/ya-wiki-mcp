# Yandex Wiki API Reference

Источник: https://yandex.ru/support/wiki/ru/api-ref/about

## Base URL

```
https://api.wiki.yandex.net/v1
```

## Authentication

Two methods supported:

### OAuth 2.0

1. Create app at https://oauth.yandex.ru/
2. Select "Для доступа к API или отладки"
3. Add permissions: `wiki:write` (full) or `wiki:read` (read-only)
4. Get token via: `https://oauth.yandex.ru/authorize?response_type=token&client_id=<ClientID>`

### IAM Token (Yandex Cloud only)

- Max lifetime: 12 hours
- Limited by federation cookie lifetime

### Required Headers

```
Authorization: OAuth <token>       # for OAuth
Authorization: Bearer <token>      # for IAM

X-Org-Id: <org-id>                 # Yandex 360 for Business
X-Cloud-Org-Id: <org-id>           # Yandex Cloud Organization
```

**Note:** Service accounts cannot be used for API authorization.

---

## Pages API

### Get Page Details

```
GET /v1/pages?slug={slug}
```

**Query Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `slug` | string | Yes | Non-normalized page slug, e.g. `users/something/abc` |
| `fields` | string | No | Additional response blocks, comma-separated |
| `raise_on_redirect` | boolean | No | Raise error if page has redirect (default: false) |
| `revision_id` | integer | No | Specific revision ID |

**Response (200):**

```json
{
  "id": 123,
  "slug": "users/test/page",
  "title": "Page Title",
  "page_type": "wysiwyg",
  "attributes": { ... },
  "breadcrumbs": [ ... ],
  "content": "...",
  "redirect": { ... }
}
```

### Get Page Details by ID

```
GET /v1/pages/{idx}
```

**Path Parameters:**

| Name | Type | Description |
|------|------|-------------|
| `idx` | integer | Page ID |

**Query Parameters:** same as Get Page Details (`fields`, `raise_on_redirect`, `revision_id`)

**Response:** same schema as Get Page Details.

### Create Page

```
POST /v1/pages
```

**Query Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `_fields` | string | — | Response fields to include |
| `is_silent` | boolean | false | Silent mode |

**Request Body:**

```json
{
  "page_type": "wysiwyg",
  "title": "Page Title",
  "slug": "users/test/newpage",
  "content": "Page body text",
  "grid_format": "yfm"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `page_type` | PageType | Yes | `page`, `grid`, `cloud_page`, `wysiwyg`, `template` |
| `title` | string | Yes | 1–255 chars |
| `slug` | string | Yes | URL path |
| `content` | string | No | Page body |
| `grid_format` | TextFormat | No | `yfm`, `wom`, `plain` |
| `cloud_page` | object | No | MS365 cloud page config (see below) |

**Cloud Page Methods:**

| method | Description | Extra fields |
|--------|-------------|-------------|
| `empty_doc` | Create empty document | `doctype`: `docx`, `pptx`, `xlsx` |
| `from_url` | Import from URL | `url`: string |
| `upload_doc` | Start file upload | `mimetype`: string |
| `finalize_upload` | Complete upload | `upload_session`: string |
| `upload_onprem` | On-premise upload | `upload_session`: string |

**Response (200):** PageFullDetailsSchema or Ms365UploadSessionSchema.

Ms365UploadSessionSchema:
```json
{
  "upload_to": "https://...",
  "upload_session": "session-id"
}
```

### Update Page

```
POST /v1/pages/{idx}
```

**Query Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `allow_merge` | boolean | false | Merge simultaneous edits via 3-way-merge |
| `fields` | string | — | Additional response fields |
| `is_silent` | boolean | false | Silent mode |

**Request Body:**

```json
{
  "title": "New Title",
  "content": "Updated content",
  "redirect": {
    "page": { "id": 456 }
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `title` | string | 1–255 chars |
| `content` | string | New page content |
| `redirect` | object | Set redirect; `null` to remove. Inner `page` has `id` (priority) or `slug` |

**Response:** PageFullDetailsSchema.

### Delete Page

```
DELETE /v1/pages/{idx}
```

**Response (200):**

```json
{
  "recovery_token": "uuid4-string"
}
```

### Clone Page

```
POST /v1/pages/{idx}/clone
```

**Request Body:**

```json
{
  "target": "users/test/copy",
  "title": "Cloned Page",
  "subscribe_me": false
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `target` | string | Yes | Destination slug |
| `title` | string | No | New title, 1–255 chars |
| `subscribe_me` | boolean | No | Subscribe to changes (default: false) |

**Response (200):**

```json
{
  "operation": { "type": "clone", "id": "op-id" },
  "dry_run": false,
  "status_url": "https://..."
}
```

**Validation Errors:** `IS_CLOUD_PAGE`, `SLUG_OCCUPIED`, `SLUG_RESERVED`, `FORBIDDEN`, `QUOTA_EXCEEDED`, `CLUSTER_BLOCKED`

### Get Page Grids

```
GET /v1/pages/{idx}/grids
```

**Query Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `cursor` | string | — | Pagination cursor |
| `order_by` | string | — | `title` or `created_at` |
| `order_direction` | string | `asc` | `asc` or `desc` |
| `page_id` | integer | 1 | Legacy page number (min: 1) |
| `page_size` | integer | 25 | Results per page (1–50) |

**Response (200):**

```json
{
  "results": [
    { "id": "uuid4", "title": "Table", "created_at": "2024-01-01T00:00:00Z" }
  ],
  "next_cursor": "...",
  "prev_cursor": "...",
  "has_next": true,
  "page_id": 1
}
```

### Append Content

```
POST /v1/pages/{idx}/append-content
```

**Query Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `fields` | string | — | Response fields |
| `is_silent` | boolean | false | Silent mode |

**Request Body:**

```json
{
  "content": "Text to append",
  "body": { "location": "bottom" },
  "section": { "id": 1, "location": "top" },
  "anchor": { "name": "#heading", "fallback": false, "regex": false }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `content` | string | Yes | Text to add (min 1 char) |
| `body.location` | string | No | `top` or `bottom` |
| `section.id` | integer | No | Target section ID |
| `section.location` | string | No | `top` or `bottom` within section |
| `anchor.name` | string | No | Anchor reference point |
| `anchor.fallback` | boolean | No | Enable fallback matching (default: false) |
| `anchor.regex` | boolean | No | Treat anchor as regex (default: false) |

Only one of `body`, `section`, or `anchor` should be used. **Response:** PageFullDetailsSchema.

---

## Page Resources API

### Get Resources

```
GET /v1/pages/{idx}/resources
```

**Path Parameters:**

| Name | Type | Description |
|------|------|-------------|
| `idx` | integer | Page ID |

**Query Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `cursor` | string | — | Pagination cursor |
| `order_by` | string | — | `name_title` or `created_at` |
| `order_direction` | string | `asc` | `asc` or `desc` |
| `page_id` | integer | 1 | Legacy page number (min: 1) |
| `page_size` | integer | 25 | Results per page (1–50) |
| `q` | string | — | Search by title (max 255 chars) |
| `types` | string | — | Filter by type, comma-separated: `attachment`, `sharepoint_resource`, `grid` |

**Response (200):**

```json
{
  "results": [
    {
      "type": "attachment",
      "item": { ... }
    }
  ],
  "next_cursor": "...",
  "prev_cursor": "..."
}
```

Each resource has `type` (ResourceType) and `item` (one of three schemas based on type):

**AttachmentSchema** (type: `attachment`):

| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Attachment ID |
| `name` | string | File name |
| `download_url` | string | Download URL |
| `size` | string | File size |
| `description` | string | Description |
| `user` | UserSchema | Uploader |
| `created_at` | string (date-time) | Upload time |
| `mimetype` | string | MIME type |
| `has_preview` | boolean | Has preview |

**PageGridsSchema** (type: `grid`):

| Field | Type | Description |
|-------|------|-------------|
| `id` | string (uuid4) | Grid ID |
| `title` | string | Grid title |
| `created_at` | string (date-time) | Creation time |

**PageSharepointSchema** (type: `sharepoint_resource`):

| Field | Type | Description |
|-------|------|-------------|
| `id` | string (uuid4) | Resource ID |
| `title` | string | Title |
| `created_at` | string (date-time) | Creation time |
| `doctype` | Ms365DocType | `docx`, `pptx`, `xlsx` |

---

## Grids (Dynamic Tables) API

### Create Grid

```
POST /v1/grids
```

**Request Body:**

```json
{
  "title": "My Table",
  "page": { "id": 123 }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | string | Yes | 1–255 chars |
| `page` | PageIdentity | Yes | `id` (integer, priority) or `slug` (string) |

**Response (200):** Full GridSchema (see below).

### Get Grid

```
GET /v1/grids/{idx}
```

**Path Parameters:**

| Name | Type | Description |
|------|------|-------------|
| `idx` | string (uuid4) | Grid ID |

**Query Parameters:**

| Name | Type | Description |
|------|------|-------------|
| `fields` | string | Additional fields, comma-separated |
| `filter` | string | Row filter, e.g. `[slug] ~ wiki AND [slug2]<32` |
| `only_cols` | string | Return specific columns by slug |
| `only_rows` | string | Return specific rows by ID |
| `revision` | integer | Load specific grid version |
| `sort` | string | Sort rows, e.g. `slug, -slug2` (prefix `-` for desc) |

**Response (200):** Full GridSchema.

### Update Grid

```
POST /v1/grids/{idx}
```

**Request Body:**

```json
{
  "revision": "rev-string",
  "title": "Updated Title",
  "default_sort": [{ "column_slug": "asc" }]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `revision` | string | Current revision |
| `title` | string | 1–255 chars |
| `default_sort` | object[] | Column slug → `asc` or `desc` |

**Response (200):** `{ "revision": "new-rev" }`

### Delete Grid

```
DELETE /v1/grids/{idx}
```

**Response:** 204 No Content, empty body.

### Add Rows

```
POST /v1/grids/{idx}/rows
```

**Request Body:**

```json
{
  "revision": "rev",
  "position": 0,
  "after_row_id": "row-id",
  "rows": [
    { "column_slug": "value", "another_col": 42 }
  ]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `rows` | object[] | Yes | Row data keyed by column slug |
| `after_row_id` | string | No | Insert after this row |
| `position` | integer | No | Insert at position |
| `revision` | string | No | Current revision |

Cell values can be: `integer`, `number`, `boolean`, `string`, `string[]`, `UserIdentityExtended[]`.

**Response (200):**

```json
{
  "revision": "new-rev",
  "results": [{ "id": "row-id", "row": [...], "pinned": false, "color": null }]
}
```

### Delete Rows

```
DELETE /v1/grids/{idx}/rows
```

**Request Body:**

```json
{
  "revision": "rev",
  "row_ids": ["row-1", "row-2"]
}
```

**Response (200):** `{ "revision": "new-rev" }`

### Add Columns

```
POST /v1/grids/{idx}/columns
```

**Request Body:**

```json
{
  "revision": "rev",
  "position": 0,
  "columns": [
    {
      "slug": "col_name",
      "title": "Column Name",
      "type": "string",
      "required": false,
      "width": 200,
      "width_units": "px",
      "pinned": null,
      "color": null,
      "multiple": false,
      "format": "plain",
      "select_options": [],
      "mark_rows": false,
      "description": "Column description"
    }
  ]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `columns` | NewColumnSchema[] | Yes | Columns to add |
| `revision` | string | No | Current revision |
| `position` | integer | No | Insert position |

**NewColumnSchema:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | string | Yes | 1–255 chars |
| `type` | ColumnType | Yes | Column data type |
| `slug` | string | **Yes*** | Column slug. *Docs say optional, but API returns 400 without it |
| `required` | boolean | **Yes*** | Required field. *Docs say optional, but API returns 400 without it |
| `id` | string | No | Column ID |
| `width` | integer | No | Column width |
| `width_units` | string | No | `%` or `px` |
| `pinned` | string | No | `left` or `right` |
| `color` | BGColor | No | Header background |
| `multiple` | boolean | No | For `select`/`staff` only |
| `format` | TextFormat | No | For `string` only: `yfm`, `wom`, `plain` |
| `ticket_field` | TicketField | No | For `ticket_field` only |
| `select_options` | string[] | No | For `select` only |
| `mark_rows` | boolean | No | For `checkbox` only |
| `description` | string | No | Max 1024 chars |

**Response (200):** `{ "revision": "new-rev" }`

### Delete Columns

```
DELETE /v1/grids/{idx}/columns
```

**Request Body:**

```json
{
  "revision": "rev",
  "column_slugs": ["col1", "col2"]
}
```

**Response (200):** `{ "revision": "new-rev" }`

### Update Cells

```
POST /v1/grids/{idx}/cells
```

**Request Body:**

```json
{
  "revision": "rev",
  "cells": [
    { "row_id": 1, "column_slug": "name", "value": "New Value" }
  ]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `cells` | UpdateCellSchema[] | Yes | Cells to update |
| `revision` | string | No | Current revision |

UpdateCellSchema: `row_id` (integer), `column_slug` (string), `value` (integer | number | boolean | string | string[] | UserIdentityExtended[])

**Response (200):**

```json
{
  "revision": "new-rev",
  "cells": [{ "row_id": "1", "column_slug": "name", "value": "New Value" }]
}
```

### Move Rows

```
POST /v1/grids/{idx}/rows/move
```

**Request Body:**

```json
{
  "revision": "rev",
  "row_id": "row-1",
  "position": 0,
  "after_row_id": "row-0",
  "rows_count": 1
}
```

**Response (200):** `{ "revision": "new-rev" }`

### Move Columns

```
POST /v1/grids/{idx}/columns/move
```

**Request Body:**

```json
{
  "revision": "rev",
  "column_slug": "col1",
  "position": 2,
  "columns_count": 1
}
```

**Response (200):** `{ "revision": "new-rev" }`

### Clone Grid

```
POST /v1/grids/{idx}/clone
```

**Request Body:**

```json
{
  "target": "users/test/table-copy",
  "title": "Cloned Table",
  "with_data": true
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `target` | string | Yes | Destination page slug (creates page if needed) |
| `title` | string | No | New title, 1–255 chars |
| `with_data` | boolean | No | Copy data too (default: false) |

**Response (200):**

```json
{
  "operation": { "type": "clone_grid", "id": "op-id" },
  "dry_run": false,
  "status_url": "https://..."
}
```

---

## Common Schemas

### PageType (enum)

`page`, `grid`, `cloud_page`, `wysiwyg`, `template`

### TextFormat (enum)

`yfm`, `wom`, `plain`

### PageIdentity

```json
{ "id": 123, "slug": "path/to/page" }
```

`id` takes priority over `slug` when both provided.

### PageFullDetailsSchema

```json
{
  "id": 123,
  "slug": "path/to/page",
  "title": "Title",
  "page_type": "wysiwyg",
  "attributes": PageAttributesSchema,
  "breadcrumbs": BreadcrumbSchema[],
  "content": "string | CloudPageContentSchema | LegacyGridSchema",
  "redirect": RedirectSchema
}
```

Fields `attributes`, `breadcrumbs`, `content`, `redirect` are **not returned by default** — request via `?fields=attributes,breadcrumbs,content,redirect`.

### PageAttributesSchema

```json
{
  "created_at": "2024-01-01T00:00:00Z",
  "modified_at": "2024-01-01T00:00:00Z",
  "lang": "ru",
  "is_readonly": false,
  "comments_count": 5,
  "comments_enabled": true,
  "keywords": ["wiki", "docs"],
  "is_collaborative": false,
  "is_draft": false
}
```

### BreadcrumbSchema

```json
{ "id": 1, "title": "Parent", "slug": "parent", "page_exists": true }
```

**Note:** `id` is optional — API may omit it for non-existent parent pages.

### RedirectSchema

```json
{
  "page_id": 456,
  "redirect_target": { "id": 456, "slug": "target", "title": "Target Page", "page_type": "page" }
}
```

### CloudPageContentSchema

```json
{
  "embed": { "iframe_src": "https://...", "edit_src": "https://..." },
  "acl_management": "wiki",
  "type": "docx",
  "filename": "document.docx",
  "error": null
}
```

### GridSchema (full response)

```json
{
  "id": "uuid4",
  "created_at": "2024-01-01T00:00:00Z",
  "title": "Table Name",
  "page": { "id": 123, "slug": "page/slug" },
  "structure": GridStructureSchema,
  "rich_text_format": "yfm",
  "rows": GridRowSchema[],
  "revision": "rev-string",
  "attributes": GridAttributesSchema,
  "user_permissions": UserPermission[],
  "template_id": null
}
```

### GridStructureSchema

```json
{
  "default_sort": [{ "slug": "col", "title": "Col", "direction": "asc" }],
  "columns": ColumnSchema[]
}
```

### ColumnSchema

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Column ID |
| `slug` | string | Column slug |
| `title` | string | Display name |
| `type` | ColumnType | `string`, `number`, `date`, `select`, `staff`, `checkbox`, `ticket`, `ticket_field` |
| `required` | boolean | Required field |
| `width` | integer | Column width |
| `width_units` | string | `%` or `px` |
| `pinned` | string | `left`, `right`, or null |
| `color` | BGColor | Background color |
| `multiple` | boolean | Allow multiple values (for `select`, `staff`) |
| `format` | TextFormat | `yfm`, `wom`, `plain` |
| `select_options` | string[] | Options for `select` type |
| `mark_rows` | boolean | For `checkbox` — color the row |
| `description` | string | Column description |
| `ticket_field` | TicketField | For `ticket_field` type |

### ColumnType (enum)

`string`, `number`, `date`, `select`, `staff`, `checkbox`, `ticket`, `ticket_field`

### TicketField (enum)

`assignee`, `components`, `created_at`, `deadline`, `description`, `end`, `estimation`, `fixversions`, `followers`, `key`, `last_comment_updated_at`, `original_estimation`, `parent`, `pending_reply_from`, `priority`, `project`, `queue`, `reporter`, `resolution`, `resolved_at`, `sprint`, `start`, `status`, `status_start_time`, `status_type`, `storypoints`, `subject`, `tags`, `type`, `updated_at`, `votes`

### BGColor (enum)

`blue`, `yellow`, `pink`, `red`, `green`, `mint`, `grey`, `orange`, `magenta`, `purple`, `copper`, `ocean`

### GridRowSchema

```json
{ "id": "row-id", "row": [...values], "pinned": false, "color": null }
```

Row values can be: `integer`, `number`, `boolean`, `string`, `TicketSchema`, `string[]`, `UserSchema[]`, `UnresolvedUserSchema[]`, `UserSchema`, `UnresolvedUserSchema`, `TrackerEnumField`.

### GridAttributesSchema

```json
{ "created_at": "2024-01-01T00:00:00Z", "modified_at": "2024-01-01T00:00:00Z" }
```

### UserSchema

```json
{
  "id": 1,
  "identity": { "uid": "123", "cloud_uid": "abc" },
  "username": "user",
  "display_name": "User Name",
  "is_dismissed": false
}
```

### UserIdentityExtended (for writes)

```json
{ "uid": "123", "cloud_uid": "abc", "username": "user" }
```

### UnresolvedUserSchema

```json
{ "username": "user", "identity": { "uid": "123", "cloud_uid": "abc" } }
```

### TicketSchema

```json
{ "key": "QUEUE-123", "resolved": false }
```

### TrackerEnumField

```json
{ "display": "Critical", "key": "critical" }
```

### UserPermission (enum)

`create_page`, `delete`, `edit`, `view`, `comment`, `change_authors`, `change_acl`, `set_redirect`, `manage_invite`, `view_invite`, `admin`

### OperationType (enum)

`test`, `export`, `move`, `clone`, `clone_grid`, `clone_inline_grid`, `apply_template`, `e2e_prepare`, `e2e_cleanup`

---

## Error Handling

- **401 Unauthorized** — expired or invalid token
- **400 VALIDATION_ERROR** — body with `error_code`, `message`, `details` describing which fields failed
- Clone validation errors: `IS_CLOUD_PAGE`, `SLUG_OCCUPIED`, `SLUG_RESERVED`, `FORBIDDEN`, `QUOTA_EXCEEDED`, `CLUSTER_BLOCKED`

Error response format:
```json
{
  "error_code": "VALIDATION_ERROR",
  "debug_message": "Validation failed",
  "message": "columns: Поле должно быть заполнено",
  "details": { "body": { ... } }
}
```

---

## Discovered Discrepancies (docs vs real API)

Findings from smoke-testing all 21 endpoints against the live API:

| Issue | Official docs | Actual behavior |
|-------|---------------|-----------------|
| `NewColumnSchema.slug` | Optional | **Required** — API returns 400 without it |
| `NewColumnSchema.required` | Optional | **Required** — API returns 400 without it |
| `BreadcrumbSchema.id` | Required (integer) | **Optional** — not returned for non-existent parent pages |
