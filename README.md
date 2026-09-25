# ארכיון Omnissa ו־Omnissa Guardian

עותק **מקומי** לתיעוד ולמאמרי KB של Omnissa, לשימוש באתרים מנותקים.  
**זה לא אתר מראה ציבורי.** התוכן שייך ל־Omnissa.

## התחלה מהירה

| פעולה | איך |
|---|---|
| לפתוח את הארכיון | `Open-Archive.bat` → http://127.0.0.1:8765/ (דפדפן מקומי) |
| לפתוח את Guardian | `Open-Guardian.bat` → **חלון שולחני** (או `dist\OmnissaGuardian\OmnissaGuardian.exe`) |
| שפת Guardian | כפתורי עברית / English בחלון |
| להוריד / להמשיך הורדה | `Open-Download.bat` (ממשיך מהתור אם נעצר באמצע) |

מדריך מפורט ללקוח: [`docs/מדריך-ללקוח.md`](docs/מדריך-ללקוח.md)

## מה כל תוכנה עושה

- **ארכיון** — חיפוש, סינון לפי מוצר/גרסה/תאריך, וקריאת מסמכים אופליין (ממשק ווב מקומי).
- **Guardian** — חלון שולחני כהה לניטור לוגים מקומיים/UNC, התראות, והצעת מאמר מהארכיון. שפה: עברית או אנגלית.

## איפה הנתונים

- `data/archive.sqlite` — מסד ההורדה
- `data/assets/` — תמונות וקבצים
- `data/library/inbox/` — שמים כאן SQLite חדש; הקורא טוען אוטומטית
- `data/guardian_config.json` — הגדרות Guardian כולל שפה
- `dist/OmnissaGuardian/OmnissaGuardian.exe` — EXE של Guardian (אם נבנה)
- `dist/Omnissa-Archive/` — חבילה להפצה ללקוח

## הורדה שממשיכה אחרי עצירה

```powershell
.\.venv\Scripts\python -m omnissa_archive fetch
```

או `Open-Download.bat`. עמודים שכבר ירדו מסומנים כ־`done` ולא יורדים מחדש. עמוד שנקטע באמצע חוזר לתור בהרצה הבאה.

## התקנה (פעם אחת)

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[dev]"
.\.venv\Scripts\python -m playwright install chromium
```

## פקודות נוספות לצוות ההפצה

```powershell
.\.venv\Scripts\python -m omnissa_archive discover
.\.venv\Scripts\python -m omnissa_archive refresh
.\.venv\Scripts\python -m omnissa_archive guardian
.\.venv\Scripts\python -m omnissa_archive package --output dist
.\.venv\Scripts\python -m omnissa_archive search "Horizon logs"
```
