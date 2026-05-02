"""
GitHub Gist as a content database.

On first run the bot creates a private Gist containing three JSON files
(morning_adhkar.json, evening_adhkar.json, post_prayer_duas.json).

The Gist ID is persisted in SQLite so subsequent starts re-use the same Gist.
Content can be edited directly on GitHub — the bot refreshes every hour.
"""

import os
import json
import logging
import httpx
import aiosqlite

from adhkar_data import MORNING_ADHKAR, EVENING_ADHKAR, POST_PRAYER_DUAS, ALL_ADHKAR

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"
DB_PATH = "islamic_bot.db"
GIST_DESCRIPTION = "Islamic Bot — Content Database (adhkar & duas)"

CONTENT_FILES = {
    "morning_adhkar.json": MORNING_ADHKAR,
    "evening_adhkar.json": EVENING_ADHKAR,
    "post_prayer_duas.json": POST_PRAYER_DUAS,
}


def _headers() -> dict:
    token = os.environ.get("GITHUB_TOKEN", "")
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


async def _get_stored_gist_id() -> str | None:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT data FROM content_cache WHERE key = 'gist_id'"
        )
        row = await cur.fetchone()
        return json.loads(row[0]) if row else None


async def _store_gist_id(gist_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO content_cache (key, data, updated_at)
               VALUES ('gist_id', ?, datetime('now'))
               ON CONFLICT(key) DO UPDATE
               SET data = excluded.data, updated_at = excluded.updated_at""",
            (json.dumps(gist_id),),
        )
        await db.commit()


async def _create_gist() -> str:
    files = {
        name: {"content": json.dumps(data, ensure_ascii=False, indent=2)}
        for name, data in CONTENT_FILES.items()
    }
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.post(
            f"{GITHUB_API}/gists",
            headers=_headers(),
            json={
                "description": GIST_DESCRIPTION,
                "public": False,
                "files": files,
            },
        )
        r.raise_for_status()
        gist = r.json()
        gist_id = gist["id"]
        html_url = gist["html_url"]
        logger.info(f"Created content Gist: {html_url}")
        return gist_id


async def _fetch_gist_file(gist_id: str, filename: str) -> list:
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as c:
        r = await c.get(f"{GITHUB_API}/gists/{gist_id}", headers=_headers())
        r.raise_for_status()
        files = r.json().get("files", {})
        file_info = files.get(filename)
        if not file_info:
            return []
        raw_url = file_info.get("raw_url", "")
        if not raw_url:
            return []
        r2 = await c.get(raw_url)
        r2.raise_for_status()
        data = r2.json()
        return data if isinstance(data, list) else []


async def ensure_gist() -> str:
    """Return Gist ID — create it if not yet stored."""
    gist_id = await _get_stored_gist_id()
    if gist_id:
        return gist_id
    try:
        gist_id = await _create_gist()
        await _store_gist_id(gist_id)
        return gist_id
    except Exception as e:
        logger.error(f"Failed to create Gist: {e}")
        return ""


async def get_gist_url() -> str:
    """Return the HTML URL of the content Gist."""
    gist_id = await _get_stored_gist_id()
    if not gist_id:
        return "Not created yet"
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.get(f"{GITHUB_API}/gists/{gist_id}", headers=_headers())
        if r.status_code == 200:
            return r.json().get("html_url", "")
    return ""


async def load_morning_adhkar() -> list:
    gist_id = await _get_stored_gist_id()
    if not gist_id:
        return MORNING_ADHKAR
    try:
        data = await _fetch_gist_file(gist_id, "morning_adhkar.json")
        return data if data else MORNING_ADHKAR
    except Exception as e:
        logger.warning(f"Gist read failed (morning): {e} — using built-in data")
        return MORNING_ADHKAR


async def load_evening_adhkar() -> list:
    gist_id = await _get_stored_gist_id()
    if not gist_id:
        return EVENING_ADHKAR
    try:
        data = await _fetch_gist_file(gist_id, "evening_adhkar.json")
        return data if data else EVENING_ADHKAR
    except Exception as e:
        logger.warning(f"Gist read failed (evening): {e} — using built-in data")
        return EVENING_ADHKAR


async def load_post_prayer_duas() -> list:
    gist_id = await _get_stored_gist_id()
    if not gist_id:
        return POST_PRAYER_DUAS
    try:
        data = await _fetch_gist_file(gist_id, "post_prayer_duas.json")
        return data if data else POST_PRAYER_DUAS
    except Exception as e:
        logger.warning(f"Gist read failed (duas): {e} — using built-in data")
        return POST_PRAYER_DUAS


async def load_all_adhkar() -> list:
    """Return the full unified adhkar collection (all categories)."""
    return ALL_ADHKAR


async def push_to_gist(filename: str, data: list) -> bool:
    """Update a single file in the Gist."""
    gist_id = await _get_stored_gist_id()
    if not gist_id:
        return False
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.patch(
                f"{GITHUB_API}/gists/{gist_id}",
                headers=_headers(),
                json={"files": {filename: {"content": json.dumps(data, ensure_ascii=False, indent=2)}}},
            )
            r.raise_for_status()
            return True
    except Exception as e:
        logger.error(f"Gist push failed: {e}")
        return False
