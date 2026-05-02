import logging
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

import random
import os
from db import upsert_user, get_user, set_user_active, get_all_users_stats
from adhan_audio import send_adhan_audio
from services import (
    get_location_names,
    get_timezone,
    get_prayer_times,
    format_time_12h,
    fetch_morning_adhkar,
    fetch_evening_adhkar,
    fetch_post_prayer_duas,
    fetch_random_quran_verse,
)
from gist_db import get_gist_url
from messages import MSG, PRAYER_NAMES, PRAYER_ORDER
from scheduler import schedule_user, remove_user_jobs

logger = logging.getLogger(__name__)

TELEGRAM_MAX_LEN = 4000


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _display_name(update: Update) -> str:
    user = update.effective_user
    if user.username:
        return f"@{user.username}"
    return user.first_name or "أخي الكريم"


def _main_keyboard(lang: str) -> ReplyKeyboardMarkup:
    rows = MSG[lang]["main_menu"]
    return ReplyKeyboardMarkup(
        [[KeyboardButton(btn) for btn in row] for row in rows],
        resize_keyboard=True,
    )


def _language_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🇸🇦 عربي", callback_data="lang_ar"),
            InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"),
        ]
    ])


def _location_keyboard(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[KeyboardButton(MSG[lang]["location_button"], request_location=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


async def _send_chunked(bot, chat_id: int, header: str, items: list, lang: str):
    """Send all adhkar items as consecutive messages, keeping each item intact."""
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


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    await upsert_user(
        user.id,
        username=user.username or "",
        first_name=user.first_name or "",
    )

    # Always ask for language first on every /start
    await update.message.reply_text(
        MSG["ar"]["choose_language"],
        reply_markup=_language_keyboard(),
    )


async def cb_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles language selection in both initial setup and /language change."""
    query = update.callback_query
    await query.answer()
    lang = "ar" if query.data == "lang_ar" else "en"
    user_id = query.from_user.id

    await upsert_user(user_id, language=lang)
    context.user_data["lang"] = lang

    db_user = await get_user(user_id)
    has_location = db_user and db_user.get("lat") is not None

    if has_location:
        # Language changed but location already known — just confirm and refresh
        await query.edit_message_text(
            MSG[lang]["language_changed"],
            parse_mode=ParseMode.HTML,
        )
        if lang == "ar":
            city_disp = db_user.get("city_ar") or db_user.get("city", "")
        else:
            city_disp = db_user.get("city", "")
        await context.bot.send_message(
            chat_id=user_id,
            text=MSG[lang]["welcome"].format(
                name=f"@{query.from_user.username}" if query.from_user.username else query.from_user.first_name,
                city=_escape(city_disp),
            ),
            parse_mode=ParseMode.HTML,
            reply_markup=_main_keyboard(lang),
        )
        await schedule_user(db_user)
    else:
        # Need to collect location
        await query.edit_message_text(
            MSG[lang]["share_location"],
            parse_mode=ParseMode.HTML,
        )
        await context.bot.send_message(
            chat_id=user_id,
            text="👇",
            reply_markup=_location_keyboard(lang),
        )


async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    loc = update.message.location
    if not loc:
        return

    db_user = await get_user(user.id)
    lang = db_user.get("language", "ar") if db_user else "ar"

    await update.message.reply_text(
        MSG[lang]["locating"],
        reply_markup=ReplyKeyboardRemove(),
    )

    lat, lon = loc.latitude, loc.longitude
    loc_names = await get_location_names(lat, lon)
    city_en = loc_names.get("en", "Unknown")
    city_ar = loc_names.get("ar", "Unknown")
    tz_name = await get_timezone(lat, lon) or "UTC"

    await upsert_user(
        user.id,
        lat=lat,
        lon=lon,
        city=city_en,
        city_ar=city_ar,
        timezone=tz_name,
        active=1,
    )

    city_display = city_ar if lang == "ar" else city_en
    name = _display_name(update)
    welcome = MSG[lang]["welcome"].format(
        name=_escape(name),
        city=_escape(city_display),
    )
    await update.message.reply_text(
        welcome,
        parse_mode=ParseMode.HTML,
        reply_markup=_main_keyboard(lang),
    )

    full_user = await get_user(user.id)
    await schedule_user(full_user)


async def cmd_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Allow user to update their location at any time."""
    user_id = update.effective_user.id
    db_user = await get_user(user_id)
    lang = db_user.get("language", "ar") if db_user else "ar"

    await update.message.reply_text(
        MSG[lang]["update_location"],
        parse_mode=ParseMode.HTML,
        reply_markup=_location_keyboard(lang),
    )


async def cmd_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        MSG["ar"]["choose_language"],
        reply_markup=_language_keyboard(),
    )


async def cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db_user = await get_user(user_id)
    lang = db_user.get("language", "ar") if db_user else "ar"
    await set_user_active(user_id, False)
    remove_user_jobs(user_id)
    await update.message.reply_text(MSG[lang]["notifications_stopped"], parse_mode=ParseMode.HTML)


async def cmd_resume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db_user = await get_user(user_id)
    lang = db_user.get("language", "ar") if db_user else "ar"
    if not db_user or not db_user.get("lat"):
        await update.message.reply_text(MSG[lang]["no_location"], parse_mode=ParseMode.HTML)
        return
    await set_user_active(user_id, True)
    await schedule_user(db_user)
    await update.message.reply_text(MSG[lang]["notifications_resumed"], parse_mode=ParseMode.HTML)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db_user = await get_user(update.effective_user.id)
    lang = db_user.get("language", "ar") if db_user else "ar"
    await update.message.reply_text(MSG[lang]["help_text"], parse_mode=ParseMode.HTML)


async def cmd_about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db_user = await get_user(update.effective_user.id)
    lang = db_user.get("language", "ar") if db_user else "ar"
    gist_url = await get_gist_url()
    gist_line = (
        f'\n🗂 <b>قاعدة بيانات المحتوى (Gist):</b>\n<a href="{gist_url}">تعديل الأذكار والأدعية</a>'
        if lang == "ar"
        else f'\n🗂 <b>Content Database (Gist):</b>\n<a href="{gist_url}">Edit adhkar & duas</a>'
    ) if gist_url and gist_url.startswith("http") else ""
    await update.message.reply_text(
        MSG[lang]["about_text"] + gist_line,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin-only: show bot usage statistics."""
    admin_id = int(os.environ.get("ADMIN_ID", "0"))
    requester_id = update.effective_user.id

    # If ADMIN_ID is set, restrict access
    if admin_id and requester_id != admin_id:
        await update.message.reply_text("⛔ هذا الأمر للمشرف فقط.")
        return

    from scheduler import scheduler

    users = await get_all_users_stats()
    total = len(users)
    active = sum(1 for u in users if u.get("active"))
    inactive = total - active
    jobs = len(scheduler.get_jobs())

    lines = [
        "📊 <b>إحصائيات البوت</b>",
        f"◈══════════════◈",
        f"👥 إجمالي المستخدمين: <b>{total}</b>",
        f"✅ نشطون: <b>{active}</b>",
        f"⏸ موقوفون: <b>{inactive}</b>",
        f"⏰ مهام مجدولة: <b>{jobs}</b>",
        f"◈══════════════◈",
        "",
    ]

    for u in users:
        status_icon = "🟢" if u.get("active") else "🔴"
        name = u.get("username") and f"@{u['username']}" or u.get("first_name") or str(u["user_id"])
        lang = "🇸🇦" if u.get("language") == "ar" else "🇬🇧"
        city = u.get("city_ar") if u.get("language") == "ar" else u.get("city")
        city = city or "—"
        tz = u.get("timezone") or "—"
        joined = (u.get("created_at") or "")[:10]
        lines.append(
            f"{status_icon} {lang} <b>{_escape(name)}</b>\n"
            f"   📍 {_escape(city)} | 🕐 {tz}\n"
            f"   📅 انضم: {joined}"
        )
        lines.append("")

    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


async def cmd_test_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db_user = await get_user(user_id)
    if not db_user or not db_user.get("lat"):
        lang = "ar"
        await update.message.reply_text(MSG[lang]["no_location"], parse_mode=ParseMode.HTML)
        return

    lang = db_user.get("language", "ar")
    if lang == "ar":
        city = db_user.get("city_ar") or db_user.get("city", "Unknown")
    else:
        city = db_user.get("city", "Unknown")
    lat = db_user["lat"]
    lon = db_user["lon"]

    await update.message.reply_text(
        MSG[lang]["test_header"], parse_mode=ParseMode.HTML
    )

    # 1. Quran passage
    verse = await fetch_random_quran_verse()
    if verse:
        header = MSG[lang]["verse_header"]
        body = MSG[lang]["verse_body"].format(
            text=_escape(verse["text"]),
            surah=_escape(verse["surah"]),
            ayah=verse["ayah"],
        )
        await update.message.reply_text("1️⃣ " + header + body, parse_mode=ParseMode.HTML)

    # 2. Morning adhkar — all items
    morning_items = await fetch_morning_adhkar()
    if morning_items:
        header = MSG[lang]["adhkar_morning_header"]
        await _send_chunked(context.bot, user_id, "2️⃣ " + header, morning_items, lang)

    # 3. Random dua
    duas = await fetch_post_prayer_duas()
    dua = random.choice(duas) if duas else None
    if dua:
        header = MSG[lang]["dua_header"]
        body = MSG[lang]["adhkar_body"].format(
            content=_escape(dua.get("content", "")),
            description=_escape(dua.get("description", "")),
            count=dua.get("count", 1),
        )
        await update.message.reply_text("3️⃣ " + header + body, parse_mode=ParseMode.HTML)

    # 4. Adhan template (audio + text)
    timings = await get_prayer_times(lat, lon)
    if timings:
        prayer_key = "Maghrib"
        idx = PRAYER_ORDER.index(prayer_key)
        next_key = PRAYER_ORDER[(idx + 1) % len(PRAYER_ORDER)]
        dua_text = _escape(dua.get("content", "…")) if dua else "…"
        raw_next = timings.get(next_key, "—")
        fmt_next = format_time_12h(raw_next, lang) if raw_next != "—" else "—"
        await send_adhan_audio(context.bot, update.effective_chat.id, prayer_key)
        adhan_msg = MSG[lang]["adhan_call"].format(
            prayer=PRAYER_NAMES[lang].get(prayer_key, prayer_key),
            city=_escape(city),
            next_prayer=PRAYER_NAMES[lang].get(next_key, next_key),
            next_time=fmt_next,
            dua=dua_text,
        )
        await update.message.reply_text("4️⃣ " + adhan_msg, parse_mode=ParseMode.HTML)


# All menu button labels across both languages flattened
_ALL_LABELS: dict[str, tuple[str, str]] = {}


def _build_label_map():
    for lang in ["ar", "en"]:
        menu = MSG[lang]["main_menu"]
        _ALL_LABELS[menu[0][0]] = ("prayer", lang)
        _ALL_LABELS[menu[0][1]] = ("dua", lang)
        _ALL_LABELS[menu[1][0]] = ("adhkar", lang)
        _ALL_LABELS[menu[1][1]] = ("verse", lang)
        _ALL_LABELS[menu[2][0]] = ("help", lang)


_build_label_map()


async def handle_menu_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    db_user = await get_user(user_id)
    lang = db_user.get("language", "ar") if db_user else "ar"

    action_info = _ALL_LABELS.get(text)
    if not action_info:
        return

    action, _ = action_info

    if action == "prayer":
        await _show_prayer_times(update, db_user, lang)
    elif action == "dua":
        await _show_dua(update, user_id, lang)
    elif action == "adhkar":
        await _show_adhkar(update, context, user_id, lang)
    elif action == "verse":
        await _show_verse(update, lang)
    elif action == "help":
        await cmd_help(update, context)


async def _show_prayer_times(update: Update, db_user: dict, lang: str):
    if not db_user or not db_user.get("lat"):
        await update.message.reply_text(MSG[lang]["no_location"], parse_mode=ParseMode.HTML)
        return
    timings = await get_prayer_times(db_user["lat"], db_user["lon"])
    if not timings:
        await update.message.reply_text(MSG[lang]["content_unavailable"], parse_mode=ParseMode.HTML)
        return
    if lang == "ar":
        city = db_user.get("city_ar") or db_user.get("city", "Unknown")
    else:
        city = db_user.get("city", "Unknown")
    header = MSG[lang]["prayer_times_header"].format(city=_escape(city))
    rows = ""
    for key in PRAYER_ORDER:
        name = PRAYER_NAMES[lang].get(key, key)
        raw_time = timings.get(key, "—")
        time_val = format_time_12h(raw_time, lang) if raw_time != "—" else "—"
        rows += MSG[lang]["prayer_times_row"].format(name=name, time=time_val)
    await update.message.reply_text(header + rows, parse_mode=ParseMode.HTML)


async def _show_dua(update: Update, user_id: int, lang: str):
    duas = await fetch_post_prayer_duas()
    item = random.choice(duas) if duas else None
    if not item:
        await update.message.reply_text(MSG[lang]["content_unavailable"], parse_mode=ParseMode.HTML)
        return
    header = MSG[lang]["dua_header"]
    body = MSG[lang]["adhkar_body"].format(
        content=_escape(item.get("content", "")),
        description=_escape(item.get("description", "")),
        count=item.get("count", 1),
    )
    await update.message.reply_text(header + body, parse_mode=ParseMode.HTML)


async def _show_adhkar(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, lang: str):
    """Show ALL morning adhkar as one complete collection."""
    items = await fetch_morning_adhkar()
    if not items:
        await update.message.reply_text(MSG[lang]["content_unavailable"], parse_mode=ParseMode.HTML)
        return
    header = MSG[lang]["adhkar_morning_header"]
    await _send_chunked(context.bot, user_id, header, items, lang)


async def _show_verse(update: Update, lang: str):
    verse = await fetch_random_quran_verse()
    if not verse:
        await update.message.reply_text(MSG[lang]["content_unavailable"], parse_mode=ParseMode.HTML)
        return
    header = MSG[lang]["verse_header"]
    body = MSG[lang]["verse_body"].format(
        text=_escape(verse["text"]),
        surah=_escape(verse["surah"]),
        ayah=verse["ayah"],
    )
    await update.message.reply_text(header + body, parse_mode=ParseMode.HTML)
