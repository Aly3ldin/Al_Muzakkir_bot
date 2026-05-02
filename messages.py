PRAYER_NAMES = {
    "ar": {
        "Fajr": "الفجر",
        "Sunrise": "الشروق",
        "Dhuhr": "الظهر",
        "Asr": "العصر",
        "Maghrib": "المغرب",
        "Isha": "العشاء",
    },
    "en": {
        "Fajr": "Fajr",
        "Sunrise": "Sunrise",
        "Dhuhr": "Dhuhr",
        "Asr": "Asr",
        "Maghrib": "Maghrib",
        "Isha": "Isha",
    },
}

PRAYER_ORDER = ["Fajr", "Dhuhr", "Asr", "Maghrib", "Isha"]

MSG = {
    "ar": {
        "choose_language": (
            "السلام عليكم 🌙\nمرحباً بك! اختر لغتك المفضلة:\n\n"
            "Hello! Choose your preferred language:"
        ),
        "share_location": (
            "📍 <b>مشاركة الموقع</b>\n\n"
            "الرجاء مشاركة موقعك حتى يتمكن البوت من:\n"
            "• ضبط أوقات الصلاة بدقة 🕌\n"
            "• إرسال الأذكار في أوقاتها الصحيحة 📿\n\n"
            "اضغط الزر أدناه لمشاركة موقعك 👇"
        ),
        "update_location": (
            "📍 <b>تحديث الموقع</b>\n\n"
            "اضغط الزر أدناه لمشاركة موقعك الجديد وسيتم تحديث أوقات الصلاة تلقائياً 👇"
        ),
        "location_button": "📍 مشاركة الموقع / Share Location",
        "locating": "⏳ جارٍ التعرف على موقعك...",
        "welcome": (
            "السلام عليكم ورحمة الله وبركاته يا <b>{name}</b> 🌙\n\n"
            "تم بنجاح التعرف على موقعك وضبط الإعدادات لـ: 📍 <b>{city}</b>\n\n"
            "البوت الآن مفعل بالكامل لخدمتك:\n"
            "🕌 <b>مواقيت الصلاة:</b> دقيقة تماماً حسب توقيت منطقتك.\n"
            "📿 <b>الأذكار التلقائية:</b> أذكار الصباح كاملة (8:00 ص) والمساء كاملة (8:00 م).\n"
            "🤲 <b>الدعاء المتجدد:</b> سأرسل لك دعاءً مختلفاً بعد كل أذان.\n"
            "📖 <b>الورد اليومي:</b> مقطع قرآني مختار يصلك كل يوم.\n\n"
            "استخدم القائمة أدناه للوصول إلى الخدمات 👇"
        ),
        "main_menu": [
            ["🕌 أوقات الصلاة", "🤲 الأدعية"],
            ["📿 الأذكار", "📖 آية قرآنية"],
            ["❓ المساعدة"],
        ],
        "prayer_times_header": "🕌 <b>أوقات الصلاة اليوم</b>\n📍 <b>{city}</b>\n\n",
        "prayer_times_row": "▪️ <b>{name}:</b> {time}\n",
        "adhkar_morning_header": (
            "☀️ <b>أذكار الصباح</b>\n"
            "◈══════════════◈\n\n"
        ),
        "adhkar_evening_header": (
            "🌙 <b>أذكار المساء</b>\n"
            "◈══════════════◈\n\n"
        ),
        "adhkar_item": (
            "{num}. {content}\n\n"
            "📌 <i>{description}</i>\n"
            "🔁 التكرار: <b>{count}</b> مرة\n"
            "◈──────────────◈\n\n"
        ),
        "adhkar_body": (
            "{content}\n\n"
            "📌 <i>{description}</i>\n"
            "🔁 التكرار: <b>{count}</b> مرة"
        ),
        "adhan_call": (
            "✨ ⟦ نِداءُ الصَّلاة | Adhan Call ⟧ ✨\n\n"
            "🕋 حان الآن وقت أذان <b>{prayer}</b>\n"
            "📍 حسب التوقيت المحلي لـ: <b>{city}</b>\n\n"
            "◈──────────◈\n"
            "⬅️ الاذان التالي: <b>{next_prayer}</b> ({next_time})\n"
            "◈──────────◈\n\n"
            "⚠️ لا تنسى أذكار ما بعد الصلاة:\n"
            "📿 {dua}"
        ),
        "dua_header": "🤲 <b>دعاء</b>\n◈──────────────◈\n\n",
        "verse_header": (
            "📖 <b>مقطع قرآني</b>\n"
            "◈──────────────◈\n\n"
        ),
        "verse_body": (
            "{text}\n\n"
            "📌 سورة <b>{surah}</b> — الآيات <b>{ayah}</b>"
        ),
        "notifications_stopped": "⏸ تم إيقاف جميع الإشعارات. اكتب /resume لتفعيلها مجدداً.",
        "notifications_resumed": "▶️ تم تفعيل الإشعارات مجدداً. سيصلك الأذان والأذكار في مواعيدها.",
        "help_text": (
            "📋 <b>دليل الاستخدام</b>\n\n"
            "🔹 /start — إعادة الإعداد واختيار اللغة والموقع\n"
            "🔹 /location — تغيير الموقع الجغرافي\n"
            "🔹 /language — تغيير لغة الواجهة\n"
            "🔹 /stop — إيقاف جميع الإشعارات المجدولة\n"
            "🔹 /resume — إعادة تفعيل الإشعارات\n"
            "🔹 /test_all — اختبار جميع أنواع الرسائل\n"
            "🔹 /about — معلومات عن البوت ومصادر البيانات\n\n"
            "📲 <b>القائمة الرئيسية:</b>\n"
            "• 🕌 أوقات الصلاة — عرض مواقيت اليوم\n"
            "• 🤲 الأدعية — دعاء من المكتبة\n"
            "• 📿 الأذكار — أذكار الصباح كاملة\n"
            "• 📖 آية قرآنية — مقطع قرآني عشوائي\n"
        ),
        "about_text": (
            "ℹ️ <b>عن البوت</b>\n\n"
            "🤖 بوت إسلامي شامل للأذان والأذكار والقرآن الكريم\n\n"
            "📡 <b>مصادر البيانات:</b>\n"
            "• مواقيت الصلاة: aladhan.com\n"
            "• الأذكار والأدعية: Azkar API (nawafalqari)\n"
            "• القرآن الكريم: quran.com\n"
            "• الجغرافيا: OpenStreetMap Nominatim\n\n"
            "🛠 مبني بـ python-telegram-bot v21"
        ),
        "language_changed": "✅ تم تغيير اللغة إلى العربية.",
        "no_location": "❗ الرجاء مشاركة موقعك أولاً باستخدام /start أو /location",
        "content_unavailable": "⚠️ المحتوى غير متاح حالياً، يرجى المحاولة لاحقاً.",
        "test_header": "🧪 <b>اختبار جميع الرسائل</b>\nسيتم إرسال رسائل اختبارية...\n\n",
    },
    "en": {
        "choose_language": (
            "Assalamu Alaikum 🌙\nWelcome! Choose your preferred language:\n\n"
            "مرحباً! اختر لغتك المفضلة:"
        ),
        "share_location": (
            "📍 <b>Share Your Location</b>\n\n"
            "Please share your location so the bot can:\n"
            "• Set accurate prayer times 🕌\n"
            "• Send adhkar at the right times 📿\n\n"
            "Tap the button below to share your location 👇"
        ),
        "update_location": (
            "📍 <b>Update Location</b>\n\n"
            "Tap the button below to share your new location. Prayer times will be updated automatically 👇"
        ),
        "location_button": "📍 مشاركة الموقع / Share Location",
        "locating": "⏳ Identifying your location...",
        "welcome": (
            "Assalamu Alaikum <b>{name}</b> 🌙\n\n"
            "Location set successfully for: 📍 <b>{city}</b>\n\n"
            "The bot is now fully active:\n"
            "🕌 <b>Prayer Times:</b> Accurate based on your region.\n"
            "📿 <b>Auto Adhkar:</b> Full Morning adhkar (8:00 AM) & Full Evening adhkar (8:00 PM).\n"
            "🤲 <b>Rotating Duas:</b> A unique dua after every Adhan.\n"
            "📖 <b>Daily Verses:</b> Selected Quranic passages sent periodically.\n\n"
            "Use the menu below to access features 👇"
        ),
        "main_menu": [
            ["🕌 Prayer Times", "🤲 Duas"],
            ["📿 Adhkar", "📖 Quran Verse"],
            ["❓ Help"],
        ],
        "prayer_times_header": "🕌 <b>Today's Prayer Times</b>\n📍 <b>{city}</b>\n\n",
        "prayer_times_row": "▪️ <b>{name}:</b> {time}\n",
        "adhkar_morning_header": (
            "☀️ <b>Morning Adhkar</b>\n"
            "◈══════════════◈\n\n"
        ),
        "adhkar_evening_header": (
            "🌙 <b>Evening Adhkar</b>\n"
            "◈══════════════◈\n\n"
        ),
        "adhkar_item": (
            "{num}. {content}\n\n"
            "📌 <i>{description}</i>\n"
            "🔁 Count: <b>{count}</b>\n"
            "◈──────────────◈\n\n"
        ),
        "adhkar_body": (
            "{content}\n\n"
            "📌 <i>{description}</i>\n"
            "🔁 Count: <b>{count}</b>"
        ),
        "adhan_call": (
            "✨ ⟦ نِداءُ الصَّلاة | Adhan Call ⟧ ✨\n\n"
            "🕋 It's now time for <b>{prayer}</b> prayer\n"
            "📍 Local time for: <b>{city}</b>\n\n"
            "◈──────────◈\n"
            "⬅️ Next prayer: <b>{next_prayer}</b> ({next_time})\n"
            "◈──────────◈\n\n"
            "⚠️ Don't forget post-prayer dhikr:\n"
            "📿 {dua}"
        ),
        "dua_header": "🤲 <b>Du'a</b>\n◈──────────────◈\n\n",
        "verse_header": (
            "📖 <b>Quranic Passage</b>\n"
            "◈──────────────◈\n\n"
        ),
        "verse_body": (
            "{text}\n\n"
            "📌 Surah <b>{surah}</b> — Verses <b>{ayah}</b>"
        ),
        "notifications_stopped": "⏸ All notifications paused. Type /resume to re-enable.",
        "notifications_resumed": "▶️ Notifications re-enabled. You'll receive Adhan & Adhkar on schedule.",
        "help_text": (
            "📋 <b>How to Use</b>\n\n"
            "🔹 /start — Setup: language & location\n"
            "🔹 /location — Change your location\n"
            "🔹 /language — Change UI language\n"
            "🔹 /stop — Pause all scheduled notifications\n"
            "🔹 /resume — Re-enable notifications\n"
            "🔹 /test_all — Test all message types\n"
            "🔹 /about — About this bot & data credits\n\n"
            "📲 <b>Main Menu:</b>\n"
            "• 🕌 Prayer Times — View today's schedule\n"
            "• 🤲 Duas — A dua from the library\n"
            "• 📿 Adhkar — Full morning adhkar collection\n"
            "• 📖 Quran Verse — Random Quranic passage\n"
        ),
        "about_text": (
            "ℹ️ <b>About This Bot</b>\n\n"
            "🤖 A comprehensive Islamic bot for Adhan, Adhkar & Quran\n\n"
            "📡 <b>Data Sources:</b>\n"
            "• Prayer Times: aladhan.com\n"
            "• Adhkar & Duas: Azkar API (nawafalqari)\n"
            "• Quran: quran.com\n"
            "• Geocoding: OpenStreetMap Nominatim\n\n"
            "🛠 Built with python-telegram-bot v21"
        ),
        "language_changed": "✅ Language changed to English.",
        "no_location": "❗ Please share your location first using /start or /location",
        "content_unavailable": "⚠️ Content unavailable right now. Please try again later.",
        "test_header": "🧪 <b>Testing All Messages</b>\nSending test messages...\n\n",
    },
}
