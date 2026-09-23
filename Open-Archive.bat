@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo The local Python environment is missing. Run the install steps in README.md first.
  pause
  exit /b 1
)
.\.venv\Scripts\python -m omnissa_archive serve
