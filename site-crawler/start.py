#!/usr/bin/env python3
"""站点管理服务启停脚本：杀掉旧进程 → 清 pycache → 启动 → 等待就绪"""
import os, sys, time, signal, subprocess, shutil

BASE = os.path.dirname(os.path.abspath(__file__))
PORT = 5050


def stop_service():
    """杀掉所有监听 PORT 的 Python 进程"""
    if sys.platform == 'win32':
        result = subprocess.run(
            f'netstat -ano | findstr ":{PORT}"',
            shell=True, capture_output=True, text=True
        )
        pids = set()
        for line in result.stdout.strip().split('\n'):
            parts = line.strip().split()
            if len(parts) >= 5:
                try:
                    pids.add(int(parts[-1]))
                except ValueError:
                    pass
        for pid in pids:
            try:
                os.kill(pid, signal.SIGTERM)
                print(f'  Killed PID {pid}')
            except OSError:
                pass
        if pids:
            time.sleep(1)
            for pid in pids:
                try:
                    subprocess.run(f'taskkill /F /PID {pid}', shell=True, capture_output=True)
                    print(f'  Force killed PID {pid}')
                except OSError:
                    pass
        else:
            print('  No process on port 5050')
    else:
        subprocess.run(
            f'fuser -k {PORT}/tcp 2>/dev/null || lsof -ti:{PORT} | xargs kill -9 2>/dev/null || true',
            shell=True, capture_output=True
        )
        print(f'  Stopped')


def clear_cache():
    """递归删除 __pycache__"""
    count = 0
    for root, dirs, files in os.walk(BASE):
        for d in dirs:
            if d == '__pycache__':
                path = os.path.join(root, d)
                try:
                    shutil.rmtree(path)
                    print(f'  Removed: {os.path.relpath(path, BASE)}')
                    count += 1
                except Exception as e:
                    print(f'  FAILED: {os.path.relpath(path, BASE)}: {e}')
    if count == 0:
        print('  No __pycache__ found')


def start_service():
    """启动 site_manager.py"""
    log_path = os.path.join(BASE, 'service.log')
    env = os.environ.copy()
    env['PYTHONIOENCODING'] = 'utf-8'
    proc = subprocess.Popen(
        [sys.executable, 'site_manager.py'],
        cwd=BASE,
        env=env,
        stdout=open(log_path, 'w', encoding='utf-8'),
        stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
    )
    print(f'  Started PID {proc.pid}')
    return proc


def wait_ready(timeout=15):
    """轮询 /api/sites 直到返回 200"""
    import urllib.request
    start = time.time()
    while time.time() - start < timeout:
        try:
            req = urllib.request.Request(f'http://localhost:{PORT}/api/sites')
            with urllib.request.urlopen(req, timeout=2) as r:
                if r.status == 200:
                    print(f'  Service ready (HTTP 200) in {time.time()-start:.1f}s')
                    return True
        except Exception:
            pass
        time.sleep(1)
    print(f'  TIMEOUT after {timeout}s')
    return False


if __name__ == '__main__':
    print('=== site-crawler service manager ===')
    print()
    print('[1/3] Stopping service...')
    stop_service()
    print()
    print('[2/3] Clearing cache...')
    clear_cache()
    print()
    print('[3/3] Starting service...')
    start_service()
    print()
    if wait_ready():
        print()
        print(f'=== Service running on http://localhost:{PORT} ===')
    else:
        print('=== FAILED ===')
        sys.exit(1)
