# Copy application payload into staging/app.

param(
    [string]$StageRoot = (Join-Path $PSScriptRoot "staging")
)

. (Join-Path $PSScriptRoot "_common.ps1")
$ProjectRoot = Get-ProjectRoot
$AppDir = Join-Path $StageRoot "app"

Write-StageStep "Staging application files -> $AppDir"
if (Test-Path $AppDir) {
    Remove-Item $AppDir -Recurse -Force
}
Ensure-Directory $AppDir

$copyItems = @(
    @{ Source = Join-Path $ProjectRoot "src"; Dest = "src" },
    @{ Source = Join-Path $ProjectRoot "config"; Dest = "config" },
    @{ Source = Join-Path $ProjectRoot "taxonomy"; Dest = "taxonomy" },
    @{ Source = Join-Path $ProjectRoot ".streamlit"; Dest = ".streamlit" }
)
foreach ($item in $copyItems) {
    Copy-Tree -Source $item.Source -Destination (Join-Path $AppDir $item.Dest)
}

$singleFiles = @("pyproject.toml", "README.md", ".env.example")
foreach ($file in $singleFiles) {
    $source = Join-Path $ProjectRoot $file
    if (Test-Path $source) {
        Copy-Item $source (Join-Path $AppDir $file) -Force
    }
}

Write-Host "App staged at $AppDir"
