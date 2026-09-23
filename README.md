# ארכיון מקומי לתיעוד Omnissa

סורק שאוסף את התיעוד הציבורי באנגלית מ-`docs.omnissa.com` ואת מאמרי `kb.omnissa.com` אל קובץ SQLite אחד ותיקיית מדיה. את התיקייה `data/` מעתיקים כמו שהיא אל הרשת המנותקת.

התוכן שייך ל-Omnissa. זה עותק פנימי, לא אתר מראה ציבורי. הסורק לא נכנס ל-`/api/`, ל-`/search`, או ל-`/articles/`.

## התקנה

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[dev]"
.\.venv\Scripts\python -m playwright install chromium
```

Akamai מחזיר 403 ל-User-Agent של בוט, לכן הבקשות יוצאות עם מזהה של Chrome רגיל. הקצב מוגבל לכ-3 בקשות בשנייה לתיעוד, ומאמרי ה-KB נטענים אחד-אחד עם השהיה.

## קריאה וחיפוש

ההורדה שומרת את גוף כל עמוד כ-HTML בתוך המסד. כדי לקרוא אותו בדפדפן:

```powershell
.\.venv\Scripts\python -m omnissa_archive serve
```

נפתח `http://127.0.0.1:8765/`. אפשר לחפש כל מילה, לפתוח את העמוד, ולראות תמונות שירדו איתו. קישור למסמך שכבר בארכיון נפתח מקומית. קישור למסמך שעוד לא ירד מודיע על כך.

אפשר גם ללחוץ פעמיים על `Open-Archive.bat`.

## פקודות

```powershell
.\.venv\Scripts\python -m omnissa_archive discover
.\.venv\Scripts\python -m omnissa_archive pilot
.\.venv\Scripts\python -m omnissa_archive fetch
.\.venv\Scripts\python -m omnissa_archive search "Horizon logs"
```

`pilot` ממלא את התור מכל ה-sitemap, ואז מוריד 20 עמודי תיעוד ו-20 מאמרי KB ובודק כותרת, גוף, טבלה, קישור פנימי ותמונה או PDF.

`fetch` בלי `--limit` ממשיך את כל מה שנשאר בתור. זו ריצה של כמה שעות לתיעוד וכמה שעות ל-KB. אפשר לעצור ולהמשיך; מה שכבר נשמר לא יורד מחדש אם התוכן לא השתנה.

```powershell
.\.venv\Scripts\python -m omnissa_archive fetch --source docs --limit 100
.\.venv\Scripts\python -m omnissa_archive fetch --source kb
```

## מה נשמר

- `data/archive.sqlite`
  - `documents` — מקור, כתובת, שפה, כותרת, מדריך, HTML, טקסט, hash, זמן, סטטוס
  - `documents_fts` — חיפוש על כותרת וטקסט
  - `assets` — כתובת מקורית, נתיב מקומי, sha256, סוג קובץ
  - `links` — קישורים מתוך גוף העמוד, כולל כתובות `/bundle/...`
  - `crawl_queue` — מצב ההורדה, כדי להמשיך אחרי עצירה
- `data/assets/` — תמונות ו-PDF. ב-HTML השמור `src` מצביע לקובץ המקומי, ו-`data-original-src` שומר את הכתובת המקורית.
