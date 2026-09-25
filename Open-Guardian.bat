@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo The local Python environment is missing. Run the install steps in README.md first.
  pause
  exit /b 1
)
start "Omnissa Archive" .\.venv\Scripts\python -m omnissa_archive serve --port 8765
start "Omnissa Guardian" .\.venv\Scripts\python -m omnissa_archive guardian --port 8766 --reader-url http://127.0.0.1:8765
echo Archive:  http://127.0.0.1:8765/
echo Guardian: http://127.0.0.1:8766/
