"""
External API calls: prayer times, Quran verses, geocoding.
Adhkar content is loaded from the Gist database (gist_db.py).
"""

import httpx
import logging
import random
from datetime import datetime, timedelta
from typing import Optional
from timezonefinder import TimezoneFinder

from db import cache_get, cache_set
import gist_db

logger = logging.getLogger(__name__)
_tf = TimezoneFinder()

NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"
QURAN_CHAPTER_URL = "https://api.quran.com/api/v4/chapters/{chapter_id}"
QURAN_BY_CHAPTER_URL = "https://api.quran.com/api/v4/verses/by_chapter/{chapter_id}"

# ── Quran verse counts per surah (1-114) — total 6236 verses ──────────────
# Source: standard Hafs 'an 'Asim rasm
_SURAH_SIZES = [
      7, 286, 200, 176, 120, 165, 206,  75, 129, 109,  # 1-10
    123, 111,  43,  52,  99, 128, 111, 110,  98, 135,  # 11-20
    112,  78, 118,  64,  77, 227,  93,  88,  69,  60,  # 21-30
     34,  30,  73,  54,  45,  83, 182,  88,  75,  85,  # 31-40
     54,  53,  89,  59,  37,  35,  38,  29,  18,  45,  # 41-50
     60,  49,  62,  55,  78,  96,  29,  22,  24,  13,  # 51-60
     14,  11,  11,  18,  12,  12,  30,  52,  52,  44,  # 61-70
     28,  28,  20,  56,  40,  31,  50,  40,  46,  42,  # 71-80
     29,  19,  36,  25,  22,  17,  19,  26,  30,  20,  # 81-90
     15,  21,  11,   8,   8,  19,   5,   8,   8,  11,  # 91-100
     11,   8,   3,   9,   5,   4,   7,   3,   6,   3,  # 101-110
      5,   4,   5,   6,                                  # 111-114
]
# Cumulative verse offsets — _SURAH_OFFSETS[i] = first verse number of surah i+1
_SURAH_OFFSETS: list[int] = []
_total = 0
for _s in _SURAH_SIZES:
    _SURAH_OFFSETS.append(_total)
    _total += _s
_TOTAL_VERSES = _total  # 6236


def _random_surah_ayah() -> tuple[int, int]:
    """Pick a uniformly random verse from the entire Quran (1-6236).
    Returns (chapter_id 1-114, verse_number 1-N)."""
    verse_idx = random.randint(0, _TOTAL_VERSES - 1)
    # Binary search for surah
    lo, hi = 0, len(_SURAH_OFFSETS) - 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if _SURAH_OFFSETS[mid] <= verse_idx:
            lo = mid
        else:
            hi = mid - 1
    surah = lo + 1                          # 1-indexed
    ayah  = verse_idx - _SURAH_OFFSETS[lo] + 1  # 1-indexed within surah
    return surah, ayah


def format_time_12h(time_str: str, lang: str = "ar") -> str:
    """Convert '14:30' → '2:30 م' (Arabic) or '2:30 PM' (English)."""
    try:
        h, m = map(int, time_str.split(":"))
        if lang == "ar":
            period = "ص" if h < 12 else "م"
        else:
            period = "AM" if h < 12 else "PM"
        h12 = h % 12 or 12
        return f"{h12}:{m:02d} {period}"
    except Exception:
        return time_str


# In-memory adhkar cache (refreshed hourly)
_adhkar_cache: dict[str, tuple[list, datetime]] = {}
_CACHE_TTL = timedelta(hours=1)


async def _get_adhkar_cached(key: str, loader) -> list:
    entry = _adhkar_cache.get(key)
    if entry:
        data, fetched_at = entry
        if datetime.utcnow() - fetched_at < _CACHE_TTL:
            return data
    data = await loader()
    _adhkar_cache[key] = (data, datetime.utcnow())
    return data


async def get_timezone(lat: float, lon: float) -> Optional[str]:
    return _tf.timezone_at(lng=lon, lat=lat)


async def get_location_names(lat: float, lon: float) -> dict:
    """Return {'ar': 'المنيا، مصر', 'en': 'Al Minya, Egypt'} using state/province + country."""
    result = {"ar": "Unknown", "en": "Unknown"}
    try:
        async with httpx.AsyncClient(timeout=12, follow_redirects=True) as c:
            for lang_code, key in [("ar", "ar"), ("en", "en")]:
                r = await c.get(
                    NOMINATIM_URL,
                    params={"lat": lat, "lon": lon, "format": "json",
                            "accept-language": lang_code},
                    headers={"User-Agent": "IslamicTelegramBot/1.0"},
                )
                r.raise_for_status()
                addr = r.json().get("address", {})
                # Use state/province level — NOT city/town/village/road
                state = addr.get("state") or addr.get("county") or addr.get("region") or ""
                country = addr.get("country") or ""
                if state and country:
                    sep = "، " if lang_code == "ar" else ", "
                    result[key] = f"{state}{sep}{country}"
                elif country:
                    result[key] = country
                elif state:
                    result[key] = state
    except Exception as e:
        logger.error(f"Geocoding error: {e}")
    return result


async def get_city_name(lat: float, lon: float) -> str:
    """Backward-compat: returns English 'State, Country'."""
    names = await get_location_names(lat, lon)
    return names.get("en", "Unknown")


