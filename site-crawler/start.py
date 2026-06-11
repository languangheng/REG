#!/usr/bin/env python3
"""Site Crawler - One-click startup script
环境检查 -> 自动安装 -> 启动服务
"""

import os
import sys
import io
import time
import subprocess
import urllib.request
import urllib.error
import socket
from pathlib import Path

# 修复 Windows 控制台编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

PROJECT_DIR = Path(__file__).parent
PORT = 5050
MIN_PYTHON = (3, 12)

# ── 输出函数 (纯 ASCII) ──────────────────
def info(msg): print(f"\033[36m[*]\033[0m {msg}")   # cyan
def ok(msg):   print(f"\033[32m[+]\033[0m {msg}")   # green
def warn(msg): print(f"\033[33m[!]\033[0m {msg}")    # yellow
def err(msg):  print(f"\033[31m[x]\033[0m {msg}")    # red
def step(msg): print(f"\n\033[35m[>]\033[0m {msg}")   # magenta


# ── 运行命令 ──────────────────────────────
def run(cmd, capture=False):
    """运行命令，返回 (returncode, stdout, stderr)"""
    try:
        r = subprocess.run(
            cmd if isinstance(cmd, (list, tuple)) else cmd.split(),
            capture_output=capture,
            text=True,
            shell=False,
        )
        return r.returncode, r.stdout or "", r.stderr or ""
    except Exception as e:
        return -1, "", str(e)


# ── 检查端口 ──────────────────────────────
def is_port_free(port):
    try:
        s = socket.socket()
        s.connect(("127.0.0.1", port))
        s.close()
        return False
    except Exception:
        return True


# ── 检查 Python 版本 ─────────────────────
def check_python():
    step("检查 Python 环境...")
    code, out, _ = run([sys.executable, "--version"], capture=True)
    if code != 0:
        warn("Python 不可用")
        return False
    import re
    m = re.search(r"(\d+)\.(\d+)", out)
    if not m:
        warn(f"无法解析版本: {out.strip()}")
        return False
    major, minor = int(m.group(1)), int(m.group(2))
    info(f"检测到 Python {major}.{minor}")
    if (major, minor) >= MIN_PYTHON:
        ok(f"Python 版本满足要求 (>= {MIN_PYTHON[0]}.{MIN_PYTHON[1]})")
        return True
    else:
        warn(f"Python 版本过低: {major}.{minor} (需要 {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+)")
        return False


# ── 安装 Python ──────────────────────────
def install_python():
    step("安装 Python 3.12+...")
    if os.name == "nt":
        code, _, _ = run("winget install -e --id Python.Python.3.12 -q")
        if code == 0:
            ok("Python 安装完成，请重启终端后重新运行此脚本")
        else:
            err("Python 安装失败，请手动下载: https://www.python.org/downloads/")
    else:
        err("请手动安装 Python 3.12+: https://www.python.org/downloads/")
    sys.exit(0)


# ── 检查 uv ──────────────────────────────
def check_uv():
    step("检查 uv 包管理器...")
    code, _, _ = run("uv --version", capture=True)
    if code == 0:
        ok("uv 已安装")
        return True
    warn("uv 未安装")
    return False


# ── 安装 uv ──────────────────────────────
def install_uv():
    step("安装 uv...")
    try:
        if os.name == "nt":
            url = "https://astral.sh/uv/install.ps1"
            script_content = urllib.request.urlopen(url, timeout=10).read().decode("utf-8")
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".ps1", delete=False, mode="w") as f:
                f.write(script_content)
                ps1_path = f.name
            try:
                subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File", ps1_path], check=True)
                ok("uv 安装完成")
            finally:
                os.unlink(ps1_path)
        else:
            subprocess.run("curl -LsSf https://astral.sh/uv/install.sh | sh", shell=True, check=True)
            ok("uv 安装完成")
    except Exception as e:
        err(f"uv 安装失败: {e}")
        err("请手动安装: https://docs.astral.sh/uv/getting-started/installation/")
        sys.exit(1)


# ── 检查 browser-act CLI ───────────────────
def check_browser_act():
    step("检查 browser-act CLI...")
    code, _, _ = run("browser-act --version", capture=True)
    if code == 0:
        ok("browser-act CLI 已安装")
        return True
    # 检查 uv tool list
    code2, out2, _ = run("uv tool list", capture=True)
    if code2 == 0 and "browser-act" in out2:
        ok("browser-act CLI 已安装 (uv tool)")
        return True
    warn("browser-act CLI 未安装")
    return False


# ── 安装 browser-act CLI ───────────────────
def install_browser_act():
    step("安装 browser-act CLI...")
    code, _, err_msg = run("uv tool install browser-act-cli --python 3.12", capture=True)
    if code == 0:
        ok("browser-act CLI 安装完成")
    else:
        err(f"browser-act CLI 安装失败: {err_msg}")
        sys.exit(1)


# ── 检查 Python 依赖 ─────────────────────
def check_python_deps():
    step("检查 Python 依赖 (flask, pyyaml)...")
    missing = []
    for pkg in ["flask", "yaml"]:
        code, _, _ = run([sys.executable, "-c", f"import {pkg}"], capture=True)
        if code != 0:
            missing.append(pkg)
        else:
            info(f"  {pkg} OK")
    if not missing:
        ok("所有 Python 依赖已安装")
        return True
    warn(f"缺少依赖: {', '.join(missing)}")
    return False


# ── 安装 Python 依赖 ─────────────────────
def install_python_deps():
    step("安装 Python 依赖...")
    code, _, err_msg = run([sys.executable, "-m", "pip", "install", "flask", "pyyaml", "-q"], capture=True)
    if code == 0:
        ok("Python 依赖安装完成")
    else:
        warn(f"部分依赖安装失败: {err_msg}")


# ── 启动服务 ──────────────────────────────
def start_service():
    step(f"启动 Site Crawler 服务 (端口 {PORT})...")
    if not is_port_free(PORT):
        warn(f"端口 {PORT} 已被占用，尝试打开已有服务...")
        import webbrowser
        webbrowser.open(f"http://localhost:{PORT}")
        return

    os.chdir(PROJECT_DIR)
    info(f"启动 Flask 服务...")
    # 后台启动
    proc = subprocess.Popen(
        [sys.executable, "site_manager.py"],
        cwd=str(PROJECT_DIR),
    )
    # 等待启动
    info("等待服务启动...")
    for i in range(30):
        time.sleep(1)
        sys.stdout.write(".")
        sys.stdout.flush()
        try:
            with urllib.request.urlopen(f"http://localhost:{PORT}", timeout=2) as r:
                if r.status == 200:
                    print("")
                    ok("服务启动成功！")
                    import webbrowser
                    webbrowser.open(f"http://localhost:{PORT}")
                    return
        except Exception:
            pass
    print("")
    warn("服务启动超时，请检查 site_manager.py 日志")
    info(f"手动访问: http://localhost:{PORT}")


# ── 主流程 ──────────────────────────────────
def main():
    print("\n" + "=" * 50)
    print("  Site Crawler 启动脚本")
    print("=" * 50 + "\n")

    if not check_python():
        install_python()

    if not check_uv():
        install_uv()

    if not check_browser_act():
        install_browser_act()

    if not check_python_deps():
        install_python_deps()

    start_service()

    print("\n" + "=" * 50)
    input("按 Enter 退出...")


if __name__ == "__main__":
    main()
