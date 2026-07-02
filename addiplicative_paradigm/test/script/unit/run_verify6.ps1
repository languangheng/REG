cd "C:\Users\languangheng\.qclaw\workspace-tfxjjhfnjialcuju\addiplicative_paradigm\test\script\unit"
$env:PYTHONIOENCODING = "utf-8"
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "ESE Verify 6: Weak Coupling Constant" -ForegroundColor Cyan
Write-Host "N=100,000, 20 runs, rank-35~55" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Starting simulations... (this will take a while)" -ForegroundColor Yellow
Write-Host ""

python verify_weak_coupling.py

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "DONE! Close this window when ready." -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Read-Host "Press Enter to close"
