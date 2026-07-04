# Pre-download the embedding model into staging/models/huggingface.

param(
    [string]$StageRoot = (Join-Path $PSScriptRoot "staging")
)

. (Join-Path $PSScriptRoot "_common.ps1")
$ModelsDir = Join-Path (Join-Path $StageRoot "models") "huggingface"
$pythonExe = Get-StagedPythonExe -StageRoot $StageRoot

Write-StageStep "Staging embedding model -> $ModelsDir"
if (Test-Path $ModelsDir) {
    Remove-Item $ModelsDir -Recurse -Force
}
Ensure-Directory $ModelsDir

$env:HF_HOME = $ModelsDir
$env:TRANSFORMERS_CACHE = $ModelsDir
$env:HF_HUB_CACHE = $ModelsDir
$env:HF_HUB_DISABLE_SYMLINKS_WARNING = "1"

Write-Host "Downloading all-MiniLM-L6-v2 into bundled cache..."
& $pythonExe -c "from dataroom.models_setup import download_all_models_cli; download_all_models_cli()"

$sizeMb = Format-SizeMb (Get-TreeSizeBytes $ModelsDir)
Write-Host "Model staged ($sizeMb MB) at $ModelsDir"
