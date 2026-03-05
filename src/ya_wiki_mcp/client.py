from __future__ import annotations

import json
import os
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://api.wiki.yandex.net"


class WikiAPIError(Exception):
    """Yandex Wiki API error with structured details."""

    def __init__(self, status_code: int, error_code: str, message: str, details: dict[str, Any] | None = None):
        self.status_code = status_code
        self.error_code = error_code
        self.details = details
        super().__init__(message)


def _headers() -> dict[str, str]:
    token = os.environ.get("YA_WIKI_TOKEN", "")
    org_id = os.environ.get("YA_WIKI_ORG_ID", "")
    org_type = os.environ.get("YA_WIKI_ORG_TYPE", "cloud")

    if not token:
        raise WikiAPIError(0, "CONFIG_ERROR", "YA_WIKI_TOKEN environment variable is not set. Get your token at https://oauth.yandex.ru/")
    if not org_id:
        raise WikiAPIError(0, "CONFIG_ERROR", "YA_WIKI_ORG_ID environment variable is not set. Find your org ID in Yandex 360 or Cloud console.")

    auth_prefix = "OAuth" if not token.startswith("t1.") else "Bearer"
    org_header = "X-Cloud-Org-Id" if org_type == "cloud" else "X-Org-Id"

    return {
        "Authorization": f"{auth_prefix} {token}",
        org_header: org_id,
        "Content-Type": "application/json",
    }


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url=BASE_URL, headers=_headers(), timeout=30.0)


async def _handle_response(r: httpx.Response) -> dict[str, Any]:
    if r.is_success:
        if r.status_code == 204:
            return {}
        return r.json()

    try:
        body = r.json()
    except (json.JSONDecodeError, ValueError):
        raise WikiAPIError(r.status_code, "HTTP_ERROR", f"HTTP {r.status_code}: {r.text[:500]}")

    error_code = body.get("error_code", "UNKNOWN")
    message = body.get("message") or body.get("debug_message") or f"HTTP {r.status_code}"
    details = body.get("details")
    raise WikiAPIError(r.status_code, error_code, message, details)


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

async def get_page(
    *,
    slug: str | None = None,
    page_id: int | None = None,
    fields: str | None = None,
    raise_on_redirect: bool = False,
    revision_id: int | None = None,
) -> dict[str, Any]:
    params: dict[str, Any] = {}
    if fields:
        params["fields"] = fields
    if raise_on_redirect:
        params["raise_on_redirect"] = True
    if revision_id is not None:
        params["revision_id"] = revision_id

    async with _client() as c:
        if page_id is not None:
            r = await c.get(f"/v1/pages/{page_id}", params=params)
        elif slug is not None:
            params["slug"] = slug
            r = await c.get("/v1/pages", params=params)
        else:
            raise WikiAPIError(0, "PARAM_ERROR", "Either slug or page_id must be provided")
        return await _handle_response(r)


async def create_page(
    *,
    page_type: str,
    title: str,
    slug: str,
    content: str | None = None,
    grid_format: str | None = None,
    cloud_page: dict[str, Any] | None = None,
    fields: str | None = None,
    is_silent: bool = False,
) -> dict[str, Any]:
    params: dict[str, Any] = {}
    if fields:
        params["_fields"] = fields
    if is_silent:
        params["is_silent"] = True

    body: dict[str, Any] = {"page_type": page_type, "title": title, "slug": slug}
    if content is not None:
        body["content"] = content
    if grid_format:
        body["grid_format"] = grid_format
    if cloud_page:
        body["cloud_page"] = cloud_page

    async with _client() as c:
        r = await c.post("/v1/pages", params=params, json=body)
        return await _handle_response(r)


async def update_page(
    *,
    page_id: int,
    title: str | None = None,
    content: str | None = None,
    redirect: dict[str, Any] | None = None,
    allow_merge: bool = False,
    fields: str | None = None,
    is_silent: bool = False,
) -> dict[str, Any]:
    params: dict[str, Any] = {}
    if allow_merge:
        params["allow_merge"] = True
    if fields:
        params["fields"] = fields
    if is_silent:
        params["is_silent"] = True

    body: dict[str, Any] = {}
    if title is not None:
        body["title"] = title
    if content is not None:
        body["content"] = content
    if redirect is not None:
        body["redirect"] = redirect

    async with _client() as c:
        r = await c.post(f"/v1/pages/{page_id}", params=params, json=body)
        return await _handle_response(r)


