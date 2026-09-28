# מפרט: Omnissa Archive ו־Omnissa Guardian

תאריך מקורי: 2026-09-25  
עודכן: 2026-09-28  
סטטוס: מיושם  
מרחב: `C:\GitHub\Omnissas Guardian`

## 1. מטרה

עותק מקומי של התיעוד הציבורי באנגלית מ־docs.omnissa.com ושל מאמרי kb.omnissa.com, לאתרים בלי אינטרנט. התוכן נשאר של Omnissa. זה לא אתר מראה ציבורי.

שני שימושים על אותו מסד:

| שימוש | מי מפעיל | מה קורה |
|---|---|---|
| הורדת התוכן | מי שמכין את המסד | `discover` / `fetch` / `refresh` כותבים ל־SQLite ולתיקיית תמונות |
| שימוש אצל הלקוח | מנהל סביבה | חלון Guardian סורק לוג, משווה שגיאה למסד, ופותח את הארכיון מקומית |

המטרה המרכזית של Guardian: נתיב לוג, מקומי או UNC, נכנס. שורת שגיאה מושוות למאמרי ה־KB שנשמרו אצלו. חיפוש באתרים הציבוריים הוא תוספת ידנית, כבויה כברירת מחדל, ולא חלק מהסריקה.

## 2. הפצה ללקוח

ללקוח אין BAT ואין Python.

פעם ראשונה: `dist\OmnissaGuardianSetup.exe`  
ההתקנה פורסת:

```
{autopf}\Omnissa Guardian\
  OmnissaGuardian.exe
  _internal\
  data\
    library\
      archive.sqlite
      inbox\
    assets\
```

ה־EXE נושא את אייקון המגן (`assets\omnissa-guardian.ico`): רקע `#2c2c3e`, מגן `#f07a58`, סימן `#e8b545`. האייקון מופיע על הקובץ, על קיצור הדרך, ועל החלון.

לחיצה על הקיצור פותחת את חלון הניטור ומפעילה את שרת הארכיון על `127.0.0.1:8765` בלבד. מחשבים אחרים ברשת לא ניגשים אליו.

פעם בחודש, במחשב שמכין את המסד:

```powershell
.\.venv\Scripts\python -m omnissa_archive refresh
.\.venv\Scripts\python installer\stage_library.py
```

`refresh` קורא מחדש את מפות האתר ומוריד רק כתובת חדשה או כתובת שהתאריך שלה השתנה. `stage_library.py` כותב עותק עקבי אל `dist\package-staging\archive.sqlite`, בלי קובץ WAL פתוח באמצע.

הלקוח שם את `archive.sqlite` החדש ב־`data\library\inbox\`. הקובץ נבדק (חתימת SQLite וטבלת `documents`), מועתק אל `data\library\archive.sqlite`, והקודם נשמר ב־`data\libraries\`. אין התקנה מחדש ואין סגירת התוכנה. תמונות חדשות מגיעות יחד עם עדכון של `data\assets\`.

התקנה חוזרת לא דורסת מסד שכבר קיים. הסרה לא מוחקת את המסד ואת התמונות.

קובץ HTML יחיד לכל הארכיון לא מתאים: המסד והתמונות גדולים ממנו. חבילת `python -m omnissa_archive package` עדיין מייצרת תיקיית עותק פנימית `dist\Omnissa-Archive\`. זו לא החבילה שהלקוח מתקין.

בניית ההתקנה:

```powershell
.\.venv\Scripts\python installer\stage_library.py
.\.venv\Scripts\pyinstaller build\pyinstaller\OmnissaGuardian.spec --noconfirm --distpath dist --workpath build\pyinstaller
& "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe" installer\OmnissaGuardian.iss
```

`stage_library.py` מעתיק את המסד החי בעותק עקבי, בלי קובץ WAL פתוח באמצע.

## 3. ארכיון

ממשק מקומי בעברית, כיוון RTL.

- תפריט צד: ראשי, מאמרי KB, מסמכים, הגדרות
- בית: שתי קוביות, חמישה KB אחרונים וחמישה מסמכים אחרונים
- טבלה: תאריך, מספר KB, נושא, קטגוריה (משפחה · מוצר · גרסה · קטגוריה)
- סינון: משפחת מוצר, מוצר, גרסה, קטגוריה, מתאריך עד תאריך. מוצר וגרסה יכולים להיות רשימה מופרדת בפסיקים
- חיפוש FTS על הכותרת והטקסט
- הגדרות: טעינת מסד SQLite

פלטה: `#2c2c3e`, `#f07a58`, `#365565`, `#4d889d`, `#e8b545`, `#bebec6`.

