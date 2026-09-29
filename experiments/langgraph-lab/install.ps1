param([string]$PythonExe='')
$ErrorActionPreference='Stop'
if (-not $PythonExe) { $PythonExe=(Read-Host 'Full path to Python 3.10.4 x64 python.exe').Trim().Trim('"') }
if (-not (Test-Path -LiteralPath $PythonExe -PathType Leaf)) { throw 'Python executable not found.' }
& $PythonExe -I -X utf8 (Join-Path $PSScriptRoot 'setup_entry.py')
exit $LASTEXITCODE
