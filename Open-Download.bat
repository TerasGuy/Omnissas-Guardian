@echo off
cd /d "%~dp0"
chcp 65001 >nul
if not exist .venv\Scripts\python.exe (
  echo The local Python environment is missing. Install it using README.md.
  pause
  exit /b 1
)
echo.
echo The archive download continues from the existing queue.
echo Pages already marked done are not downloaded again.
echo A page stopped in the middle returns to the queue and is tried first next time.
echo To stop: Ctrl+C in this window. To continue: run this file again.
echo.
.\.venv\Scripts\python -m omnissa_archive fetch
echo.
echo Download run finished. Exit code: %ERRORLEVEL%
pause
