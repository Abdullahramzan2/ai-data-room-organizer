# Create an embedded Python environment under staging/python.

param(
    [string]$StageRoot = (Join-Path $PSScriptRoot "staging"),
    [string]$BasePython = "python",
    [switch]$Resume
)

. (Join-Path $PSScriptRoot "_common.ps1")
$ProjectRoot = Get-ProjectRoot
$PythonDir = Join-Path $StageRoot "python"
$AppDir = Join-Path $StageRoot "app"

Write-StageStep "Staging Python environment -> $PythonDir"

if (-not (Test-Path (Join-Path $AppDir "pyproject.toml"))) {
    throw "App payload missing at $AppDir. Run packaging/stage_app.ps1 first."
}

$pythonExe = $null
if ($Resume -and (Test-Path $PythonDir)) {
    Write-Host "Resuming existing staged Python environment..."
    $pythonExe = Get-StagedPythonExe -StageRoot $StageRoot
} else {
    if (Test-Path $PythonDir) {
        Remove-Item $PythonDir -Recurse -Force
    }
    Write-Host "Creating virtual environment with $BasePython ..."
    & $BasePython -m venv $PythonDir
    $pythonExe = Get-StagedPythonExe -StageRoot $StageRoot
    Write-Host "Upgrading pip..."
    & $pythonExe -m pip install --upgrade pip wheel setuptools
}

$pipExe = Join-Path $PythonDir "Scripts\pip.exe"

Write-Host "Installing dataroom package with [ui,windows] extras (this may take several minutes)..."
& $pipExe install -e "${AppDir}[ui,windows]"

Write-Host "Verifying package import..."
& $pythonExe -c "import dataroom; print('dataroom import OK')"

$sizeMb = Format-SizeMb (Get-TreeSizeBytes $PythonDir)
Write-Host "Python staged ($sizeMb MB) at $PythonDir"
