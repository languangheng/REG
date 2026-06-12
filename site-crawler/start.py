#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Site Crawler - 一键启动脚本 (Python 版本)
功能：
1. 检查所有依赖环境（Python、Flask、browser-act CLI）
2. 启动前杀死 5050 端口上的进程
3. 启动 Flask 服务
4. 自动打开浏览器
"""

import os
import sys
import time
import subprocess
import webbrowser
import platform
from pathlib import Path

# 颜色代码（Windows 需要特殊处理）
if platform.system() == "Windows":
    os.system("color")

class Colors:
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    RESET = "\033[0m"
    BOLD = "\033[1m"

def print_step(step: str, message: str, status: str = "info"):
    """打印带颜色的步骤信息"""
    colors = {
        "info": Colors.BLUE,
        "success": Colors.GREEN,
        "warning": Colors.YELLOW,
        "error": Colors.RED
    }
    symbols = {
        "info": "[*]",
        "success": "[✓]",
        "warning": "[!]",
        "error": "[✗]"
    }
    color = colors.get(status, Colors.RESET)
    symbol = symbols.get(status, "[*]")
    print(f"{color}{symbol} {Colors.BOLD}[{step}]{Colors.RESET}{color} {message}{Colors.RESET}")

def check_python_version():
    """检查 Python 版本"""
    print_step("1/5", "检查 Python 版本...", "info")
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print_step("1/5", f"Python 版本过低: {version.major}.{version.minor}", "error")
        print("    需要 Python 3.8+，请升级 Python")
        return False
    print_step("1/5", f"Python {version.major}.{version.minor}.{version.micro}", "success")
    return True

def check_flask():
    """检查 Flask 是否安装"""
    print_step("2/5", "检查 Flask...", "info")
    try:
        import flask
        # 使用 importlib.metadata 获取版本号（避免 deprecation warning）
        try:
            from importlib.metadata import version
            flask_version = version("flask")
        except ImportError:
            flask_version = flask.__version__  # 回退到旧方法
        print_step("2/5", f"Flask {flask_version}", "success")
        return True
    except ImportError:
        print_step("2/5", "Flask 未安装", "warning")
        print("    正在安装 Flask...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "flask"])
            print_step("2/5", "Flask 安装成功", "success")
            return True
        except subprocess.CalledProcessError:
            print_step("2/5", "Flask 安装失败", "error")
            return False

def check_browser_act():
    """检查 browser-act CLI 是否可用"""
    print_step("3/5", "检查 browser-act CLI...", "info")
    
    # 检查 browser-act 命令是否可用
    try:
        result = subprocess.run(
            ["browser-act", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            version = result.stdout.strip()
            print_step("3/5", f"browser-act CLI {version}", "success")
            return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    
    # 检查 npx browser-act
    try:
        result = subprocess.run(
            ["npx", "browser-act", "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            version = result.stdout.strip()
            print_step("3/5", f"npx browser-act {version}", "success")
            return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    
    print_step("3/5", "browser-act CLI 未安装", "warning")
    print("    提示: 分组爬取功能需要 browser-act")
    print("    安装方法: npm install -g browser-act")
    print("    或: npx browser-act (会自动下载)")
    return False

def kill_port_5050():
    """杀死 5050 端口上的进程"""
    print_step("4/5", "检查并清理 5050 端口...", "info")
    
    system = platform.system()
    
    if system == "Windows":
        # Windows: 使用 netstat 和 taskkill
        try:
            # 查找占用 5050 端口的进程
            result = subprocess.run(
                ["netstat", "-ano", "|", "findstr", ":5050"],
                capture_output=True,
                text=True,
                shell=True
            )
            
            if result.stdout:
                # 提取 PID
                lines = result.stdout.strip().split("\n")
                pids = set()
                for line in lines:
                    parts = line.split()
                    if len(parts) > 4:
                        pid = parts[-1]
                        pids.add(pid)
                
                if pids:
                    print_step("4/5", f"发现 {len(pids)} 个进程占用 5050 端口", "warning")
                    for pid in pids:
                        try:
                            subprocess.run(
                                ["taskkill", "/PID", pid, "/F"],
                                capture_output=True,
                                check=True
                            )
                            print_step("4/5", f"已杀死进程 PID={pid}", "success")
                        except subprocess.CalledProcessError:
                            print_step("4/5", f"无法杀死进程 PID={pid} (可能需要管理员权限)", "error")
                    time.sleep(1)  # 等待端口释放
                else:
                    print_step("4/5", "5050 端口未被占用", "success")
            else:
                print_step("4/5", "5050 端口未被占用", "success")
                
        except Exception as e:
            print_step("4/5", f"清理端口时出错: {e}", "warning")
    
    else:
        # Linux/macOS: 使用 lsof 和 kill
        try:
            result = subprocess.run(
                ["lsof", "-ti:5050"],
                capture_output=True,
                text=True
            )
            
            if result.stdout.strip():
                pids = result.stdout.strip().split("\n")
                print_step("4/5", f"发现 {len(pids)} 个进程占用 5050 端口", "warning")
                for pid in pids:
                    try:
                        subprocess.run(["kill", "-9", pid], check=True)
                        print_step("4/5", f"已杀死进程 PID={pid}", "success")
                    except subprocess.CalledProcessError:
                        print_step("4/5", f"无法杀死进程 PID={pid}", "error")
                time.sleep(1)
            else:
                print_step("4/5", "5050 端口未被占用", "success")
                
        except Exception as e:
            print_step("4/5", f"清理端口时出错: {e}", "warning")
    
    return True

def start_flask():
    """启动 Flask 服务"""
    print_step("5/5", "启动 Flask 服务...", "info")
    
    # 获取项目根目录
    script_dir = Path(__file__).parent.absolute()
    os.chdir(script_dir)
    
    # 设置 PYTHONPATH
    os.environ["PYTHONPATH"] = str(script_dir)
    
    # 检查 site_manager.py 是否存在
    site_manager = script_dir / "site_manager.py"
    if not site_manager.exists():
        print_step("5/5", "site_manager.py 不存在", "error")
        return False
    
    # 构造本地访问地址
    host = "127.0.0.1"
    port = 5050
    url = f"http://{host}:{port}"
    
    print()
    print("=" * 60)
    print("  Site Crawler 启动成功！")
    print("=" * 60)
    print(f"  访问地址: {url}")
    print("  按 Ctrl+C 停止服务")
    print("=" * 60)
    print()
    
    # 3 秒后打开浏览器（使用 subprocess 更可靠）
    def open_browser():
        time.sleep(3)
        try:
            webbrowser.open(url)
        except Exception:
            # 回退：用系统命令打开
            if platform.system() == "Windows":
                os.system(f"start {url}")
            elif platform.system() == "Darwin":
                os.system(f"open {url}")
            else:
                os.system(f"xdg-open {url}")
    
    import threading
    browser_thread = threading.Thread(target=open_browser, daemon=True)
    browser_thread.start()
    
    # 启动 Flask
    try:
        subprocess.run([sys.executable, "site_manager.py"])
    except KeyboardInterrupt:
        print("\n")
        print_step("停止", "服务已停止", "info")
    
    return True

def main():
    """主函数"""
    print()
    print("=" * 60)
    print("  Site Crawler - 一键启动脚本")
    print("=" * 60)
    print()
    
    # 步骤 1: 检查 Python 版本
    if not check_python_version():
        input("\n按 Enter 键退出...")
        sys.exit(1)
    
    # 步骤 2: 检查 Flask
    if not check_flask():
        input("\n按 Enter 键退出...")
        sys.exit(1)
    
    # 步骤 3: 检查 browser-act CLI
    check_browser_act()  # 警告但不阻止启动
    
    # 步骤 4: 杀死 5050 端口上的进程
    kill_port_5050()
    
    # 步骤 5: 启动 Flask
    start_flask()
    
    input("\n按 Enter 键退出...")

if __name__ == "__main__":
    main()
