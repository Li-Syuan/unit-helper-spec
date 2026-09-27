@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
if errorlevel 1 goto failed
powershell.exe -NoLogo -NoProfile -File "%~dp0scripts\create-shortcut.ps1"
if errorlevel 1 goto failed
echo You can now open QA agent from your desktop.
pause
exit /b 0
:failed
echo Unable to create the QA agent shortcut. See the error above.
echo If company policy blocks scripts, ask IT to approve scripts\create-shortcut.ps1.
pause
exit /b 1
