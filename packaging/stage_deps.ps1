# Bundle Tesseract, Poppler, and LibreOffice into staging/tools.

param(
    [string]$StageRoot = (Join-Path $PSScriptRoot "staging"),
    [switch]$AllowWingetInstall
)

. (Join-Path $PSScriptRoot "_common.ps1")
$ToolsDir = Join-Path $StageRoot "tools"
Write-StageStep "Staging external tools -> $ToolsDir"

if (Test-Path $ToolsDir) {
    Remove-Item $ToolsDir -Recurse -Force
}
Ensure-Directory $ToolsDir

function Stage-ToolTree {
    param(
        [string]$Source,
        [string]$RelativeDest
    )
    $dest = Join-Path $ToolsDir $RelativeDest
    if (Test-Path $dest) {
        Remove-Item $dest -Recurse -Force
    }
    Copy-Tree -Source $Source -Destination $dest
    Write-Host "  staged $RelativeDest"
}

# Tesseract
$tesseract = Find-TesseractInstall
if (-not $tesseract -and $AllowWingetInstall) {
    Ensure-WingetPackage -Name "Tesseract OCR" -WingetId "UB-Mannheim.TesseractOCR"
    $tesseract = Find-TesseractInstall
}
if (-not $tesseract) {
    throw "Tesseract not found. Install with: winget install --id UB-Mannheim.TesseractOCR"
}
Stage-ToolTree -Source $tesseract -RelativeDest "tesseract"

# Poppler (preserve Library/bin layout)
$poppler = Find-PopplerInstall
if (-not $poppler -and $AllowWingetInstall) {
    Ensure-WingetPackage -Name "Poppler" -WingetId "oschwartz10612.Poppler"
    $poppler = Find-PopplerInstall
}
if (-not $poppler) {
    throw "Poppler not found. Install with: winget install --id oschwartz10612.Poppler"
}
Stage-ToolTree -Source $poppler -RelativeDest "poppler"

# LibreOffice
$libreOffice = Find-LibreOfficeInstall
if (-not $libreOffice -and $AllowWingetInstall) {
    Ensure-WingetPackage -Name "LibreOffice" -WingetId "TheDocumentFoundation.LibreOffice"
    $libreOffice = Find-LibreOfficeInstall
}
if (-not $libreOffice) {
    throw "LibreOffice not found. Install with: winget install --id TheDocumentFoundation.LibreOffice"
}
Stage-ToolTree -Source $libreOffice -RelativeDest "libreoffice"

$sizeMb = Format-SizeMb (Get-TreeSizeBytes $ToolsDir)
Write-Host "Tools staged ($sizeMb MB) at $ToolsDir"
