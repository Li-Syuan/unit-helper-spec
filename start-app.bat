@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
if errorlevel 1 goto failed
if not exist ".venv\Scripts\python.exe" goto missing
if not exist ".venv\Scripts\pythonw.exe" goto missing
".venv\Scripts\python.exe" "scripts\check-launch.py" --check-sdk
if errorlevel 1 goto failed
if /i "%~1"=="--check" exit /b 0
start "" /d "%~dp0" ".venv\Scripts\pythonw.exe" -m desktop_app
if errorlevel 1 goto failed
exit /b 0

:missing
echo Project Python environment is missing.
echo Please follow ENVIRONMENT.md to run scripts\setup.ps1 first.
goto failed

:failed
echo Unable to start QA agent. See the error above.
echo For diagnostics, run: .venv\Scripts\python.exe -m desktop_app
if /i "%~1"=="--check" exit /b 1
pause
exit /b 1
