# Run cambc against all maps in separate terminal windows with --watch
$maps_folder = ".\maps"
$maps = Get-ChildItem -Path $maps_folder -Filter "*.map26" | Select-Object -ExpandProperty Name

foreach ($map in $maps) {
    Write-Host "Starting: $map in new terminal" -ForegroundColor Cyan
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cambc run Starter Starterr $map --watch"
    Start-Sleep -Milliseconds 500  # Small delay between opening terminals
}

Write-Host "All maps launched in separate terminals!" -ForegroundColor Green
