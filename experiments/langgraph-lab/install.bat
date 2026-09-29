@echo off
powershell.exe -NoProfile -File "%~dp0install.ps1"
set "QA_LAB_RESULT=%ERRORLEVEL%"
pause
exit /b %QA_LAB_RESULT%
