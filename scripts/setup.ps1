param([Parameter(Mandatory=$true)][string]$PythonExe,[string]$Environment='.venv',[string]$CaBundle='')
$ErrorActionPreference='Stop'
$Project=Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $Project
$PythonPath=(Resolve-Path -LiteralPath $PythonExe).Path
& $PythonPath -c "import sys,struct,tkinter; assert sys.version_info[:3]==(3,10,4),sys.version; assert struct.calcsize('P')*8==64; print(sys.executable); print(sys.version); print('Tk',tkinter.TkVersion)"
if ($LASTEXITCODE -ne 0) { throw 'Requires Windows x64 Python exactly 3.10.4 with Tcl/Tk.' }
if ($Environment -notmatch '^\.venv(?:-[a-zA-Z0-9]+)?$') { throw 'Environment must be .venv or .venv-name inside this project.' }
$EnvPath=Join-Path $Project $Environment
if (Test-Path -LiteralPath $EnvPath) { throw 'Environment already exists. Choose a new environment name; existing environments are not overwritten.' }
& $PythonPath -m venv $EnvPath
if ($LASTEXITCODE -ne 0) { throw 'venv creation failed.' }
$EnvPython=Join-Path $EnvPath 'Scripts\python.exe'
$PreviousCert=$env:PIP_CERT
try {
    if ($CaBundle) { $env:PIP_CERT=(Resolve-Path -LiteralPath $CaBundle).Path }
    & $EnvPython -m pip install --requirement requirements.lock
    if ($LASTEXITCODE -ne 0) { throw 'Install failed. Ask IT for an approved CA bundle or package mirror. TLS verification remains enabled.' }
    & $EnvPython -m pip check
    if ($LASTEXITCODE -ne 0) { throw 'Dependency check failed.' }
    & $EnvPython scripts/doctor.py
    if ($LASTEXITCODE -ne 0) { throw 'Environment diagnostic failed.' }
} finally { $env:PIP_CERT=$PreviousCert }
