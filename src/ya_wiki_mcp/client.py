from __future__ import annotations

import os

from dotenv import load_dotenv
from ya_wiki_api import AsyncWikiClient, WikiAPIError

load_dotenv()

__all__ = ["create_client", "WikiAPIError"]


def create_client() -> AsyncWikiClient:
    """Create an AsyncWikiClient configured from environment variables.

    Env vars: YA_WIKI_TOKEN, YA_WIKI_ORG_ID, YA_WIKI_ORG_TYPE (cloud/business).
    """
    token = os.environ.get("YA_WIKI_TOKEN", "")
    org_id = os.environ.get("YA_WIKI_ORG_ID", "")
    org_type = os.environ.get("YA_WIKI_ORG_TYPE", "cloud")

    if not token:
        raise ValueError(
            "YA_WIKI_TOKEN environment variable is not set. "
            "Get your token at https://oauth.yandex.ru/"
        )
    if not org_id:
        raise ValueError(
            "YA_WIKI_ORG_ID environment variable is not set. "
            "Find your org ID in Yandex 360 or Cloud console."
        )

    return AsyncWikiClient(
        token=token,
        cloud_org_id=org_id if org_type == "cloud" else None,
        org_id=org_id if org_type != "cloud" else None,
        is_iam=token.startswith("t1."),
    )
