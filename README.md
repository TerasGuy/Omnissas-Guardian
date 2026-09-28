# ארכיון Omnissa ו־Omnissa Guardian

עותק **מקומי** לתיעוד ולמאמרי KB של Omnissa, לשימוש באתרים מנותקים.  
**זה לא אתר מראה ציבורי.** התוכן שייך ל־Omnissa.

מפרט מיושם: [`docs/superpowers/specs/2026-09-25-omnissa-archive-guardian-design.md`](docs/superpowers/specs/2026-09-25-omnissa-archive-guardian-design.md)  
מדריך ללקוח: [`docs/מדריך-ללקוח.md`](docs/מדריך-ללקוח.md)

## מה כל תוכנה עושה

- **ארכיון** — חיפוש, סינון לפי מוצר, משפחה, גרסה, קטגוריה ותאריך, וקריאת מסמכים אופליין. הטבלה כוללת מספר KB (למשל `1027744`). מסמכי תיעוד בלי מספר מוצגים עם מקף.
- **Guardian** — חלון שולחני לניטור לוגים. נתיב מקומי או UNC נסרק, שורות שגיאה מושוות למסד המקומי, ומוצג מאמר מתאים. בפתיחה Guardian גם מפעיל את שרת הארכיון על `http://127.0.0.1:8765/`. חיפוש במסמכים אונליין כבוי כברירת מחדל. הוא נפתח רק אחרי סימון בהגדרות, לחיצה על **חיפוש אונליין**, ורק אם יש רשת אל `kb.omnissa.com`.

קובצי `Open-*.bat` הם קיצורי דרך למחשב הפיתוח. ללקוח מפיצים את קובץ ההתקנה, לא BAT.

## מה נכנס ל־Git ומה מעתיקים בנפרד

Git שומר את הקוד, הבדיקות, האייקון, סקריפט ההתקנה והמסמכים.  
המסד, התמונות, סביבת Python ותוצרי הבנייה **לא** נכנסים ל־Git:

| נתיב | ב־Git? | בשביל מה |
|---|---|---|
| `src\`, `tests\`, `installer\`, `assets\omnissa-guardian.ico` | כן | הקוד והאייקון |
| `data\archive.sqlite` (+ `-wal` / `-shm` אם קיימים) | לא | המסד והתור. בלי זה ההורדה מתחילה מחדש |
| `data\assets\` | לא | תמונות המאמרים |
| `.venv\` | לא | נוצרת מחדש במחשב היעד |
| `dist\`, `build\` | לא | EXE, חבילת בדיקה וקובץ התקנה. נבנים מחדש |

## העברה למחשב אחר

1. עצרו את ההורדה (`fetch`) כדי שלא ייכתב למסד בזמן ההעתקה.
2. צמצמו את ה־WAL למסד אחד:

```powershell
.\.venv\Scripts\python -c "import sqlite3; c=sqlite3.connect(r'data/archive.sqlite'); c.execute('PRAGMA wal_checkpoint(TRUNCATE)'); c.close()"
```

3. העתיקו את כל תיקיית הפרויקט, ובמיוחד את `data\archive.sqlite` ואת `data\assets\`. אפשר דרך Git לקוד, והתיקייה `data\` בנפרד (היא ב־`.gitignore`).
4. במחשב החדש, מתוך שורש הפרויקט:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[dev]"
.\.venv\Scripts\python -m playwright install chromium
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python -m omnissa_archive fetch
```

נדרשים Python 3.11 ומעלה (הפיתוח רץ על 3.14) ו־Google Chrome לרינדור מאמרי KB.  
`fetch` ממשיך מהתור שבתוך המסד. כתובת במצב `done` לא יורדת שוב.  
סביבה וירטואלית שהועתקה ממחשב אחר לא רצה: יוצרים `.venv` חדש עם Python המקומי.

לבנות מחדש את התוכנה ואת קובץ ההתקנה צריך גם [Inno Setup 6](https://jrsoftware.org/isinfo.php):

```powershell
.\.venv\Scripts\python installer\stage_library.py
.\.venv\Scripts\pyinstaller build\pyinstaller\OmnissaGuardian.spec --noconfirm --distpath dist --workpath build\pyinstaller
& "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe" installer\OmnissaGuardian.iss
```

התוצאה: `dist\OmnissaGuardianSetup.exe`.

## פקודות

```powershell
.\.venv\Scripts\python -m omnissa_archive discover
.\.venv\Scripts\python -m omnissa_archive fetch
.\.venv\Scripts\python -m omnissa_archive refresh
.\.venv\Scripts\python -m omnissa_archive serve --port 8765
.\.venv\Scripts\python -m omnissa_archive guardian
.\.venv\Scripts\python -m omnissa_archive package --output dist
.\.venv\Scripts\python -m omnissa_archive search "Horizon logs"
```

עדכון חודשי הוא `refresh`, לא `Open-Download.bat`. הקובץ הזה ממשיך תור קיים בלי לקרוא מחדש את מפות האתר.

`refresh` מדפיס קודם סיכום לכל מפת אתר, בלי זמן ובלי כותרת, למשל `docs sitemap-0001.xml english=65 new=0`. `new=0` אומר שהכתובות כבר במסד. בסוף השלב מופיעים `changed` לתיעוד ושורת מפת ה־KB. רק אחר כך, ורק לעמוד חדש או שהתאריך שלו השתנה, מודפסת שורת הורדה עם זמן מקומי, `docs` או `kb`, מיקום מתוך הסך, מספר KB, כותרת, וסיכום `saved/done/pending/running/error`.

אחרי סיום ההורדה, עותק עקבי ללקוח:

```powershell
.\.venv\Scripts\python installer\stage_library.py
```

הקובץ נכתב אל `dist\package-staging\archive.sqlite`. אצל הלקוח שמים אותו ב־`data\library\inbox\`.
