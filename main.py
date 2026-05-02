import os
import sys
import logging

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

sys.path.insert(0, os.path.dirname(__file__))

from db import init_db
from gist_db import ensure_gist, get_gist_url
from scheduler import scheduler, set_app, schedule_all_users
from handlers import (
    cmd_start,
    cmd_language,
    cmd_location,
    cmd_stats,
    cb_language,
    handle_location,
    cmd_stop,
    cmd_resume,
    cmd_help,
    cmd_about,
    cmd_test_all,
    handle_menu_button,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


async def post_init(application):
    await init_db()

    # Create or re-use the GitHub Gist content database
    gist_id = await ensure_gist()
    if gist_id:
        url = await get_gist_url()
        logger.info(f"Content Gist ready: {url}")
    else:
        logger.warning("Gist not available — using built-in adhkar data.")

    set_app(application)
    scheduler.start()
    scheduler.add_job(
        schedule_all_users,
        "cron",
        hour=0,
        minute=5,
        id="daily_prayer_refresh",
        replace_existing=True,
    )
    await schedule_all_users()
    logger.info("Bot initialized and scheduler started.")


async def post_shutdown(application):
    if scheduler.running:
        scheduler.shutdown(wait=False)
    logger.info("Scheduler stopped.")


def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not set!")
        sys.exit(1)

    app = (
        ApplicationBuilder()
        .token(token)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("location", cmd_location))
    app.add_handler(CommandHandler("language", cmd_language))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("stop", cmd_stop))
    app.add_handler(CommandHandler("resume", cmd_resume))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("about", cmd_about))
    app.add_handler(CommandHandler("test_all", cmd_test_all))

    app.add_handler(CallbackQueryHandler(cb_language, pattern="^lang_(ar|en)$"))
    app.add_handler(MessageHandler(filters.LOCATION, handle_location))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu_button))

    logger.info("Starting Islamic Bot (polling)...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
