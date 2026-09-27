param()
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Drawing
$project=Split-Path -Parent $PSScriptRoot
$assets=Join-Path $project 'desktop_app/assets/candidates'
$board=[Drawing.Bitmap]::new(1280,960)
$g=[Drawing.Graphics]::FromImage($board)
$font=[Drawing.Font]::new('Microsoft JhengHei',18,[Drawing.FontStyle]::Bold)
$small=[Drawing.Font]::new('Microsoft JhengHei',10)
$names=@('Q 對話夥伴','QA 字母融合','雙對話框協作','極簡 Agent 面罩')
function Brush($hex) { [Drawing.SolidBrush]::new([Drawing.ColorTranslator]::FromHtml($hex)) }
try {
 for($row=0;$row -lt 2;$row++){
  $bg=if($row -eq 0){'#202124'}else{'#F6F7F9'}
  $fg=if($row -eq 0){'#ECEEF1'}else{'#222833'}
  $b=Brush $bg; $g.FillRectangle($b,0,($row*480),1280,480); $b.Dispose()
  $b=Brush $fg
  for($col=0;$col -lt 4;$col++){
   $letter=[string][char](65+$col); $x=20+$col*320; $y=$row*480
   $g.DrawString("$letter  $($names[$col])",$font,$b,$x,($y+20))
   $img=[Drawing.Bitmap]::new((Join-Path $assets "$letter.png"))
   try {
    foreach($size in @(16,32,48,224)){
     $thumb=[Drawing.Bitmap]::new($size,$size,[Drawing.Imaging.PixelFormat]::Format32bppArgb)
     $tg=[Drawing.Graphics]::FromImage($thumb)
     try {
      $tg.Clear([Drawing.Color]::Transparent)
      $tg.InterpolationMode=[Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
      $tg.PixelOffsetMode=[Drawing.Drawing2D.PixelOffsetMode]::HighQuality
      $tg.DrawImage($img,0,0,$size,$size)
      if($row -eq 0){ $thumb.Save((Join-Path $assets "$letter-$size.png"),[Drawing.Imaging.ImageFormat]::Png) }
      if($size -eq 224){ $g.DrawImageUnscaled($thumb,($x+24),($y+70)) }
      else{
       $index=@(16,32,48).IndexOf($size); $px=$x+32+$index*88
       $g.DrawImageUnscaled($thumb,$px,($y+336+(48-$size)/2))
       $g.DrawString("$size px",$small,$b,$px,($y+400))
      }
     }finally{$tg.Dispose();$thumb.Dispose()}
    }
    if($row -eq 0){Write-Output "$letter $($img.Width)x$($img.Height) corner alpha=$($img.GetPixel(0,0).A)"}
   }finally{$img.Dispose()}
  }
  $b.Dispose()
 }
 $board.Save((Join-Path $project 'docs/images/icon-candidates.png'),[Drawing.Imaging.ImageFormat]::Png)
}finally{$g.Dispose();$board.Dispose();$font.Dispose();$small.Dispose()}

