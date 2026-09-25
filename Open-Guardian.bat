@echo off
cd /d "%~dp0"
chcp 65001 >nul
if exist "dist\OmnissaGuardian\OmnissaGuardian.exe" (
  start "" "dist\OmnissaGuardian\OmnissaGuardian.exe"
  exit /b 0
)
if exist "dist\OmnissaGuardian.exe" (
  start "" "dist\OmnissaGuardian.exe"
  exit /b 0
)
if not exist .venv\Scripts\python.exe (
  echo חסרה סביבת Python מקומית. התקינו לפי README.md
  pause
  exit /b 1
)
echo פותח את Omnissa Guardian כחלון שולחני (לא דפדפן)...
start "Omnissa Guardian" .\.venv\Scripts\python -m omnissa_archive guardian --reader-url http://127.0.0.1:8765
