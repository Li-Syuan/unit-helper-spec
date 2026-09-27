param([string]$PythonExe='', [string]$Destination='wheelhouse', [string]$CaBundle='')
$ErrorActionPreference='Stop'
$Project=Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $Project
if (-not $PythonExe) { $PythonExe=Join-Path $Project '.venv\Scripts\python.exe' }
$PythonPath=(Resolve-Path -LiteralPath $PythonExe).Path
$PreviousCert=$env:PIP_CERT
try {
    if ($CaBundle) { $env:PIP_CERT=(Resolve-Path -LiteralPath $CaBundle).Path }
    & $PythonPath scripts/offline_bundle.py build --directory $Destination
    if ($LASTEXITCODE -ne 0) { throw 'Offline bundle preparation failed. Use a new destination for retry; no partial bundle is considered verified.' }
} finally { $env:PIP_CERT=$PreviousCert }
