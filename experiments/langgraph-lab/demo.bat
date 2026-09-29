@echo off
if not exist "%~dp0.venv\Scripts\python.exe" (
  echo Run install.bat first.
  pause
  exit /b 1
)
"%~dp0.venv\Scripts\python.exe" -I -X utf8 "%~dp0demo.py"
set "QA_LAB_RESULT=%ERRORLEVEL%"
pause
exit /b %QA_LAB_RESULT%
