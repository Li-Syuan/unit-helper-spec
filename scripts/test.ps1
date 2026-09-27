param([string]$Environment='.venv')
$ErrorActionPreference='Stop'
$Project=Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $Project
if ($Environment -notmatch '^\.venv(?:-[a-zA-Z0-9]+)?$') { throw 'Invalid environment name.' }
$Python=Join-Path $Project "$Environment\Scripts\python.exe"
& $Python scripts/doctor.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $Python -m pip check
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $Python -m unittest discover -s tests -v
exit $LASTEXITCODE
