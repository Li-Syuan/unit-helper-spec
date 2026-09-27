[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][ValidateSet('Inspect','CreateUnrelated')][string]$Action,
    [Parameter(Mandatory=$true)][string]$ShortcutPath
)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.UTF8Encoding]::new()
$Shell = New-Object -ComObject WScript.Shell
try {
    $Shortcut = $Shell.CreateShortcut($ShortcutPath)
    try {
        if ($Action -eq 'CreateUnrelated') {
            $Shortcut.TargetPath = $env:ComSpec
            $Shortcut.Description = 'Another application'
            $Shortcut.Save()
        } else {
            @{
                target = $Shortcut.TargetPath
                arguments = $Shortcut.Arguments
                directory = $Shortcut.WorkingDirectory
                icon = $Shortcut.IconLocation
                description = $Shortcut.Description
            } | ConvertTo-Json -Compress
        }
    } finally { [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($Shortcut) }
} finally { [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($Shell) }
