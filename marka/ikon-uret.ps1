# logo.svg ile ayni cizimi GDI+ ile PNG/ICO olarak uretir (ek arac gerektirmez).
# Kullanim: powershell -File istemci\marka\ikon-uret.ps1
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
$cikis = Join-Path $PSScriptRoot 'ikonlar'

function Ciz-Logo([int]$boyut) {
    $bmp = New-Object System.Drawing.Bitmap $boyut, $boyut, ([System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.SmoothingMode = 'AntiAlias'; $g.PixelOffsetMode = 'HighQuality'; $g.Clear([System.Drawing.Color]::Transparent)
    $s = $boyut / 512.0
    $g.ScaleTransform($s, $s)

    $mavi = [System.Drawing.ColorTranslator]::FromHtml('#1D4ED8')
    $turkuaz = [System.Drawing.ColorTranslator]::FromHtml('#06B6D4')
    $beyaz = [System.Drawing.Color]::White

    # Yuvarlak kose kare + gradyan
    $r = 112; $d = 2 * $r
    $yol = New-Object System.Drawing.Drawing2D.GraphicsPath
    $yol.AddArc(0, 0, $d, $d, 180, 90); $yol.AddArc(512 - $d, 0, $d, $d, 270, 90)
    $yol.AddArc(512 - $d, 512 - $d, $d, $d, 0, 90); $yol.AddArc(0, 512 - $d, $d, $d, 90, 90); $yol.CloseFigure()
    $firca = New-Object System.Drawing.Drawing2D.LinearGradientBrush (New-Object System.Drawing.PointF 0, 0), (New-Object System.Drawing.PointF 512, 512), $mavi, $turkuaz
    $g.FillPath($firca, $yol)

    # Kucuk boyutlarda cizgiler kalinlassin
    $k = if ($boyut -le 32) { 1.6 } elseif ($boyut -le 64) { 1.25 } else { 1.0 }

    $ince = New-Object System.Drawing.Pen ([System.Drawing.Color]::FromArgb(217, 255, 255, 255)), (14 * $k)
    $ince.StartCap = 'Round'; $ince.EndCap = 'Round'
    if ($boyut -gt 24) {
        $g.DrawLine($ince, 196, 255, 196, 330); $g.DrawLine($ince, 256, 230, 256, 330); $g.DrawLine($ince, 316, 255, 316, 330)
    }
    $kalin = New-Object System.Drawing.Pen $beyaz, (28 * $k)
    $kalin.StartCap = 'Round'; $kalin.EndCap = 'Round'
    # Q(136,330 256,130 376,330) -> kubik bezier
    $g.DrawBezier($kalin, 136, 330, 216, 196.67, 296, 196.67, 376, 330)
    $g.DrawLine($kalin, 96, 330, 416, 330)

    $bf = New-Object System.Drawing.SolidBrush $beyaz
    $dis = 34 * [math]::Min($k, 1.2); $ic = 14 * [math]::Min($k, 1.2)
    foreach ($x in 96, 416) { $g.FillEllipse($bf, $x - $dis, 330 - $dis, 2 * $dis, 2 * $dis) }
    $g.FillEllipse((New-Object System.Drawing.SolidBrush $mavi), 96 - $ic, 330 - $ic, 2 * $ic, 2 * $ic)
    $g.FillEllipse((New-Object System.Drawing.SolidBrush $turkuaz), 416 - $ic, 330 - $ic, 2 * $ic, 2 * $ic)
    $g.Dispose()
    return $bmp
}

function Png-Bayt([System.Drawing.Bitmap]$b) {
    $ms = New-Object System.IO.MemoryStream
    $b.Save($ms, [System.Drawing.Imaging.ImageFormat]::Png)
    return , $ms.ToArray()
}

function Yaz-Ico([string]$yol, [int[]]$boyutlar) {
    $resimler = foreach ($b in $boyutlar) { , (Png-Bayt (Ciz-Logo $b)) }
    $fs = [System.IO.File]::Create($yol); $w = New-Object System.IO.BinaryWriter $fs
    $w.Write([uint16]0); $w.Write([uint16]1); $w.Write([uint16]$boyutlar.Count)
    $ofset = 6 + 16 * $boyutlar.Count
    for ($i = 0; $i -lt $boyutlar.Count; $i++) {
        $b = $boyutlar[$i]; $veri = $resimler[$i]
        $bb = if ($b -ge 256) { 0 } else { $b }
        $w.Write([byte]$bb); $w.Write([byte]$bb); $w.Write([byte]0); $w.Write([byte]0)
        $w.Write([uint16]1); $w.Write([uint16]32); $w.Write([uint32]$veri.Length); $w.Write([uint32]$ofset)
        $ofset += $veri.Length
    }
    foreach ($veri in $resimler) { $w.Write($veri) }
    $w.Close()
}

New-Item -ItemType Directory -Force $cikis | Out-Null
(Ciz-Logo 512).Save((Join-Path $cikis 'icon.png'), [System.Drawing.Imaging.ImageFormat]::Png)
Yaz-Ico (Join-Path $cikis 'icon.ico') @(16, 24, 32, 48, 64, 128, 256)
Yaz-Ico (Join-Path $cikis 'tray-icon.ico') @(16, 24, 32, 48, 64)
foreach ($b in 32, 64, 128, 256) { (Ciz-Logo $b).Save((Join-Path $cikis "${b}x${b}.png"), [System.Drawing.Imaging.ImageFormat]::Png) }

# Baslik logosu (300x60 kutuya sigar): ikon + "Köprü" yazisi, seffaf zemin
$adMetni = [string]::new([char[]]@(0x4B, 0xF6, 0x70, 0x72, 0xFC))
foreach ($tema in @(@{ ad = 'logo_light.png'; renk = '#0F172A' }, @{ ad = 'logo_dark.png'; renk = '#F8FAFC' })) {
    $lb = New-Object System.Drawing.Bitmap 345, 120
    $lg = [System.Drawing.Graphics]::FromImage($lb); $lg.SmoothingMode = 'AntiAlias'; $lg.TextRenderingHint = 'AntiAliasGridFit'
    $lg.Clear([System.Drawing.Color]::Transparent)
    $lg.DrawImage((Ciz-Logo 104), 8, 8, 104, 104)
    $lf = New-Object System.Drawing.Font 'Segoe UI Semibold', 54
    $lg.DrawString($adMetni, $lf, (New-Object System.Drawing.SolidBrush ([System.Drawing.ColorTranslator]::FromHtml($tema.renk))), 128, 10)
    $lg.Dispose()
    $lb.Save((Join-Path $cikis $tema.ad), [System.Drawing.Imaging.ImageFormat]::Png)
}

# Onizleme: logo + ad
$on = New-Object System.Drawing.Bitmap 900, 300
$g = [System.Drawing.Graphics]::FromImage($on); $g.SmoothingMode = 'AntiAlias'; $g.TextRenderingHint = 'AntiAliasGridFit'
$g.Clear([System.Drawing.ColorTranslator]::FromHtml('#F8FAFC'))
$g.DrawImage((Ciz-Logo 200), 50, 50, 200, 200)
$yazi = New-Object System.Drawing.Font 'Segoe UI Semibold', 72
$g.DrawString([string]::new([char[]]@(0x4B,0xF6,0x70,0x72,0xFC)), $yazi, (New-Object System.Drawing.SolidBrush ([System.Drawing.ColorTranslator]::FromHtml('#0F172A'))), 290, 70)
$alt = New-Object System.Drawing.Font 'Segoe UI', 22
$g.DrawString('Uzak Masaustu', $alt, (New-Object System.Drawing.SolidBrush ([System.Drawing.ColorTranslator]::FromHtml('#64748B'))), 300, 180)
foreach ($i in 0..3) { $kb = @(16, 32, 48, 64)[$i]; $g.DrawImage((Ciz-Logo $kb), 600 + $i * 0 + @(0, 30, 75, 135)[$i], 200 - $kb / 2 + 40, $kb, $kb) }
$g.Dispose()
$on.Save((Join-Path $PSScriptRoot 'onizleme.png'), [System.Drawing.Imaging.ImageFormat]::Png)
Get-ChildItem $cikis, (Join-Path $PSScriptRoot 'onizleme.png') | Select-Object Name, Length