תאריך פרסום במסמכי docs הוא `omnissa-datecreated`. ב־KB הוא `article:published_time`. הטקסט `Last updated:` בתחילת מאמר KB הוא תאריך העדכון שנשמר ב־`updated_at`.

## 4. Guardian

חלון כהה בסגנון קונסולת ניטור, עם עברית ואנגלית. השפה נשמרת ב־`data\guardian_config.json`.

נתיבי ברירת מחדל מתוך KB 1027744 (מיקום לוגי Horizon). הם נכונים כשהתהליך רץ על אותו שרת. משרת עם גישת SMB מדביקים UNC, למשל `\\host\C$\ProgramData\Omnissa\Horizon\logs`. החשבון שמריץ את התוכנה הוא החשבון שקורא את השיתוף. סיסמה לא נשמרת בתוכנה.

סריקה:

- מרווח ברירת מחדל 60 שניות, מינימום 15
- הסריקה הראשונה של קובץ קוראת את התוכן שכבר קיים. מעל 2MB נקראים שני המגה־בייט האחרונים
- אחר כך נקרא רק מה שהתווסף
- שורה מזוהה לפי error, exception, failed, failure, fatal, critical, warning
- החיפוש שולף מילים מהשורה, מוריד מילות רעש, ומדרג מאמרים ב־FTS
- ההתראה מציגה כותרת, תאריך, קטע, וקישור `/read/{id}` בארכיון המקומי

Guardian קורא את אותו מסד. תיבת `inbox` נבדקת גם ממנו, לא רק ממסך הארכיון.

החלון: ניטור חי, היסטוריה, תיקיות מעקב, מקורות KB, הגדרות, דוא״ל, יומן מערכת. עברית ואנגלית. לשונית הדוא״ל לא שולחת הודעות. הזיהויים נשארים במחשב.

### מסמכים אונליין

בלשונית מקורות KB נשאר אזור חיפוש בדפדפן, עם התבניות מהקליינט הקודם:

| שם | תבנית |
|---|---|
| Omnissa KB | `https://kb.omnissa.com/s/global-search/{q}` |
| Omnissa TechZone | `https://techzone.omnissa.com/search#q={q}` |
| Broadcom Support | `https://support.broadcom.com/web/ecx/search#q={q}` |
| VMware Community | `https://community.broadcom.com/search?q={q}` |
| Reddit r/vmware | `https://www.reddit.com/r/vmware/search/?q={q}` |
| Google | `https://www.google.com/search?q=Omnissa+Horizon+{q}` |

`{q}` הוא טקסט השגיאה, עד 200 תווים, אחרי קידוד לכתובת.

האזור מוצג תמיד. הוא לא נבדק בסריקת הלוג.

בהגדרות יש תיבה **חיפוש במסמכים אונליין**. היא נשמרת כ־`online_search` ב־`data\guardian_config.json`, וכבויה כברירת מחדל. בלי הסימון, לחיצה על **חיפוש אונליין** לא פונה לרשת.

כשהתיבה מסומנת, לחיצה על **חיפוש אונליין** (בלשונית או מתוך פירוט זיהוי) בודקת קודם חיבור TCP קצר אל `kb.omnissa.com` בפורט 443. אם החיבור נכשל, לא נפתח דפדפן והחיפוש נשאר על הארכיון המקומי. אם החיבור הצליח, נפתח חיפוש לכל תבנית.

לא כלול: שליחה לענן, סוכן על כל תחנה, תיקון אוטומטי, חבילת אבחון לספק, או פנייה אוטומטית לאתרי Omnissa בזמן סריקה.

## 5. הוראה והמשך אחרי עצירה

מקורות:

- docs: אינדקס sitemap, דפי אנגלית בלי קידומת שפה. גוף העמוד הוא `article .doc-body`. מטא־נתונים נקראים מהעמוד המלא.
- KB: רשימת SitemapGeneratorVF. המאמר מרונדר ב־Chrome דרך Playwright עד ש־`#article_content` ו־`article:published_time` מופיעים. מאמר שכבר לא זמין לא מנוסה שוב.

