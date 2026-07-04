# Shared helpers for Windows installer staging scripts.

$ErrorActionPreference = "Stop"

function Get-PackagingRoot {
    return Split-Path -Parent $PSScriptRoot
}

function Get-ProjectRoot {
    return Split-Path -Parent $PSScriptRoot
}

function Get-DefaultStageRoot {
    return Join-Path $PSScriptRoot "staging"
}

function Write-StageStep {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message"
}

function Ensure-Directory {
    param([string]$Path)
    New-Item -ItemType Directory -Path $Path -Force | Out-Null
}

function Copy-Tree {
    param(
        [string]$Source,
        [string]$Destination,
        [string[]]$ExcludeDirs = @("__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache")
    )
    if (-not (Test-Path $Source)) {
        throw "Source path not found: $Source"
    }
    Ensure-Directory $Destination
    $xd = $ExcludeDirs | ForEach-Object { "/XD", $_ }
    robocopy $Source $Destination /E /NFL /NDL /NJH /NJS /nc /ns /np @xd | Out-Null
    if ($LASTEXITCODE -ge 8) {
        throw "robocopy failed ($LASTEXITCODE) copying $Source -> $Destination"
    }
}

function Find-TesseractInstall {
    $candidates = @(
        "${env:ProgramFiles}\Tesseract-OCR",
        "${env:ProgramFiles(x86)}\Tesseract-OCR"
    )
    foreach ($path in $candidates) {
        if (Test-Path (Join-Path $path "tesseract.exe")) {
            return $path
        }
    }
    return $null
}

function Find-PopplerInstall {
    $candidates = @(
        "${env:ProgramFiles}\poppler\Library\bin",
        "${env:ProgramFiles}\poppler-24.08.0\Library\bin",
        "C:\poppler\Library\bin"
    )
    foreach ($path in $candidates) {
        if (Test-Path (Join-Path $path "pdftoppm.exe")) {
            return (Split-Path -Parent (Split-Path -Parent $path))
        }
    }
    $wingetRoot = Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Packages"
    if (Test-Path $wingetRoot) {
        $match = Get-ChildItem $wingetRoot -Directory -Filter "oschwartz10612.Poppler_*" -ErrorAction SilentlyContinue |
            Sort-Object Name -Descending |
            Select-Object -First 1
        if ($match) {
            $popplerRoot = Join-Path $match.FullName "poppler-*"
            $resolved = Get-ChildItem $match.FullName -Directory -Filter "poppler-*" -ErrorAction SilentlyContinue |
                Select-Object -First 1
            if ($resolved -and (Test-Path (Join-Path $resolved.FullName "Library\bin\pdftoppm.exe"))) {
                return $resolved.FullName
            }
        }
    }
    return $null
}

function Find-LibreOfficeInstall {
    $candidates = @(
        "${env:ProgramFiles}\LibreOffice",
        "${env:ProgramFiles(x86)}\LibreOffice"
    )
    foreach ($path in $candidates) {
        if (Test-Path (Join-Path $path "program\soffice.exe")) {
            return $path
        }
    }
    return $null
}

function Ensure-WingetPackage {
    param(
        [string]$Name,
        [string]$WingetId
    )
    $null = Get-Command winget -ErrorAction SilentlyContinue
    if (-not $?) {
        throw "winget is required to install $Name automatically. Install $Name manually, then rerun."
    }
    Write-Host "Installing $Name via winget ($WingetId)..."
    winget install --id $WingetId --accept-package-agreements --accept-source-agreements --silent
}

function Get-StagedPythonExe {
    param([string]$StageRoot)
    $candidates = @(
        (Join-Path $StageRoot "python\Scripts\python.exe"),
        (Join-Path $StageRoot "python\python.exe")
    )
    foreach ($path in $candidates) {
        if (Test-Path $path) {
            return $path
        }
    }
    throw "Staged Python not found under $StageRoot\python"
}

function Format-SizeMb {
    param([long]$Bytes)
    return [math]::Round($Bytes / 1MB, 2)
}

function Get-TreeSizeBytes {
    param([string]$Path)
    if (-not (Test-Path $Path)) { return 0 }
    return (Get-ChildItem $Path -Recurse -File -ErrorAction SilentlyContinue |
        Measure-Object -Property Length -Sum).Sum
}
