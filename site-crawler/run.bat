@echo off
chcp 65001 >nul
echo 正在启动 Site Crawler...
echo.
python "%~dp0start.py"
pause
