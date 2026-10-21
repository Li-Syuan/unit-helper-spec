@echo off
setlocal
if not exist "%~dp0.venv\Scripts\python.exe" (
  echo Please install the project environment with install-offline.bat first.
  exit /b 1
)
pushd "%~dp0"
"%~dp0.venv\Scripts\python.exe" -X utf8 -m desktop_app.cli %*
set "qa_exit=%errorlevel%"
popd
exit /b %qa_exit%
