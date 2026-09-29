@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (
  echo Please run scripts/setup.ps1 first.
  pause
  exit /b 1
)
start "QA agent" ".venv\Scripts\pythonw.exe" -m desktop_app --ui tk %*
