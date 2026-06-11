# 自动分析流程修复记录

## 修复时间
2026-06-11 01:52 GMT+8

## 修复的问题

### P0 - `auto_config.py` 语法错误
**位置**: `crawler/auto_config.py` 第 433-438 行

**问题**: `"extract_chains": [],` 漂浮在 dict 字面量外，导致 `SyntaxError`

**修复**: 将 `"extract_chains": [],` 移入 `config = {...}` dict 内部

**修复前**:
```python
    config = {
        ...,
        "pagination": {...},
    }   # ← dict 在此结束

    if url_increment_pattern:
        config["pagination"]["url_template"] = ...
        config["pagination"]["start_page"] = ...
        "extract_chains": [],   # ← 语法错误！在 dict 外
    }   # ← 多余的 }
```

**修复后**:
```python
    config = {
        ...,
        "pagination": {...},
        "extract_chains": [],   # ← 在 dict 内，正确
    }

    if url_increment_pattern:
        config["pagination"]["url_template"] = ...
        config["pagination"]["start_page"] = ...
```

---

### P1 - `site_manager.py` SSE 阻塞 5 分钟无进度
**位置**: `site_manager.py` 第 344-348 行

**问题**: `q.get(timeout=300)` 阻塞最多 5 分钟，期间无任何 SSE 事件发出，用户以为卡死

**修复**: 改为带心跳的轮询循环，`yield ": heartbeat\n\n"` 保持 SSE 连接 alive

**修复前**:
```python
            t = threading.Thread(target=run, daemon=True)
            t.start()

            q.get(timeout=300)  # ← 阻塞 5 分钟！

            result = result_holder[0]
```

**修复后**:
```python
            t = threading.Thread(target=run, daemon=True)
            t.start()

            # Poll for completion with heartbeat
            import time as _time
            while True:
                try:
                    q.get_nowait()  # non-blocking check
                    break  # got completion signal
                except queue.Empty:
                    # Send heartbeat to keep SSE alive
                    yield ": heartbeat\n\n"
                    _time.sleep(2)

            result = result_holder[0]
```

**效果**:
- 每 2 秒发送一次心跳（SSE 注释行，浏览器忽略）
- SSE 连接不再超时或假死
- 用户能看到进度（虽然 still 只在 `auto_config()` 完成后才收到日志，但连接保持 alive）

---

## 未修复的问题（后续优化）

### 实时进度推送
**问题**: 当前实现要等 `auto_config()` 完全执行完才能收到所有日志，中间无进度更新

**方案**（未实现）:
1. 修改 `auto_config()` 接受 `log_callback` 参数
2. 每次 `result.log.append(line)` 时同时调用 `log_callback(line)`
3. `site_manager.py` 中传入 callback，将日志行实时放入队列
4. SSE 生成器实时 yield 日志行

**优先级**: P2（当前能工作，只是体验不够好）

---

## 验证结果

### 语法检查
```bash
python -m py_compile crawler/auto_config.py
# 无输出 = 语法正确
```

### 逻辑检查
- [x] `config` dict 包含 `"extract_chains"` 键
- [x] `if url_increment_pattern:` 块无语法错误
- [x] `site_manager.py` 的 `generate()` 函数能正确 yield 心跳

---

## 复习：Review 时误诊的问题

### 误诊 1: `site_manager.py` 异常处理后访问 `.log`
**我说的**: 如果 `auto_config()` 抛异常，`result` 是 `Exception` 对象，后续 `for line in result.log:` 会崩溃

**实际情况**: `if isinstance(result, Exception):` 分支里有 `return`，所以永远不会执行到 `for line in result.log:`。**不是 bug**。

### 误诊 2: 前端 `analyzeSource.onerror` 未清理
**我说的**: `onerror` 回调里没设 `analyzeSource = null`

**实际情况**: 代码里**已经有** `analyzeSource = null;` 了。我看错了。

---

## 文件变更清单

| 文件 | 变更 |
|------|------|
| `crawler/auto_config.py` | 修复语法错误（`"extract_chains"` 位置） |
| `site_manager.py` | 修复 SSE 阻塞（轮询 + 心跳） |

---

## 后续建议

1. **实现实时进度推送**（见上文"未修复的问题"）
2. **给 `auto_config()` 加超时保护**（当前无限等待页面加载）
3. **前端加超时处理**（如果 SSE 连接意外断开，提示用户）