async def get_prayer_times(lat: float, lon: float) -> Optional[dict]:
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as c:
            r = await c.get(
                "https://api.aladhan.com/v1/timings",
                params={"latitude": lat, "longitude": lon, "method": 4},
            )
            r.raise_for_status()
            timings = r.json()["data"]["timings"]
            return dict(timings)
    except Exception as e:
        logger.error(f"Prayer times error: {e}")
        return None


async def fetch_morning_adhkar() -> list:
    return await _get_adhkar_cached("morning", gist_db.load_morning_adhkar)


async def fetch_evening_adhkar() -> list:
    return await _get_adhkar_cached("evening", gist_db.load_evening_adhkar)


async def fetch_post_prayer_duas() -> list:
    return await _get_adhkar_cached("duas", gist_db.load_post_prayer_duas)


async def fetch_all_adhkar() -> list:
    """Return the complete unified adhkar collection (all categories)."""
    return await _get_adhkar_cached("all", gist_db.load_all_adhkar)


async def fetch_random_adhkar(count: int = 5) -> list:
    """Pick `count` random adhkar from the full collection (all categories)."""
    all_items = await fetch_all_adhkar()
    if not all_items:
        return []
    return random.sample(all_items, min(count, len(all_items)))


def _invalidate_adhkar_cache():
    _adhkar_cache.clear()


async def fetch_random_quran_passage() -> Optional[dict]:
    """
    Fetch 3-4 consecutive Quranic verses chosen with true uniform randomness
    across all 6236 verses of the Quran (beginnings, middles, and endings of surahs).
    Uses our own _random_surah_ayah() instead of any API random endpoint.
    """
    try:
        # ── Step 1: Pick a truly random verse from the entire Quran ──────────
        chapter_id, verse_start = _random_surah_ayah()
        total_verses = _SURAH_SIZES[chapter_id - 1]

        # Passage length 3-4 verses
        passage_len = random.randint(3, 4)

        # Clamp: if near end of surah, shift start backward
        if verse_start + passage_len - 1 > total_verses:
            verse_start = max(1, total_verses - passage_len + 1)

        verse_end = min(verse_start + passage_len - 1, total_verses)

        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as c:
            # ── Step 2: Fetch chapter name ─────────────────────────────────
            r_ch = await c.get(
                QURAN_CHAPTER_URL.format(chapter_id=chapter_id),
                params={"language": "ar"},
            )
            r_ch.raise_for_status()
            chapter = r_ch.json().get("chapter", {})

            # ── Step 3: Fetch the consecutive verses ──────────────────────
            r2 = await c.get(
                QURAN_BY_CHAPTER_URL.format(chapter_id=chapter_id),
                params={
                    "language": "ar",
                    "fields": "text_uthmani,verse_number",
                    "verse_start": verse_start,
                    "verse_end": verse_end,
                    "per_page": 10,
                },
            )
            r2.raise_for_status()
            verses = r2.json().get("verses", [])

        if not verses:
            logger.warning(f"Empty verses for surah {chapter_id}:{verse_start}-{verse_end}")
            return None

        # Hard cap: never show more than 4 verses
        verses = verses[:4]

        # ── Step 4: Format as continuous Mushaf text ──────────────────────
        parts = []
        for v in verses:
            text = v.get("text_uthmani", "").strip()
            num = v.get("verse_number", "")
            if text:
                parts.append(f"{text} ﴿{num}﴾")
        passage_text = " ".join(parts)

        actual_start = verses[0].get("verse_number", verse_start)
        actual_end   = verses[-1].get("verse_number", verse_end)
        ayah_label   = str(actual_start) if actual_start == actual_end else f"{actual_start} - {actual_end}"

        return {
            "text": passage_text,
            "surah": chapter.get("name_arabic", ""),
            "surah_en": chapter.get("name_simple", ""),
            "ayah": ayah_label,
            "surah_num": chapter_id,
        }

    except Exception as e:
        logger.error(f"Quran passage error: {e}")
        # ── Fallback: alquran.cloud with our own random index ────────────
        try:
            ch, ay = _random_surah_ayah()
            total = _SURAH_SIZES[ch - 1]
            end   = min(ay + 3, total)
            async with httpx.AsyncClient(timeout=12, follow_redirects=True) as c:
                r = await c.get(
                    f"https://api.alquran.cloud/v1/surah/{ch}/ar.uthmani",
                    params={"offset": ay - 1, "limit": end - ay + 1},
                )
                r.raise_for_status()
                data  = r.json()["data"]
                ayahs = data.get("ayahs", [])
            if not ayahs:
                return None
            parts = [f"{a['text']} ﴿{a['numberInSurah']}﴾" for a in ayahs]
            a0, a1 = ayahs[0]["numberInSurah"], ayahs[-1]["numberInSurah"]
            return {
                "text": " ".join(parts),
                "surah": data.get("name", ""),
                "surah_en": data.get("englishName", ""),
                "ayah": str(a0) if a0 == a1 else f"{a0} - {a1}",
                "surah_num": ch,
            }
        except Exception as e2:
            logger.error(f"Quran fallback also failed: {e2}")
            return None


# Keep old name as alias for backward compatibility
async def fetch_random_quran_verse() -> Optional[dict]:
    return await fetch_random_quran_passage()
