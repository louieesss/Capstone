# Simple script to run the Pollination Monitoring App
Write-Host "Activating virtual environment..." -ForegroundColor Green
& .\.venv\Scripts\Activate.ps1

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  🐝 POLLINATION MONITORING SYSTEM" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Dashboard: http://localhost:5000" -ForegroundColor Yellow
Write-Host "Report:    http://localhost:5000/report" -ForegroundColor Yellow
Write-Host "Control:   http://localhost:5000/control" -ForegroundColor Yellow
Write-Host ""
Write-Host "Starting Flask app..." -ForegroundColor Green
Write-Host ""

python app.py
