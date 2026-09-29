param([Parameter(Mandatory=$true)][string]$PythonExe,[string]$Environment='.venv',[string]$CaBundle='',[string]$OfflineBundle='')
$ErrorActionPreference='Stop'
$Project=Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $Project
$PythonPath=(Resolve-Path -LiteralPath $PythonExe).Path
& $PythonPath scripts/check-python.py
if ($LASTEXITCODE -ne 0) { throw 'Requires Windows x64 Python exactly 3.10.4 with Tcl/Tk.' }
if ($Environment -notmatch '^\.venv(?:-[a-zA-Z0-9]+)?$') { throw 'Environment must be .venv or .venv-name inside this project.' }
$EnvPath=Join-Path $Project $Environment
if (Test-Path -LiteralPath $EnvPath) { throw 'Environment already exists. Choose a new environment name; existing environments are not overwritten.' }
if ($OfflineBundle) {
    $BundlePath=(Resolve-Path -LiteralPath $OfflineBundle).Path
    & $PythonPath scripts/offline_bundle.py verify --directory $BundlePath
    if ($LASTEXITCODE -ne 0) { throw 'Offline bundle validation failed. No environment was created.' }
}
& $PythonPath -m venv $EnvPath
if ($LASTEXITCODE -ne 0) { throw 'venv creation failed.' }
$EnvPython=Join-Path $EnvPath 'Scripts\python.exe'
$PreviousCert=$env:PIP_CERT
try {
    if ($CaBundle) { $env:PIP_CERT=(Resolve-Path -LiteralPath $CaBundle).Path }
    if ($OfflineBundle) {
        # Resolve the exact lock from verified local wheels, preserving portable name==version freeze records.
        & $EnvPython -m pip --isolated install --disable-pip-version-check --no-index --no-deps --no-cache-dir --only-binary=:all: --find-links $BundlePath --requirement requirements.lock
    } else {
        & $EnvPython -m pip install --requirement requirements.lock
    }
    if ($LASTEXITCODE -ne 0) { throw 'Install failed. Offline installs never fall back to a network index. For online installs ask IT for an approved CA or mirror.' }
    & $EnvPython -m pip check
    if ($LASTEXITCODE -ne 0) { throw 'Dependency check failed.' }
    & $EnvPython scripts/doctor.py
    if ($LASTEXITCODE -ne 0) { throw 'Environment diagnostic failed. Read individual check statuses; existing user configuration may need attention.' }
} finally { $env:PIP_CERT=$PreviousCert }
