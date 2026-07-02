# CF (CloudFlare) 问题修复报告

## 问题现象

每次打开 Web UI 点击爬取，浏览器都需要重新通过 CloudFlare 验证，等待 **2.5 分钟**。

## 根因分析

旧架构中，`site_manager.py` 的 `/api/crawl` 和 `/api/crawl/test` 端点使用 `subprocess.Popen` 启动子进程：

```
Flask → subprocess.Popen("python -m crawler.group_crawler ...")
       → 子进程创建 BrowserActClient(session="group_crawl")
       → 新浏览器 session → CF 重新验证 → 2.5 分钟
```

每次子进程退出后 session 也随之消亡，下一个请求又要重新来过。

## 修复方案

### 1. 持久化 Browser Session（site_manager.py）

```python
# 全局维护一个浏览器 session
_crawl_client = None  # BrowserActClient，跨请求存活

def _get_persistent_client():
    """懒初始化，session 跨请求复用"""
    global _crawl_client
    if _crawl_client is None:
        _crawl_client = BrowserActClient(session="group_crawl", browser_id=BROWSER_ID)
    return _crawl_client

def _warm_session(url):
    """预热：首次 ensure_session + Cookie 保存，后续同域名直接 navigate"""
    if domain_already_warm:
        client.navigate(url)  # 秒级完成！
    else:
        client.ensure_session(url)  # 首次等待 CF
```

### 2. In-Thread 替代 Subprocess

爬取不再 spawn 子进程，而是在 Flask 线程中直接调用 CrawlEngine：

```
Flask → threading.Thread(target=_do_crawl)
       → 复用持久化 BrowserActClient
       → 进度事件通过 queue.Queue → SSE
```

### 3. 引擎事件回调（engine.py）

```python
_event_callback = None  # 模块级回调

def set_event_callback(cb):
    """in-thread 模式下，_log_msg/_emit 推送到队列而非 stdout"""

def _log_msg(msg, ltype=""):
    if _event_callback:
        _event_callback("log", {"msg": full_msg, "type": ltype})  # → queue → SSE
    else:
        _safe_print(full_msg)  # CLI 模式保持原样
```

### 4. CF 检测优化（browser_act.py）

```python
# 旧逻辑：session 存活 → navigate → CF wait 60s → 可能接受未渲染页面
# 新逻辑：session 存活 → navigate → 12s 快速渲染检测 → 未渲染则强制重建
```

## 效果对比

| 场景 | 旧架构 | 新架构 |
|------|--------|--------|
| 首次爬取 | 2.5 分钟（CF验证） | ~10 秒（Cookie导入 + 快速CF） |
| 再次爬取 | 2.5 分钟（CF验证） | **~2 秒**（直接 navigate） |
| Session 管理 | 每次新建+销毁 | 持久复用 |

## 修改文件

| 文件 | 改动 |
|------|------|
| `site_manager.py` | 持久化 session + in-thread crawling + warm-up |
| `crawler/engine.py` | set_event_callback / clear_event_callback |
| `crawler/group_crawler.py` | _crawl_with_engine 支持 client 参数 |
| `crawler/browser_act.py` | ensure_session 快速渲染检测 + 中文CF关键词 |

## 注意事项

- 并发爬取被锁保护（`_crawl_client_busy`），同时只能一个任务
- 同域名 session 预热后无需重复 CF 验证
- CLI 模式（`python -m crawler.group_crawler`）仍然可用，不受影响
