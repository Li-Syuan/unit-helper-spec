param([string]$Config='')
$ErrorActionPreference='Stop'
$Project=Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $Project
$Python=Join-Path $Project '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $Python)) { throw 'Run scripts/setup.ps1 first.' }
if ($Config) { & $Python -m desktop_app --config $Config } else { & $Python -m desktop_app }
exit $LASTEXITCODE
