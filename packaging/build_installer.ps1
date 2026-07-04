# Compile the Windows installer with Inno Setup 6.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File packaging\build_installer.ps1
#   powershell -ExecutionPolicy Bypass -File packaging\build_installer.ps1 -Version 0.5.0
#
# Output: packaging\dist\AI-Data-Room-Organizer-Setup.exe

param(
    [string]$Version = "0.5.0",
    [string]$StageRoot = "",
    [string]$IsccPath = ""
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "_common.ps1")

$ProjectRoot = Get-ProjectRoot
Set-Location $PSScriptRoot

if (-not $StageRoot) {
    $StageRoot = Get-DefaultStageRoot
}
if (-not (Test-Path $StageRoot)) {
    throw "Staging folder not found: $StageRoot. Run packaging\build.ps1 first."
}

$required = @("app", "python", "tools", "models", "launcher")
foreach ($name in $required) {
    $path = Join-Path $StageRoot $name
    if (-not (Test-Path $path)) {
        throw "Staging incomplete: missing $path. Run packaging\build.ps1 first."
    }
}

$launcherExe = Join-Path $StageRoot "launcher\DataRoomOrganizer.exe"
if (-not (Test-Path $launcherExe)) {
    throw "Launcher not found: $launcherExe. Re-run packaging\build.ps1 without -SkipLauncher."
}

if (-not $IsccPath) {
    $candidates = @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
    )
    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) {
            $IsccPath = $candidate
            break
        }
    }
}
if (-not $IsccPath -or -not (Test-Path $IsccPath)) {
    throw "Inno Setup 6 compiler (ISCC.exe) not found. Install from https://jrsoftware.org/isinfo.php"
}

$iss = Join-Path $PSScriptRoot "installer.iss"
$dist = Join-Path $PSScriptRoot "dist"
Ensure-Directory $dist

Write-StageStep "Compiling installer v$Version"
Write-Host "Staging: $StageRoot"
Write-Host "Compiler: $IsccPath"

& $IsccPath $iss "/DAppVersion=$Version"

$setupExe = Join-Path $dist "AI-Data-Room-Organizer-Setup.exe"
if (-not (Test-Path $setupExe)) {
    throw "Installer build failed: $setupExe was not created."
}

$sizeMb = Format-SizeMb (Get-Item $setupExe).Length
Write-Host ""
Write-Host "Installer ready:"
Write-Host "  $setupExe ($sizeMb MB)"
Write-Host ""
Write-Host "Test install locally, then upload this file for Carl."