async def delete_page(*, page_id: int) -> dict[str, Any]:
    async with _client() as c:
        r = await c.delete(f"/v1/pages/{page_id}")
        return await _handle_response(r)


async def clone_page(
    *,
    page_id: int,
    target: str,
    title: str | None = None,
    subscribe_me: bool = False,
) -> dict[str, Any]:
    body: dict[str, Any] = {"target": target}
    if title:
        body["title"] = title
    if subscribe_me:
        body["subscribe_me"] = True

    async with _client() as c:
        r = await c.post(f"/v1/pages/{page_id}/clone", json=body)
        return await _handle_response(r)


async def append_content(
    *,
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
) -> dict[str, Any]:
    params: dict[str, Any] = {}
    if fields:
        params["fields"] = fields
    if is_silent:
        params["is_silent"] = True

    payload: dict[str, Any] = {"content": content}
    if body_location:
        payload["body"] = {"location": body_location}
    if section_id is not None:
        section: dict[str, Any] = {"id": section_id}
        if section_location:
            section["location"] = section_location
        payload["section"] = section
    if anchor_name:
        anchor: dict[str, Any] = {"name": anchor_name}
        if anchor_fallback:
            anchor["fallback"] = True
        if anchor_regex:
            anchor["regex"] = True
        payload["anchor"] = anchor

    async with _client() as c:
        r = await c.post(f"/v1/pages/{page_id}/append-content", params=params, json=payload)
        return await _handle_response(r)


# ---------------------------------------------------------------------------
# Page Resources
# ---------------------------------------------------------------------------

async def get_page_resources(
    *,
    page_id: int,
    cursor: str | None = None,
    order_by: str | None = None,
    order_direction: str | None = None,
    page_num: int | None = None,
    page_size: int | None = None,
    q: str | None = None,
    types: str | None = None,
) -> dict[str, Any]:
    params: dict[str, Any] = {}
    if cursor:
        params["cursor"] = cursor
    if order_by:
        params["order_by"] = order_by
    if order_direction:
        params["order_direction"] = order_direction
    if page_num is not None:
        params["page_id"] = page_num
    if page_size is not None:
        params["page_size"] = page_size
    if q:
        params["q"] = q
    if types:
        params["types"] = types

    async with _client() as c:
        r = await c.get(f"/v1/pages/{page_id}/resources", params=params)
        return await _handle_response(r)


async def get_page_grids(
    *,
    page_id: int,
    cursor: str | None = None,
    order_by: str | None = None,
    order_direction: str | None = None,
    page_num: int | None = None,
    page_size: int | None = None,
) -> dict[str, Any]:
    params: dict[str, Any] = {}
    if cursor:
        params["cursor"] = cursor
    if order_by:
        params["order_by"] = order_by
    if order_direction:
        params["order_direction"] = order_direction
    if page_num is not None:
        params["page_id"] = page_num
    if page_size is not None:
        params["page_size"] = page_size

    async with _client() as c:
        r = await c.get(f"/v1/pages/{page_id}/grids", params=params)
        return await _handle_response(r)


# ---------------------------------------------------------------------------
# Grids
# ---------------------------------------------------------------------------

async def create_grid(
    *,
    title: str,
    page_id: int | None = None,
    page_slug: str | None = None,
) -> dict[str, Any]:
    page: dict[str, Any] = {}
    if page_id is not None:
        page["id"] = page_id
    elif page_slug:
        page["slug"] = page_slug
    else:
        raise WikiAPIError(0, "PARAM_ERROR", "Either page_id or page_slug must be provided")

    async with _client() as c:
        r = await c.post("/v1/grids", json={"title": title, "page": page})
        return await _handle_response(r)


