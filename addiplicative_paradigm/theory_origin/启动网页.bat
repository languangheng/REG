@echo off
chcp 65001 >nul
echo ====================
echo 理论起源网页 - 快速启动
echo ====================
echo.
echo 选择启动方式:
echo [1] 直接用默认浏览器打开
echo [2] 启动本地服务器 (Python)
echo [3] 退出
echo.
set /p choice=请输入选项 (1-3): 

if "%choice%"=="1" (
    start theory_origin.html
    echo 已在浏览器中打开...
    pause
) else if "%choice%"=="2" (
    echo.
    echo 启动本地服务器...
    echo 请在浏览器中访问: http://localhost:8000/theory_origin.html
    echo 按 Ctrl+C 停止服务器
    echo.
    python -m http.server 8000
) else if "%choice%"=="3" (
    exit
) else (
    echo 无效选项！
    pause
    goto :EOF
)
