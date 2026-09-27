@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
if errorlevel 1 exit /b 1
call "%~dp0start-app.bat" --check
if errorlevel 1 goto failed
if /i "%~1"=="--check" exit /b 0
start "" /d "%~dp0" ".venv\Scripts\pythonw.exe" -m desktop_app --groq-trial
if errorlevel 1 goto failed
exit /b 0
:failed
echo Unable to start QA agent Groq trial.
if /i "%~1"=="--check" exit /b 1
pause
exit /b 1
