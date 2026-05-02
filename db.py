import aiosqlite
import json
import logging
from typing import Optional

DB_PATH = "islamic_bot.db"
logger = logging.getLogger(__name__)


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id     INTEGER PRIMARY KEY,
                username    TEXT,
                first_name  TEXT,
                language    TEXT DEFAULT 'ar',
                lat         REAL,
                lon         REAL,
                city        TEXT,
                city_ar     TEXT,
                timezone    TEXT,
                active      INTEGER DEFAULT 1,
                created_at  TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS content_pointers (
                user_id     INTEGER,
                category    TEXT,
                last_index  INTEGER DEFAULT -1,
                PRIMARY KEY (user_id, category)
            );

            CREATE TABLE IF NOT EXISTS content_cache (
                key         TEXT PRIMARY KEY,
                data        TEXT,
                updated_at  TEXT DEFAULT (datetime('now'))
            );
        """)
        # Migration: add city_ar if missing (existing installs)
        try:
            await db.execute("ALTER TABLE users ADD COLUMN city_ar TEXT")
            await db.commit()
            logger.info("Migration: added city_ar column.")
        except Exception:
            pass  # Column already exists
        await db.commit()
    logger.info("Database initialized.")


async def upsert_user(user_id: int, **kwargs):
    async with aiosqlite.connect(DB_PATH) as db:
        existing = await db.execute(
            "SELECT user_id FROM users WHERE user_id = ?", (user_id,)
        )
        row = await existing.fetchone()
        if row:
            if kwargs:
                sets = ", ".join(f"{k} = ?" for k in kwargs)
                vals = list(kwargs.values()) + [user_id]
                await db.execute(f"UPDATE users SET {sets} WHERE user_id = ?", vals)
        else:
            cols = ["user_id"] + list(kwargs.keys())
            placeholders = ", ".join("?" for _ in cols)
            vals = [user_id] + list(kwargs.values())
            await db.execute(
                f"INSERT INTO users ({', '.join(cols)}) VALUES ({placeholders})", vals
            )
        await db.commit()


async def get_user(user_id: int) -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = await cur.fetchone()
        return dict(row) if row else None


async def get_all_active_users() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM users WHERE active = 1 AND lat IS NOT NULL"
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


async def set_user_active(user_id: int, active: bool):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET active = ? WHERE user_id = ?", (1 if active else 0, user_id)
        )
        await db.commit()


async def get_next_content(user_id: int, category: str, items: list) -> dict:
    """Pointer-based rotation. Never repeats until full cycle."""
    if not items:
        return {}
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT last_index FROM content_pointers WHERE user_id = ? AND category = ?",
            (user_id, category),
        )
        row = await cur.fetchone()
        last = row[0] if row else -1
        next_idx = (last + 1) % len(items)
        await db.execute(
            """INSERT INTO content_pointers (user_id, category, last_index)
               VALUES (?, ?, ?)
               ON CONFLICT(user_id, category) DO UPDATE SET last_index = excluded.last_index""",
            (user_id, category, next_idx),
        )
        await db.commit()
    return items[next_idx]


async def cache_set(key: str, data):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO content_cache (key, data, updated_at)
               VALUES (?, ?, datetime('now'))
               ON CONFLICT(key) DO UPDATE SET data = excluded.data, updated_at = excluded.updated_at""",
            (key, json.dumps(data, ensure_ascii=False)),
        )
        await db.commit()


async def get_all_users_stats() -> list[dict]:
    """Return all users (active and inactive) for stats."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT user_id, username, first_name, language, city, city_ar, timezone, active, created_at FROM users"
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


async def cache_get(key: str):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT data FROM content_cache WHERE key = ?", (key,)
        )
        row = await cur.fetchone()
        return json.loads(row[0]) if row else None
