@echo off
chcp 65001 >nul
title ESE Verify 6 - Weak Coupling Constant (N=100000, 20 runs)
cd /d "C:\Users\languangheng\.qclaw\workspace-tfxjjhfnjialcuju\addiplicative_paradigm\test\script\unit"
echo ============================================================
echo ESE Verify 6: Weak Coupling Constant
echo N=100,000, 20 runs, rank-35~55
echo ============================================================
echo.
"C:\Users\languangheng\AppData\Local\Python\pythoncore-3.14-64\python.exe" verify_weak_coupling.py
echo.
echo ============================================================
echo DONE! Close this window when ready.
echo ============================================================
pause
