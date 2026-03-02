$git = "C:\Program Files\Git\bin\git.exe"
Set-Location "C:\Users\Admin\Desktop\CAPS"

Write-Host "=== Step 1: Configure git user ===" -ForegroundColor Cyan
& $git config user.email "louieesss@github.com"
& $git config user.name "louieesss"

Write-Host "=== Step 2: Staging files ===" -ForegroundColor Cyan
& $git add .
Write-Host "Add exit code: $LASTEXITCODE"

Write-Host "=== Step 3: Git status ===" -ForegroundColor Cyan
& $git status --short | Select-Object -First 5

Write-Host "=== Step 4: Commit ===" -ForegroundColor Cyan
& $git commit -m "Initial commit - Pollination Monitoring System"
Write-Host "Commit exit code: $LASTEXITCODE"

Write-Host "=== Step 5: Add remote ===" -ForegroundColor Cyan
& $git remote remove origin 2>$null
& $git remote add origin "https://github.com/louieesss/Capstone.git"

Write-Host "=== Step 6: Push ===" -ForegroundColor Cyan
& $git branch -M main
& $git push -u origin main
Write-Host "Push exit code: $LASTEXITCODE"
