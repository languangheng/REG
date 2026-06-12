# TASKS.md

## 已完成 ✅

| 任务 | 完成时间 | 备注 |
|------|----------|------|
| 死代码清理 — 6个核心文件 | 2026-06-12 | 2856→1668行 (-42%), py_compile通过 |
| DFS 验证模式端到端测试 | 2026-06-12 | ✅ 3 链贯通，success=true |
| BFS 完整爬取测试 | 2026-06-12 | ✅ 翻页正常，数据导出正常 |
| 深度爬取并行化 — engine.py | 2026-06-12 | ThreadPoolExecutor, workers参数, standalone worker函数 |
| 深度爬取并行化 — CLI参数 | 2026-06-12 | group_crawler + engine_cli 均支持 --workers |
| 列表页并行爬取 — engine.py | 2026-06-12 | _crawl_list_pages_parallel() + url预计算 |
| WebUI 线程数选择器 + 添加分组按钮 | 2026-06-12 | index.html下拉框, site_manager workers参数, add_group模式 |

## 待办 📋

| 优先级 | 任务 | 状态 |
|--------|------|------|
| P0 | 并行爬取端到端测试（4 workers，列表+深度） | 待用户验证 |
| P1 | HAR 录制→配置生成→爬取全流程自动化验证 | 待开始 |

---

## 并行爬取技术细节

### 两层并行
1. **列表页并行**（`_crawl_list_pages_parallel`）：url_construct 预计算 page 2..N → ThreadPoolExecutor 并行爬取
2. **深链并行**（`_execute_deep_chain_parallel`）：detail/stream 链 → 每个 link 独立 session worker

### 架构
- **worker-safe 函数**：`_run_chain_steps()`, `_resolve_target_url()`, `_extract_streams()` 不绑定 CrawlEngine 实例
- **预计算**：`_generate_page_urls()` 从第1页URL + url_construct 推算全部分页
- **Session pool**：每个 worker 创建独立 BrowserActClient（`{base_session}_w{N}`）
- **结果合并**：`threading.Lock` 保护共享列表

### WebUI
- 每个卡片增加线程数下拉框（1/2/3/4/5/8/10），默认1
- 完整爬取和⚡验证均读取 workers 值
- 「＋ 添加分组」按钮 → HAR录制弹窗（mode=add_group, site_key传参）
- site_manager.py `/api/har/generate` 支持 add_group 模式追加分组

### 使用
```bash
# WebUI: 选择线程数 → 点击爬取，自动传参

# CLI:
python -m crawler.group_crawler --site www_mimimi_top --workers 4
```

---

**最后更新**: 2026-06-12
