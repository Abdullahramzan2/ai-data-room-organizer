# Stop Data Room Organizer processes before reinstalling or uninstalling.
# Usage: powershell -ExecutionPolicy Bypass -File packaging\stop_dataroom.ps1

$ErrorActionPreference = "SilentlyContinue"

Write-Host "Stopping Data Room Organizer processes..."

$names = @("DataRoomOrganizer", "DataRoomDoctor", "streamlit", "python", "pythonw")
foreach ($name in $names) {
    Get-Process -Name $name | ForEach-Object {
        $cmd = $_.Path
        if (
            $cmd -and (
                $cmd -match "AI Data Room Organizer" -or
                $cmd -match "Data Room Organizer" -or
                $cmd -match "packaging\\test-install" -or
                $cmd -match "packaging\\staging"
            )
        ) {
            Write-Host "  Stopping $name (PID $($_.Id)): $cmd"
            Stop-Process -Id $_.Id -Force
        }
    }
}

Start-Sleep -Seconds 2
Write-Host "Done. You can now uninstall or reinstall the application."
