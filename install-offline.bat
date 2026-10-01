@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
if "%~1"=="" goto usage
if not exist "%~1" goto usage
"%~1" "scripts\install-offline.py" --offline-bundle "wheelhouse"
set "QA_INSTALL_RESULT=%ERRORLEVEL%"
pause
exit /b %QA_INSTALL_RESULT%
:usage
echo Usage: install-offline.bat "C:\approved\Python3104\python.exe"
echo Run from CMD with the approved Python 3.10.4 x64 executable path.
echo Extract the COMPLETE current Code ZIP or official offline ZIP first.
echo Code ZIP reuses tracked lab wheels plus the verified App additions.
echo No PowerShell policy change is required. Existing .venv is not overwritten.
pause
exit /b 2
