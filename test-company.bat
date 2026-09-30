@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Missing project Python environment. First run:
  echo install-offline.bat "C:\approved\Python3104\python.exe"
  echo Requires Python 3.10.4 x64 with Tk, 69 verified wheels, WebView2 and .NET.
  exit /b 1
)
".venv\Scripts\python.exe" "scripts\company-test.py" %*
set "TEST_RESULT=%ERRORLEVEL%"
if not "%TEST_RESULT%"=="0" echo Validation failed or company checks were not executed. Read the report above.
exit /b %TEST_RESULT%
