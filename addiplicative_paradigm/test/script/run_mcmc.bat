@echo off
chcp 65001 >nul 2>&1
cd /d "C:\Users\languangheng\.qclaw\workspace-tfxjjhfnjialcuju\addiplicative_paradigm\test"
echo ============================================================
echo   Pantheon+ SNe + Planck CMB MCMC  (v5, bilinear + pool)
echo ============================================================
echo.
"D:\Program Files\QClaw\v0.2.29.592\resources\python\python.exe" mcmc_fast_v5.py
echo.
echo ============================================================
echo   Run complete. Scroll up to see all results.
echo ============================================================
pause
