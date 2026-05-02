import logging
import random
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
import pytz

from db import get_all_active_users
from services import (
    get_prayer_times,
    format_time_12h,
    fetch_post_prayer_duas,
    fetch_morning_adhkar,
    fetch_evening_adhkar,
    fetch_random_adhkar,
    fetch_random_quran_verse,
)
from adhan_audio import send_adhan_audio
from messages import MSG, PRAYER_NAMES, PRAYER_ORDER

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()
_bot_app = None

TELEGRAM_MAX_LEN = 4000  # Leave buffer below 4096


def set_app(app):
    global _bot_app
    _bot_app = app


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


async def _send_chunked(bot, chat_id: int, header: str, items: list, lang: str):
    """
    Send all adhkar items as consecutive messages.
    Items that together exceed Telegram's limit are split into multiple
    messages, but each individual item is always kept intact.
    """
    item_template = MSG[lang]["adhkar_item"]
    chunks = []
    current = header

    for i, item in enumerate(items, start=1):
        entry = item_template.format(
            num=i,
            content=_escape(item.get("content", "")),
            description=_escape(item.get("description", "")),
            count=item.get("count", 1),
        )
        if len(current) + len(entry) > TELEGRAM_MAX_LEN:
            chunks.append(current)
            current = entry
        else:
            current += entry

    if current.strip():
        chunks.append(current)

    for chunk in chunks:
        await bot.send_message(chat_id=chat_id, text=chunk, parse_mode="HTML")


async def send_adhan(user_id: int, prayer_key: str, city: str, lang: str, timings: dict):
    if _bot_app is None:
        return
    user_db = await get_all_active_users()
    user_active = any(u["user_id"] == user_id for u in user_db)
    if not user_active:
        return

    try:
        prayer_display = PRAYER_NAMES[lang].get(prayer_key, prayer_key)
        idx = PRAYER_ORDER.index(prayer_key) if prayer_key in PRAYER_ORDER else -1
        next_key = PRAYER_ORDER[(idx + 1) % len(PRAYER_ORDER)] if idx >= 0 else "Fajr"
        next_name = PRAYER_NAMES[lang].get(next_key, next_key)
        raw_next = timings.get(next_key, "—")
        next_time = format_time_12h(raw_next, lang) if raw_next != "—" else "—"

        duas = await fetch_post_prayer_duas()
        dua_item = random.choice(duas) if duas else None
        if dua_item:
            content = _escape(dua_item.get("content", "…"))
            source = dua_item.get("source", "")
            desc = dua_item.get("description", "")
            # Format: source label + content + description
            if source:
                source_label = f"<i>({source})</i>\n" if lang == "ar" else f"<i>({source})</i>\n"
                dua_text = f"{source_label}{content}"
            else:
                dua_text = content
            if desc:
                dua_text += f"\n<i>— {_escape(desc)}</i>"
        else:
            dua_text = "…"

        # Send adhan audio clip first (best-effort — never blocks the text)
        await send_adhan_audio(_bot_app.bot, user_id, prayer_key)

        text = MSG[lang]["adhan_call"].format(
            prayer=prayer_display,
            city=_escape(city),
            next_prayer=next_name,
            next_time=next_time,
            dua=dua_text,
        )
        await _bot_app.bot.send_message(chat_id=user_id, text=text, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Error sending adhan to {user_id}: {e}")


async def send_morning_adhkar_job(user_id: int, lang: str):
    """Send ALL morning adhkar at 8:00 AM."""
    if _bot_app is None:
        return
    try:
        items = await fetch_morning_adhkar()
        if not items:
            return
        header = MSG[lang]["adhkar_morning_header"]
        await _send_chunked(_bot_app.bot, user_id, header, items, lang)
    except Exception as e:
        logger.error(f"Morning adhkar error for {user_id}: {e}")


async def send_evening_adhkar_job(user_id: int, lang: str):
    """Send ALL evening adhkar at 8:00 PM."""
    if _bot_app is None:
        return
    try:
        items = await fetch_evening_adhkar()
        if not items:
            return
        header = MSG[lang]["adhkar_evening_header"]
        await _send_chunked(_bot_app.bot, user_id, header, items, lang)
    except Exception as e:
        logger.error(f"Evening adhkar error for {user_id}: {e}")


async def send_daily_verse_job(user_id: int, lang: str):
    if _bot_app is None:
        return
    try:
        verse = await fetch_random_quran_verse()
        if not verse:
            return
        header = MSG[lang]["verse_header"]
        body = MSG[lang]["verse_body"].format(
            text=_escape(verse["text"]),
            surah=_escape(verse["surah"]),
            ayah=verse["ayah"],
        )
        await _bot_app.bot.send_message(
            chat_id=user_id, text=header + body, parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Daily verse error for {user_id}: {e}")


def _remove_user_jobs(user_id: int):
    prefix = f"user_{user_id}_"
    for job in scheduler.get_jobs():
        if job.id.startswith(prefix):
            job.remove()


async def schedule_user(user: dict):
    user_id = user["user_id"]
    lat = user["lat"]
    lon = user["lon"]
    lang = user.get("language", "ar")
    if lang == "ar":
        city = user.get("city_ar") or user.get("city") or "Unknown"
    else:
        city = user.get("city") or "Unknown"
    tz_name = user.get("timezone", "UTC")

    _remove_user_jobs(user_id)

    try:
        tz = pytz.timezone(tz_name)
    except Exception:
        tz = pytz.utc

    timings = await get_prayer_times(lat, lon)
    if not timings:
        logger.warning(f"Could not fetch prayer times for user {user_id}")
        return

    now = datetime.now(tz)

    for prayer_key in PRAYER_ORDER:
        time_str = timings.get(prayer_key)
        if not time_str:
            continue
        try:
            hour, minute = map(int, time_str.split(":"))
            run_time = tz.localize(
                datetime(now.year, now.month, now.day, hour, minute, 0)
            )
            if run_time <= now:
                continue
            scheduler.add_job(
                send_adhan,
                trigger=DateTrigger(run_date=run_time),
                args=[user_id, prayer_key, city, lang, timings],
                id=f"user_{user_id}_adhan_{prayer_key}",
                replace_existing=True,
                misfire_grace_time=300,
            )
        except Exception as e:
            logger.error(f"Scheduling adhan {prayer_key} for {user_id}: {e}")

    scheduler.add_job(
        send_morning_adhkar_job,
        trigger=CronTrigger(hour=8, minute=0, timezone=tz),
        args=[user_id, lang],
        id=f"user_{user_id}_morning",
        replace_existing=True,
        misfire_grace_time=600,
    )

    scheduler.add_job(
        send_evening_adhkar_job,
        trigger=CronTrigger(hour=20, minute=0, timezone=tz),
        args=[user_id, lang],
        id=f"user_{user_id}_evening",
        replace_existing=True,
        misfire_grace_time=600,
    )

    scheduler.add_job(
        send_daily_verse_job,
        trigger=CronTrigger(hour=9, minute=30, timezone=tz),
        args=[user_id, lang],
        id=f"user_{user_id}_verse",
        replace_existing=True,
        misfire_grace_time=600,
    )

    logger.info(f"Scheduled jobs for user {user_id} in {tz_name}")


async def schedule_all_users():
    users = await get_all_active_users()
    logger.info(f"Scheduling {len(users)} active users...")
    for user in users:
        await schedule_user(user)


def remove_user_jobs(user_id: int):
    _remove_user_jobs(user_id)
