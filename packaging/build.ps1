# Build the full Windows installer staging tree.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File packaging\build.ps1
#   powershell -ExecutionPolicy Bypass -File packaging\build.ps1 -Version 0.5.0 -AllowWingetInstall
#
# Output layout (packaging\staging):
#   app\  python\  tools\  models\  launcher\  BUILD_INFO.txt

param(
    [string]$Version = "0.5.0",
    [string]$StageRoot = "",
    [string]$BasePython = "python",
    [switch]$AllowWingetInstall,
    [switch]$SkipDeps,
    [switch]$SkipPython,
    [switch]$SkipModel,
    [switch]$SkipLauncher,
    [switch]$SkipClean,
    [switch]$ResumePython,
    [switch]$BuildInstaller
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "_common.ps1")

$ProjectRoot = Get-ProjectRoot
Set-Location $ProjectRoot

if (-not $StageRoot) {
    $StageRoot = Get-DefaultStageRoot
}
$StageRoot = (Resolve-Path -LiteralPath (New-Item -ItemType Directory -Path $StageRoot -Force)).Path

Write-Host "Data Room Organizer - installer staging build v$Version"
Write-Host "Stage root: $StageRoot"

if (-not $SkipClean -and (Test-Path $StageRoot)) {
    Write-StageStep "Cleaning previous staging tree"
    Remove-Item $StageRoot -Recurse -Force
    Ensure-Directory $StageRoot
}

$stageApp = Join-Path $PSScriptRoot "stage_app.ps1"
$stageDeps = Join-Path $PSScriptRoot "stage_deps.ps1"
$stagePython = Join-Path $PSScriptRoot "stage_python.ps1"
$stageModel = Join-Path $PSScriptRoot "stage_model.ps1"
$buildLauncher = Join-Path $PSScriptRoot "build_launcher.ps1"

& $stageApp -StageRoot $StageRoot

if (-not $SkipDeps) {
    $depsArgs = @{ StageRoot = $StageRoot }
    if ($AllowWingetInstall) { $depsArgs.AllowWingetInstall = $true }
    & $stageDeps @depsArgs
} else {
    Write-Host "Skipping tool staging (-SkipDeps)"
}

if (-not $SkipPython) {
    $pythonArgs = @{ StageRoot = $StageRoot; BasePython = $BasePython }
    if ($ResumePython) { $pythonArgs.Resume = $true }
    & $stagePython @pythonArgs
} else {
    Write-Host "Skipping Python staging (-SkipPython)"
}

if (-not $SkipModel) {
    if ($SkipPython) {
        throw "-SkipModel requires staged Python. Remove -SkipPython or run stage_model.ps1 separately."
    }
    & $stageModel -StageRoot $StageRoot
} else {
    Write-Host "Skipping model staging (-SkipModel)"
}

$launcherDir = Join-Path $StageRoot "launcher"
Ensure-Directory $launcherDir
if (-not $SkipLauncher) {
    Write-StageStep "Building and copying launcher executables"
    & $buildLauncher -SkipInstall
    Copy-Item (Join-Path $PSScriptRoot "dist\*.exe") $launcherDir -Force
} else {
    Write-Host "Skipping launcher build (-SkipLauncher)"
}

$buildInfo = @(
    "AI-Assisted Data Room Organizer"
    "Bundle version: $Version"
    "Built: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    "Stage root: $StageRoot"
    ""
    "Test doctor:"
    ('  python -m dataroom.bundled_launcher --install-root "{0}" --doctor --no-browser' -f $StageRoot)
    ""
    "Test UI:"
    ('  python -m dataroom.bundled_launcher --install-root "{0}"' -f $StageRoot)
    ""
    "Or double-click:"
    "  $($launcherDir)\DataRoomOrganizer.exe"
) -join "`r`n"
Set-Content -Path (Join-Path $StageRoot "BUILD_INFO.txt") -Value $buildInfo -Encoding UTF8

Write-StageStep "Staging complete"
$totalMb = Format-SizeMb (Get-TreeSizeBytes $StageRoot)
Write-Host "Total staged size: $totalMb MB"
if ($BuildInstaller) {
    $buildInstaller = Join-Path $PSScriptRoot "build_installer.ps1"
    & $buildInstaller -Version $Version -StageRoot $StageRoot
} else {
    Write-Host "Next: powershell -ExecutionPolicy Bypass -File packaging\build_installer.ps1"
}
Write-Host ""
Get-ChildItem $StageRoot -Directory | ForEach-Object {
    $dirSize = Format-SizeMb (Get-TreeSizeBytes $_.FullName)
    Write-Host ('  {0,-12} {1,8} MB' -f $_.Name, $dirSize)
}