התור ב־`crawl_queue`: `pending`, `running`, `done`, `error`.  
`fetch` מחזיר `running` שנקטע אל `pending`, ומדלג על `done`. עד שלושה ניסיונות לשגיאה.

`refresh` הוא העדכון התקופתי: קודם `discover`, אחר כך `fetch`. `Open-Download.bat` מריץ רק `fetch`. הוא ממשיך תור קיים ולא קורא מחדש את מפות האתר, ולכן הוא לא העדכון החודשי.

בשלב מפות האתר כל שורה היא סיכום, בלי זמן ובלי כותרת:

```text
docs sitemap-0001.xml english=65 new=0
docs revisions stamped=… changed=…
kb sitemap articles=… new=… stamped=… changed=…
```

`english` ו־`articles` הם כמה כתובות נמצאו במפה. `new` הוא כמה מהן לא היו בתור. `changed` הוא כמה כתובות שה־`lastmod` שלהן השתנה וחזרו אל `pending`.

`lastmod` של המפה נשמר בנפרד. בשמירה, אם `Last updated` זהה, גוף העמוד לא נכתב מחדש.

שורת לוג של הורדה מופיעה רק אחר כך, ורק לעמוד שבאמת יורד:

```text
YYYY-MM-DD HH:MM:SS docs|kb n/total KB id|— | כותרת או סטטוס | saved=… done=… pending=… running=… error=…
```

הזמן הוא השעון המקומי.

קצב מנומס: בערך 3 בקשות בשנייה לתיעוד, ומאמר KB אחד בכל פעם עם השהיה. `robots.txt` נשמר: אין `/api/` ואין `/search` בתיעוד, וב־KB אין `/articles/`. המאמרים עצמם נלקחים מ־`/s/article/`.

## 6. אחסון

SQLite עם WAL ו־FTS5 על כותרת וטקסט.

`documents`: מקור, כתובת, כותרת, גוף, hash, מוצר, משפחה, גרסה, קטגוריה, תאריך פרסום, תאריך עדכון, `sitemap_lastmod`.  
`crawl_queue`: כתובת, סטטוס, ניסיונות, `remote_lastmod`.  
תמונות ו־PDF ב־`data\assets\`, וה־HTML המקומי מצביע אליהן.

במחשב הפיתוח המסד החי הוא `data\archive.sqlite`. אצל הלקוח הוא `data\library\archive.sqlite`.

## 7. העברה למחשב אחר

`data\`, `.venv\`, `build\` ו־`dist\` לא נכנסים ל־Git. הקוד כן.

כדי להמשיך הורדה במחשב חדש מעתיקים את `data\archive.sqlite` אחרי `PRAGMA wal_checkpoint(TRUNCATE)`, ואת `data\assets\`. בלי המסד התור ריק. אחר כך יוצרים `.venv` מחדש עם Python המקומי ומריצים `refresh` או `fetch`. פירוט הפקודות ב־`README.md`.

`.venv` שהועתק ממחשב או ממשתמש אחר לא שמיש. `pyvenv.cfg` שומר את נתיב ה־Python שיצר אותו, וההתקנה הניתנת לעריכה שומרת את נתיב קוד המקור. במחשב החדש יוצרים סביבה חדשה.

## 8. הצלחה

- לקוח מתקין מקובץ אחד, בלי Python, ורואה את האייקון על קובץ התוכנה.
- החלפת מסד חודשית נטענת בלי ריסטארט.
- נתיב UNC עם שגיאה קיימת בלוג מציג מאמר מהמסד המקומי כבר בסריקה הראשונה.
- הורדה שנעצרת באמצע ממשיכה מהתור במחשב הזה או במחשב שאליו הועתק `data\`.
- עדכון חודשי עם `refresh` מדפיס קודם סיכומי מפות אתר. שורות עם זמן וכותרת מופיעות רק לעמודים שהשתנו או שנוספו.
- סריקת לוג לא פונה לאתרי Omnissa. חיפוש אונליין נפתח רק אחרי סימון בהגדרות, לחיצה מפורשת, וחיבור אל `kb.omnissa.com`.
