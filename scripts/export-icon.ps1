param([string]$Source='', [string]$Destination='')
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Drawing
$Project=Split-Path -Parent $PSScriptRoot
if (-not $Source) { $Source=Join-Path $Project 'desktop_app\assets\qa-agent.png' }
if (-not $Destination) { $Destination=Join-Path $Project 'desktop_app\assets' }
$null=New-Item -ItemType Directory -Force -Path $Destination
$SourceImage=[System.Drawing.Image]::FromFile((Resolve-Path -LiteralPath $Source).Path)
$Sizes=@(16,24,32,48,64,128,256)
$Frames=[System.Collections.Generic.List[byte[]]]::new()
try {
    foreach ($Size in $Sizes) {
        $Bitmap=[System.Drawing.Bitmap]::new($Size,$Size,[System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
        $Graphics=[System.Drawing.Graphics]::FromImage($Bitmap)
        try {
            $Graphics.Clear([System.Drawing.Color]::Transparent)
            $Graphics.CompositingMode=[System.Drawing.Drawing2D.CompositingMode]::SourceCopy
            $Graphics.CompositingQuality=[System.Drawing.Drawing2D.CompositingQuality]::HighQuality
            $Graphics.InterpolationMode=[System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
            $Graphics.PixelOffsetMode=[System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
            $Graphics.DrawImage($SourceImage,0,0,$Size,$Size)
            $Memory=[System.IO.MemoryStream]::new()
            try {
                $Bitmap.Save($Memory,[System.Drawing.Imaging.ImageFormat]::Png)
                $Bytes=$Memory.ToArray()
                $Frames.Add($Bytes)
                [System.IO.File]::WriteAllBytes((Join-Path $Destination "qa-agent-$Size.png"),$Bytes)
            } finally { $Memory.Dispose() }
        } finally { $Graphics.Dispose(); $Bitmap.Dispose() }
    }
    $Stream=[System.IO.File]::Create((Join-Path $Destination 'qa-agent.ico'))
    $Writer=[System.IO.BinaryWriter]::new($Stream)
    try {
        $Writer.Write([uint16]0); $Writer.Write([uint16]1); $Writer.Write([uint16]$Sizes.Count)
        $Offset=6+16*$Sizes.Count
        for ($Index=0; $Index -lt $Sizes.Count; $Index++) {
            $Side=if ($Sizes[$Index] -eq 256) { 0 } else { $Sizes[$Index] }
            $Writer.Write([byte]$Side); $Writer.Write([byte]$Side)
            $Writer.Write([byte]0); $Writer.Write([byte]0)
            $Writer.Write([uint16]1); $Writer.Write([uint16]32)
            $Writer.Write([uint32]$Frames[$Index].Length); $Writer.Write([uint32]$Offset)
            $Offset+=$Frames[$Index].Length
        }
        foreach ($Frame in $Frames) { $Writer.Write([byte[]]$Frame) }
    } finally { $Writer.Dispose(); $Stream.Dispose() }
} finally { $SourceImage.Dispose() }
Write-Output 'Exported transparent PNG sizes and seven-size Windows ICO.'
