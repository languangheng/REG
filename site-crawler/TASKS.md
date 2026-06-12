# TASKS.md

## 已完成 ✅

| 任务 | 完成时间 | 备注 |
|------|----------|------|
| 死代码清理 — 6个核心文件 | 2026-06-12 | 2856→1668行 (-42%), py_compile通过 |
| DFS 验证模式端到端测试 | 2026-06-12 | ✅ 3 链贯通，success=true |
| BFS 完整爬取测试 | 2026-06-12 | ✅ 翻页正常，数据导出正常 |
| 深度爬取并行化 — engine.py | 2026-06-12 | ThreadPoolExecutor, workers参数, standalone worker函数 |
| 深度爬取并行化 — CLI参数 | 2026-06-12 | group_crawler + engine_cli 均支持 --workers |

## 待办 📋

| 优先级 | 任务 | 状态 |
|--------|------|------|
| P0 | 并行爬取端到端测试（4 workers） | 待用户验证 |
| P1 | HAR 录制→配置生成→爬取全流程自动化验证 | 待开始 |

---

## 并行爬取技术细节

### 架构
- **worker-safe 函数**：`_run_chain_steps()`, `_resolve_target_url()`, `_extract_streams()` 不绑定 CrawlEngine 实例
- **Session pool**：每个 worker 创建独立 BrowserActClient（`{base_session}_w{N}`）
- **结果合并**：`threading.Lock` 保护共享列表
- **进度事件**：`deep_progress` SSE 事件（completed/total/workers）

### 文件改动
| 文件 | 改动 | 行数 |
|------|------|------|
| `engine.py` | _execute_deep_chain_parallel() + 3个worker-safe函数 | +130 |
| `group_crawler.py` | --workers CLI + 参数透传 | +6 |
| `engine_cli.py` | --workers CLI + 参数透传 | +4 |

### 使用
```bash
# 串行（默认，兼容旧行为）
python -m crawler.group_crawler --site www_mimimi_top

# 4 workers 并行
python -m crawler.group_crawler --site www_mimimi_top --workers 4
```

---

**最后更新**: 2026-06-12
