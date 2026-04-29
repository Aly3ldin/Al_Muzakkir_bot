# Muzakkir Bot

بوت تليجرام إسلامي async بلغة Python يعتمد على البيانات الخارجية، التدوير داخل SQLite، وجدولة التنبيهات حسب الموقع.

## الميزات

- `/start` لاختيار اللغة ثم طلب الموقع.
- `/language` لتغيير اللغة في أي وقت.
- `/help` شرح الأزرار والإعدادات.
- `/stop` لإيقاف التنبيهات التلقائية.
- `/resume` لإعادة جدولة التنبيهات تلقائيًا.
- `/about` لعرض مصادر البيانات.
- `/test_all` لإرسال 4 رسائل اختبارية.

## المصادر

- الأذكار والأدعية: `https://raw.githubusercontent.com/nawafalqari/ayah/main/src/data/adkar.json`
- الآيات: `https://api.alquran.cloud/v1/ayah/random/ar.alafasy`
- مواقيت الصلاة: Aladhan API

## الإعداد

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
```

اضبط `BOT_TOKEN` ثم شغّل:

```bash
muzakkir-bot
```

## ملاحظات

- يحتاج المستخدم مشاركة الموقع حتى تعمل التنبيهات التلقائية.
- عند `/stop` يتم حذف مهام الجدولة الخاصة بالمستخدم من APScheduler.
- عند `/resume` تتم إعادة الجدولة من الموقع المخزن في SQLite.
