[CmdletBinding()]
param([string]$Destination = [Environment]::GetFolderPath('Desktop'))
$ErrorActionPreference = 'Stop'
$Project = (Resolve-Path -LiteralPath (Split-Path -Parent $PSScriptRoot)).Path
$Marker = 'QA agent desktop launcher [unit-helper-spec]'
$Python = Join-Path $Project '.venv\Scripts\python.exe'
$Pythonw = Join-Path $Project '.venv\Scripts\pythonw.exe'
$Icon = Join-Path $Project 'desktop_app\assets\qa-agent.ico'
$Png = Join-Path $Project 'desktop_app\assets\qa-agent.png'
foreach ($Required in @($Python, $Pythonw, $Icon, $Png)) {
    if (-not (Test-Path -LiteralPath $Required -PathType Leaf)) {
        throw "Required project file is missing: $Required. Rebuild the environment or restore app assets first."
    }
}
& $Python -c "import sys,struct,tkinter; assert sys.platform=='win32'; assert sys.version_info[:3]==(3,10,4); assert struct.calcsize('P')==8; r=tkinter.Tk(); r.withdraw(); r.destroy()"
if ($LASTEXITCODE -ne 0) { throw 'Requires Windows x64 Python exactly 3.10.4 with working Tcl/Tk.' }
if ([string]::IsNullOrWhiteSpace($Destination) -or -not (Test-Path -LiteralPath $Destination -PathType Container)) {
    throw 'Destination must be an existing directory. The Windows Desktop folder could not be resolved.'
}
$DestinationPath = (Resolve-Path -LiteralPath $Destination).Path
$ShortcutPath = Join-Path $DestinationPath 'QA agent.lnk'
$Shell = New-Object -ComObject WScript.Shell
function Assert-OwnedShortcut {
    if (Test-Path -LiteralPath $ShortcutPath) {
        if (-not (Test-Path -LiteralPath $ShortcutPath -PathType Leaf)) { throw 'The shortcut name is occupied by a directory.' }
        $Existing = $Shell.CreateShortcut($ShortcutPath)
        try {
            if ($Existing.Description -cne $Marker -or $Existing.Arguments -cne '-m desktop_app' -or
                $Existing.TargetPath -notmatch '[\\/]\.venv[\\/]Scripts[\\/]pythonw\.exe$') {
                throw 'An unrelated QA agent shortcut already exists. It was not changed. Rename it before trying again.'
            }
        } finally { [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($Existing) }
    }
}
$TemporaryPath = Join-Path $DestinationPath ('.qa-agent-' + [Guid]::NewGuid().ToString('N') + '.lnk')
try {
    Assert-OwnedShortcut
    $Shortcut = $Shell.CreateShortcut($TemporaryPath)
    try {
        $Shortcut.TargetPath = $Pythonw
        $Shortcut.Arguments = '-m desktop_app'
        $Shortcut.WorkingDirectory = $Project
        $Shortcut.IconLocation = $Icon + ',0'
        $Shortcut.Description = $Marker
        $Shortcut.WindowStyle = 1
        $Shortcut.Save()
    } finally { [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($Shortcut) }
    Assert-OwnedShortcut
    Move-Item -LiteralPath $TemporaryPath -Destination $ShortcutPath -Force
    Write-Output "QA agent shortcut is ready: $ShortcutPath"
} finally {
    if (Test-Path -LiteralPath $TemporaryPath -PathType Leaf) { Remove-Item -LiteralPath $TemporaryPath }
    [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($Shell)
}
