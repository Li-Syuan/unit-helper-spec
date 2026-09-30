@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Missing project environment. Run install-offline.bat first.
  exit /b 1
)
".venv\Scripts\python.exe" -m desktop_app --demo-login
exit /b %ERRORLEVEL%
