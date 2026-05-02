"""
Adhan audio management.

Downloads MP3 audio from islamcan.com once per session and caches
the Telegram file_id so subsequent sends never re-upload.
Each of the 5 prayers has a distinct audio clip.
Fajr uses azan1 which typically carries 'الصلاة خير من النوم'.
"""

import logging
import httpx

logger = logging.getLogger(__name__)

# Each prayer → its own adhan clip (public MP3s from islamcan.com)
ADHAN_URLS: dict[str, str] = {
    "Fajr":    "https://islamcan.com/audio/adhan/azan1.mp3",
    "Dhuhr":   "https://islamcan.com/audio/adhan/azan3.mp3",
    "Asr":     "https://islamcan.com/audio/adhan/azan5.mp3",
    "Maghrib": "https://islamcan.com/audio/adhan/azan2.mp3",
    "Isha":    "https://islamcan.com/audio/adhan/azan7.mp3",
}

# In-memory file_id cache: {prayer_key: telegram_file_id}
_file_id_cache: dict[str, str] = {}


async def send_adhan_audio(bot, chat_id: int, prayer_key: str) -> bool:
    """
    Send the adhan audio for the given prayer to chat_id.
    Uses a cached Telegram file_id if available; otherwise downloads
    the MP3 and sends it, then caches the file_id for future sends.
    Returns True on success, False on any failure.
    """
    url = ADHAN_URLS.get(prayer_key)
    if not url:
        return False

    try:
        # Use cached file_id if we've already sent this prayer's audio before
        if prayer_key in _file_id_cache:
            msg = await bot.send_audio(
                chat_id=chat_id,
                audio=_file_id_cache[prayer_key],
            )
            return True

        # First time: download and upload
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as c:
            r = await c.get(url, headers={"User-Agent": "IslamicTelegramBot/1.0"})
            r.raise_for_status()
            audio_bytes = r.content

        msg = await bot.send_audio(
            chat_id=chat_id,
            audio=audio_bytes,
        )
        # Cache the file_id returned by Telegram
        if msg.audio:
            _file_id_cache[prayer_key] = msg.audio.file_id
            logger.info(
                f"Adhan audio for {prayer_key} uploaded & cached "
                f"(file_id={msg.audio.file_id[:20]}…)"
            )
        return True

    except Exception as e:
        logger.warning(f"Could not send adhan audio for {prayer_key}: {e}")
        return False
