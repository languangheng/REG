# start_site_manager.ps1 - 智能启动/重启 site_manager.py
# 用法: .\start_site_manager.ps1 [-Port 5050] [-NoRebuild]

param(
    [int]$Port = 5050,
    [string]$Script = "site_manager.py"
)

$ErrorActionPreference = "Stop"
$workdir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $workdir

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Site Crawler Manager - 启动脚本" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ── 1. 检查端口是否被占用 ──────────────────────────
function Get-ProcessOnPort($port) {
    $netstat = netstat -ano | Select-String ":$port\s"
    foreach ($line in $netstat) {
        $parts = $line.Line -split '\s+'
        # 格式:  TCP    0.0.0.0:5050    0.0.0.0:0    LISTENING   12345
        if ($parts -contains "LISTENING") {
            $pidPart = $parts[-1]
            try { return Get-Process -Id $pidPart -ErrorAction SilentlyContinue } catch {}
        }
    }
    return $null
}

$existingProc = Get-ProcessOnPort -port $Port
if ($existingProc) {
    Write-Host "⚠️  端口 $Port 已被进程占用:" -ForegroundColor Yellow
    Write-Host "    PID: $($existingProc.Id)  |  进程: $($existingProc.ProcessName)  |  启动时间: $($existingProc.StartTime)"
    Write-Host "    → 正在终止旧进程..." -ForegroundColor Yellow
    try {
        Stop-Process -Id $existingProc.Id -Force
        Start-Sleep -Seconds 2
        # 确认已停止
        $check = Get-Process -Id $existingProc.Id -ErrorAction SilentlyContinue
        if ($check) {
            Write-Host "    ❌ 无法终止进程 (PID $($existingProc.Id))，请手动检查" -ForegroundColor Red
            exit 1
        }
        Write-Host "    ✅ 旧进程已终止" -ForegroundColor Green
    } catch {
        Write-Host "    ❌ 终止失败: $_" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "✅ 端口 $Port 未被占用" -ForegroundColor Green
}

# ── 2. 清理 __pycache__ ─────────────────────────────
Write-Host "🧹 清理 __pycache__..." -ForegroundColor Gray
Get-ChildItem -Path $workdir -Recurse -Directory -Filter "__pycache__" | ForEach-Object {
    Remove-Item $_.FullName -Recurse -Force -ErrorAction SilentlyContinue
}
Write-Host "    ✅ 缓存已清理" -ForegroundColor Green

# ── 3. 启动服务 ─────────────────────────────────────
Write-Host "🚀 启动 $Script ..." -ForegroundColor Cyan
$env:PYTHONIOENCODING = "utf-8"
$proc = Start-Process -FilePath "python" -ArgumentList $Script -WorkingDirectory $workdir -PassThru -WindowStyle Hidden

if (-not $proc) {
    Write-Host "    ❌ 启动失败" -ForegroundColor Red
    exit 1
}
Write-Host "    新进程 PID: $($proc.Id)" -ForegroundColor Gray

# ── 4. 等待服务就绪 ─────────────────────────────────
Write-Host "⏳ 等待服务就绪 (端口 $Port)..." -ForegroundColor Gray
$maxWait = 15
$waited = 0
$ready = $false
while ($waited -lt $maxWait) {
    Start-Sleep -Seconds 1
    $waited++
    try {
        $resp = Invoke-WebRequest -Uri "http://localhost:$Port/api/sites" -UseBasicParsing -TimeoutSec 2
        if ($resp.StatusCode -eq 200) {
            $ready = $true
            break
        }
    } catch {}
    Write-Host "    [$waited/$maxWait s] 等待中..." -ForegroundColor DarkGray
}

if (-not $ready) {
    Write-Host "    ❌ 服务启动超时（${maxWait}s）" -ForegroundColor Red
    Write-Host "    请检查 $Script 是否报错" -ForegroundColor Yellow
    exit 1
}

# ── 5. 验证 ──────────────────────────────────────────
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  ✅ 服务已启动" -ForegroundColor Green
Write-Host "  URL : http://localhost:$Port" -ForegroundColor Green
Write-Host "  PID : $($proc.Id)" -ForegroundColor Gray
Write-Host "  缓存: 已清理 (__pycache__)" -ForegroundColor Gray
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# 打开浏览器（可选）
$openBrowser = Read-Host "是否打开浏览器？(Y/N)"
if ($openBrowser -eq "Y" -or $openBrowser -eq "y") {
    Start-Process "http://localhost:$Port"
}
