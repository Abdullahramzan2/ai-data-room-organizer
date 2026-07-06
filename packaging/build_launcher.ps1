# Build PyInstaller launchers for bundled installs.
# Output: packaging/dist/DataRoomOrganizer.exe, packaging/dist/DataRoomDoctor.exe

param(
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    $Python = "python"
}

if (-not $SkipInstall) {
    Write-Host "Installing PyInstaller..."
    & $Python -m pip install pyinstaller --quiet
}

$dist = Join-Path $PSScriptRoot "dist"
$build = Join-Path $PSScriptRoot "build"
if (Test-Path $dist) { Remove-Item $dist -Recurse -Force }
if (Test-Path $build) { Remove-Item $build -Recurse -Force }

Write-Host "Building DataRoomOrganizer.exe (UI, no console)..."
& $Python -m PyInstaller (Join-Path $PSScriptRoot "launcher.spec") `
    --noconfirm --clean `
    --distpath $dist `
    --workpath $build

Write-Host "Building DataRoomDoctor.exe (doctor, console)..."
& $Python -m PyInstaller (Join-Path $PSScriptRoot "launcher_doctor.spec") `
    --noconfirm --clean `
    --distpath $dist `
    --workpath (Join-Path $build "doctor")

Write-Host ""
Write-Host "Done:"
if (Test-Path $dist) {
    Get-ChildItem $dist -Filter "*.exe" | ForEach-Object {
        $sizeMb = [math]::Round($_.Length / 1MB, 2)
        Write-Host "  $($_.FullName) ($sizeMb MB)"
    }
} else {
    Write-Host "  No executables produced. Check PyInstaller output above."
}
