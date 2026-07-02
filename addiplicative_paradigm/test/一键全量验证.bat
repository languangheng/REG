@echo off
chcp 65001 >nul 2>&1
title REG: 关系涌现引力论 - 全量验证
cd /d "%~dp0"

echo ============================================================
echo   REG: 关系涌现引力论 - 一键全量验证
echo   Relational Emergent Gravity - One-Click Full Validation
echo ============================================================
echo.
echo   Directory: %CD%
echo   Checking dependencies -> auto-install
echo   Running 6 core scripts sequentially
echo   Auto-generating SUMMARY.md
echo.
echo ============================================================
echo.

"D:\Program Files\QClaw\v0.2.29.592\resources\python\python.exe" run_all.py

echo.
echo ============================================================
echo   Done. Check output above and SUMMARY.md
echo ============================================================
pause
