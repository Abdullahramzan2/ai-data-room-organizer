# Create a local bundled-layout test tree under packaging/dev-install.
# Double-click: packaging\dev-install\launcher\DataRoomOrganizer.exe
# (Do NOT run the copy in packaging\dist\ — that folder has no app/python payload.)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$DevInstall = Join-Path $PSScriptRoot "dev-install"
$App = Join-Path $DevInstall "app"
$Launcher = Join-Path $DevInstall "launcher"
$Python = Join-Path $DevInstall "python"
$Tools = Join-Path $DevInstall "tools"
$Models = Join-Path (Join-Path $DevInstall "models") "huggingface"

if (Test-Path $DevInstall) {
    Remove-Item $DevInstall -Recurse -Force
}

New-Item -ItemType Directory -Path $App, $Launcher, $Tools, $Models -Force | Out-Null

Copy-Item (Join-Path $Root "config") (Join-Path $App "config") -Recurse
Copy-Item (Join-Path $Root "taxonomy") (Join-Path $App "taxonomy") -Recurse
Copy-Item (Join-Path $Root ".streamlit") (Join-Path $App ".streamlit") -Recurse
Copy-Item (Join-Path $Root ".env.example") (Join-Path $App ".env.example")

$Venv = Join-Path $Root ".venv"
if (-not (Test-Path (Join-Path $Venv "Scripts\python.exe"))) {
    throw "Project venv not found. Run: python -m venv .venv; pip install -e `".[ui]`""
}
cmd /c mklink /J "$Python" "$Venv" | Out-Null

$Dist = Join-Path $PSScriptRoot "dist"
if (-not (Test-Path (Join-Path $Dist "DataRoomOrganizer.exe"))) {
    Write-Host "Building launchers..."
    & (Join-Path $PSScriptRoot "build_launcher.ps1") -SkipInstall
}
if (Test-Path $Dist) {
    Copy-Item (Join-Path $Dist "*.exe") $Launcher -Force
}

New-Item -ItemType Directory -Path (Join-Path $Tools "tesseract") -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $Tools "poppler\Library\bin") -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $Tools "libreoffice\program") -Force | Out-Null

$LauncherExe = Join-Path $Launcher "DataRoomOrganizer.exe"
Write-Host ""
Write-Host "Dev install ready."
Write-Host "Double-click this file to launch the UI:"
Write-Host "  $LauncherExe"
Write-Host ""
Write-Host "CLI test:"
Write-Host "  python -m dataroom.bundled_launcher --install-root `"$DevInstall`" --doctor --no-browser"
