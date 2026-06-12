# 项目记忆 — site-crawler

## 核心架构
- **browser-act CLI** 驱动 Chrome 浏览器（subprocess 调用）
- **CrawlEngine** 通用引擎（链式操作路径驱动），支持 BFS/DFS 双模式
- **sites.json** 每站自包含完整配置（entry_points + link_patterns + crawl_pattern）
- **MacCMS 默认链配置** 硬编码在 site_config.py（MACCMS_CRAWL_PATTERN, MACCMS_LINK_PATTERNS）
- **HAR 录制→ConfigGenerator** 自动检测 site_type + 生成完整链配置
- **开发原则**: 只做功能，不做兼容旧格式。配置必须有 crawl_pattern 才能爬取

## 关键文件
- `crawler/engine.py` — 通用引擎（链式操作路径驱动，BFS/DFS）
- `crawler/engine_cli.py` — 引擎 CLI 入口（--mode bfs/dfs）
- `crawler/browser_act.py` — browser-act CLI 封装
- `crawler/site_config.py` — 配置数据结构+解析+MacCMS默认值
- `crawler/group_crawler.py` — 分组爬虫（只走引擎，缺crawl_pattern报错）
- `crawler/config_wizard_har.py` — HAR 向导（site_type检测+链推断）
- `site_manager.py` — Flask 后端（/api/crawl + /api/crawl/test DFS验证）
- `templates/index.html` — WebUI（完整爬取+⚡验证按钮）

## smart_wait 策略
- 默认 state=attached（Playwright visible 严格，不可见元素超时）
- 混合策略：先 wait_selector(attached) + 1s渲染等待，超时 fallback time.sleep

## Windows 编码防御
- sys.stdout.reconfigure(utf-8) + buffer.write(utf-8) + PYTHONIOENCODING=utf-8

## DFS 验证模式
- per_chain_limit=1, max_pages=1 → 3-4页面出结果
- /api/crawl/test/<key> SSE 端点 → engine_cli --mode dfs
- 前端"⚡ 验证"按钮 → validateCrawl() 函数
- success=true/false（抓到流=配置正确）