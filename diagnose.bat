@echo off
setlocal
set "PYTHONIOENCODING=utf-8"
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Project environment missing. Read ENVIRONMENT.md and run scripts\setup.ps1 first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" "scripts\doctor.py" --human --output "artifacts\diagnostics\readiness.json"
set "DIAGNOSTIC_EXIT=%ERRORLEVEL%"
echo Share-safe report: artifacts\diagnostics\readiness.json
echo Company service acceptance is separate from this offline check.
pause
exit /b %DIAGNOSTIC_EXIT%
