@echo off
cd /d "%~dp0"
chcp 65001 >nul
if not exist .venv\Scripts\python.exe (
  echo חסר סביבת Python מקומית. התקינו לפי README.md
  pause
  exit /b 1
)
echo.
echo הורדת הארכיון ממשיכה מהתור הקיים.
echo עמודים שכבר סומנו כ-done לא יורדים מחדש.
echo עמוד שנעצר באמצע יחזור לתור ויתועדף בניסיון הבא.
echo לעצירה: Ctrl+C בחלון הזה. להמשך: הריצו שוב את הקובץ.
echo.
.\.venv\Scripts\python -m omnissa_archive fetch
echo.
echo סיום ריצת ההורדה. קוד יציאה: %ERRORLEVEL%
pause
