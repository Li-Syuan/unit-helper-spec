param(
    [string]$Environment='.venv',
    [ValidateSet('quick','targeted','full')][string]$Suite='quick',
    [string[]]$Tests=@()
)
$ErrorActionPreference='Stop'
$Project=Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $Project
if ($Environment -notmatch '^\.venv(?:-[a-zA-Z0-9]+)?$') { throw 'Invalid environment name.' }
$Python=Join-Path $Project "$Environment\Scripts\python.exe"
$RunnerArgs=@('scripts/test_runner.py','--suite',$Suite)
if ($Tests.Count -gt 0) { $RunnerArgs+=@('--tests'); $RunnerArgs+=$Tests }
& $Python @RunnerArgs
exit $LASTEXITCODE