async def get_grid(
    *,
    grid_id: str,
    fields: str | None = None,
    filter: str | None = None,
    only_cols: str | None = None,
    only_rows: str | None = None,
    revision: int | None = None,
    sort: str | None = None,
) -> dict[str, Any]:
    params: dict[str, Any] = {}
    if fields:
        params["fields"] = fields
    if filter:
        params["filter"] = filter
    if only_cols:
        params["only_cols"] = only_cols
    if only_rows:
        params["only_rows"] = only_rows
    if revision is not None:
        params["revision"] = revision
    if sort:
        params["sort"] = sort

    async with _client() as c:
        r = await c.get(f"/v1/grids/{grid_id}", params=params)
        return await _handle_response(r)


async def update_grid(
    *,
    grid_id: str,
    revision: str,
    title: str | None = None,
    default_sort: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {"revision": revision}
    if title:
        body["title"] = title
    if default_sort is not None:
        body["default_sort"] = default_sort

    async with _client() as c:
        r = await c.post(f"/v1/grids/{grid_id}", json=body)
        return await _handle_response(r)


async def delete_grid(*, grid_id: str) -> dict[str, Any]:
    async with _client() as c:
        r = await c.delete(f"/v1/grids/{grid_id}")
        return await _handle_response(r)


async def add_rows(
    *,
    grid_id: str,
    rows: list[dict[str, Any]],
    revision: str | None = None,
    position: int | None = None,
    after_row_id: str | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {"rows": rows}
    if revision:
        body["revision"] = revision
    if position is not None:
        body["position"] = position
    if after_row_id:
        body["after_row_id"] = after_row_id

    async with _client() as c:
        r = await c.post(f"/v1/grids/{grid_id}/rows", json=body)
        return await _handle_response(r)


async def delete_rows(
    *,
    grid_id: str,
    row_ids: list[str],
    revision: str | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {"row_ids": row_ids}
    if revision:
        body["revision"] = revision

    async with _client() as c:
        r = await c.request("DELETE", f"/v1/grids/{grid_id}/rows", json=body)
        return await _handle_response(r)


async def add_columns(
    *,
    grid_id: str,
    columns: list[dict[str, Any]],
    revision: str | None = None,
    position: int | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {"columns": columns}
    if revision:
        body["revision"] = revision
    if position is not None:
        body["position"] = position

    async with _client() as c:
        r = await c.post(f"/v1/grids/{grid_id}/columns", json=body)
        return await _handle_response(r)


async def delete_columns(
    *,
    grid_id: str,
    column_slugs: list[str],
    revision: str | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {"column_slugs": column_slugs}
    if revision:
        body["revision"] = revision

    async with _client() as c:
        r = await c.request("DELETE", f"/v1/grids/{grid_id}/columns", json=body)
        return await _handle_response(r)


async def update_cells(
    *,
    grid_id: str,
    cells: list[dict[str, Any]],
    revision: str | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {"cells": cells}
    if revision:
        body["revision"] = revision

    async with _client() as c:
        r = await c.post(f"/v1/grids/{grid_id}/cells", json=body)
        return await _handle_response(r)


async def move_rows(
    *,
    grid_id: str,
    row_id: str,
    revision: str,
    position: int | None = None,
    after_row_id: str | None = None,
    rows_count: int = 1,
) -> dict[str, Any]:
    body: dict[str, Any] = {"revision": revision, "row_id": row_id, "rows_count": rows_count}
    if position is not None:
        body["position"] = position
    if after_row_id:
        body["after_row_id"] = after_row_id

    async with _client() as c:
        r = await c.post(f"/v1/grids/{grid_id}/rows/move", json=body)
        return await _handle_response(r)


async def move_columns(
    *,
    grid_id: str,
    column_slug: str,
    revision: str,
    position: int | None = None,
    columns_count: int = 1,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "revision": revision,
        "column_slug": column_slug,
        "columns_count": columns_count,
    }
    if position is not None:
        body["position"] = position

    async with _client() as c:
        r = await c.post(f"/v1/grids/{grid_id}/columns/move", json=body)
        return await _handle_response(r)


async def clone_grid(
    *,
    grid_id: str,
    target: str,
    title: str | None = None,
    with_data: bool = False,
) -> dict[str, Any]:
    body: dict[str, Any] = {"target": target}
    if title:
        body["title"] = title
    if with_data:
        body["with_data"] = True

    async with _client() as c:
        r = await c.post(f"/v1/grids/{grid_id}/clone", json=body)
        return await _handle_response(r)
