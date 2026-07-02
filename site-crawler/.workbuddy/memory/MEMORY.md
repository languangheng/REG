# 项目记忆 — site-crawler

## 核心架构
- **browser-act CLI** 驱动 Chrome 浏览器（**现已改为 persistent session**）
- **CrawlEngine** 通用引擎（链式操作路径驱动），支持 BFS/DFS 双模式
- **sites.json** 每站自包含完整配置（entry_points + link_patterns + crawl_pattern）
- **MacCMS 默认链配置** 硬编码在 site_config.py（MACCMS_CRAWL_PATTERN, MACCMS_LINK_PATTERNS）
- **HAR 录制→ConfigGenerator** 自动检测 site_type + 生成完整链配置
- **引导式向导** (guided_wizard.py) 替代 HAR 录制，用户主动触发每一步
- **开发原则**: 只做功能，不做兼容旧格式。配置必须有 crawl_pattern 才能爬取

## 引导式向导架构
- `GuidedWizard` 类管理引导会话生命周期（start→pagination→add_path→detect_resource→complete）
- **只录 URL 模式，不录按钮操作**: 按钮点击后的 URL 变化 = 下一级页面模式
- `generalize_path()` 将数字序列替换为 `\d+`，扩展名点号转义
- `detect_pagination()` 支持5种翻页模式: query_param, path_page, maccms, suffix_page, query_other
- 翻页检测: 用户点"开始"记录URL → 翻页 → 点"结束"对比URL变化
- 资源检测: 调用 `network_requests()` 查找 m3u8/mp4/flv/ts
- `generate_site_config()` 从 levels + pagination 生成完整 sites.json 配置
- 10个 `/api/guided/*` API 端点（POST为主，status用GET）
- 前端 `wizard_guided.html`: 左面板引导步骤+日志，右面板配置预览
- **不支持的(已排除)**: URL不变翻页(AJAX/滚动)、多路径、实时预览

## CF (CloudFlare) 防护 — 持久化 Session 架构
- **site_manager.py** 维护持久化 BrowserActClient（`_get_persistent_client()`）
- `_warm_session(url)` → 首次预热：ensure_session + Cookie 保存；后续同域名直接 navigate
- `/api/crawl` 和 `/api/crawl/test` 改为 **in-thread** 模式（不再 subprocess）
- engine.py 支持 `set_event_callback()` → SSE 事件通过 queue 推送
- group_crawler.py 的 `_crawl_with_engine` 支持外部传入 client 参数（复用 session）
- **效果**: CF 从每次 2.5min → 首次 10s（Cookie 导入）→ 后续 2s（直接 navigate）
- `_crawl_client_busy` 锁防止并发爬取冲突

## 关键文件
- `crawler/engine.py` — 通用引擎（链式操作路径驱动，BFS/DFS）+ `set_event_callback()`
- `crawler/engine_cli.py` — 引擎 CLI 入口（--mode bfs/dfs）
- `crawler/browser_act.py` — browser-act CLI 封装，`ensure_session()` 快速渲染检测
- `crawler/site_config.py` — 配置数据结构+解析+MacCMS默认值
- `crawler/group_crawler.py` — 分组爬虫（支持 client 参数复用 session）
- `crawler/config_wizard_har.py` — HAR 向导（site_type检测+链推断，旧版保留）
- `crawler/guided_wizard.py` — **引导式向导**（用户主动触发分步采集）
- `site_manager.py` — Flask 后端（持久化 session + in-thread crawl + 10个guided API）
- `templates/index.html` — WebUI（完整爬取+⚡验证+➕添加网站按钮）
- `templates/wizard_guided.html` — 引导向导前端页面

## smart_wait 策略
- 默认 state=attached（Playwright visible 严格，不可见元素超时）
- 混合策略：先 wait_selector(attached) + 1s渲染等待，超时 fallback time.sleep

## Windows 编码防御
- sys.stdout.reconfigure(utf-8) + buffer.write(utf-8) + PYTHONIOENCODING=utf-8

## DFS 验证模式
- per_chain_limit=1, max_pages=1 → 3-4页面出结果
- /api/crawl/test/<key> SSE 端点 → in-thread CrawlEngine DFS
- 前端"⚡ 验证"按钮 → validateCrawl() 函数
- success=true/false（抓到流=配置正确）