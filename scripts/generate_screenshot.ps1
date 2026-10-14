Add-Type -AssemblyName System.Drawing

$targetPath = "c:\Users\priya\Downloads\TriagePilot-main\TriagePilot-main\data\bundles\S06\screenshot.png"

$width = 720
$height = 360
$bmp = New-Object System.Drawing.Bitmap $width, $height
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
$g.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::ClearTypeGridFit

# Background
$bgBrush = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(248, 249, 250))
$g.FillRectangle($bgBrush, 0, 0, $width, $height)

# Modal Card
$cardX = 40
$cardY = 30
$cardW = 640
$cardH = 300
$cardBrush = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::White)
$cardPen = New-Object System.Drawing.Pen ([System.Drawing.Color]::FromArgb(222, 226, 230), 2)
$g.FillRectangle($cardBrush, $cardX, $cardY, $cardW, $cardH)
$g.DrawRectangle($cardPen, $cardX, $cardY, $cardW, $cardH)

# Title Bar
$barBrush = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(241, 243, 245))
$g.FillRectangle($barBrush, $cardX, $cardY, $cardW, 45)
$titleFont = New-Object System.Drawing.Font("Segoe UI", 11, [System.Drawing.FontStyle]::Bold)
$titleBrush = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(73, 80, 87))
$g.DrawString("Bank Retail Fund Transfer Portal", $titleFont, $titleBrush, [float]($cardX + 16), [float]($cardY + 12))

# Alert Box
$alertBgBrush = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(255, 245, 245))
$alertBorderPen = New-Object System.Drawing.Pen ([System.Drawing.Color]::FromArgb(255, 192, 192), 1)
$g.FillRectangle($alertBgBrush, [float]($cardX + 20), [float]($cardY + 65), [float]($cardW - 40), [float]140)
$g.DrawRectangle($alertBorderPen, [float]($cardX + 20), [float]($cardY + 65), [float]($cardW - 40), [float]140)

# Red Icon circle
$iconBrush = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(224, 49, 49))
$g.FillEllipse($iconBrush, [float]($cardX + 40), [float]($cardY + 85), [float]36, [float]36)
$xFont = New-Object System.Drawing.Font("Segoe UI", 16, [System.Drawing.FontStyle]::Bold)
$whiteBrush = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::White)
$g.DrawString("X", $xFont, $whiteBrush, [float]($cardX + 49), [float]($cardY + 87))

# Error Headline
$errHeadFont = New-Object System.Drawing.Font("Segoe UI", 12, [System.Drawing.FontStyle]::Bold)
$errHeadBrush = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(201, 42, 42))
$g.DrawString("Transaction Blocked - Limit Validation", $errHeadFont, $errHeadBrush, [float]($cardX + 90), [float]($cardY + 80))

# Error Message (Key target for vision model OCR)
$errMsgFont = New-Object System.Drawing.Font("Segoe UI", 11, [System.Drawing.FontStyle]::Regular)
$errMsgBrush = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(33, 37, 41))
$msg = "Error: Daily limit of INR 1,00,000 exceeded for request of INR 1,00,000.00"
$g.DrawString($msg, $errMsgFont, $errMsgBrush, [float]($cardX + 90), [float]($cardY + 110))

# Reference Detail
$metaFont = New-Object System.Drawing.Font("Segoe UI", 9, [System.Drawing.FontStyle]::Regular)
$metaBrush = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(108, 117, 125))
$g.DrawString("Reference: TXN-6001 | Account: [ACCT_REDACTED] | Timestamp: 2026-10-14 14:09:55 IST", $metaFont, $metaBrush, [float]($cardX + 90), [float]($cardY + 145))
$g.DrawString("Rule: Cumulative Retail Volume Policy (DOC-LIMITS-01)", $metaFont, $metaBrush, [float]($cardX + 90), [float]($cardY + 165))

# Action Buttons
$btnBrush = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(220, 53, 69))
$g.FillRectangle($btnBrush, [float]($cardX + $cardW - 160), [float]($cardY + 230), [float]130, [float]36)
$btnFont = New-Object System.Drawing.Font("Segoe UI", 10, [System.Drawing.FontStyle]::Bold)
$g.DrawString("Back to Home", $btnFont, $whiteBrush, [float]($cardX + $cardW - 145), [float]($cardY + 238))

# Save
$bmp.Save($targetPath, [System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose()
$bmp.Dispose()
Write-Host "Generated screenshot at $targetPath"
