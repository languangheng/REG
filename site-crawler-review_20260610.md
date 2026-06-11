# Site-Crawler 项目代码审阅记录

> 时间：2026-06-10 22:25

## 项目概述

**Site Crawler** 是一个基于 `browser-act` CLI 的配置驱动型网站资源爬虫，核心功能：
1. 从列表页逐页爬取链接（图片/视频/文章详情页），自动翻页
2. 按配置的 `extract_chains` 深度爬取详情页，提取视频流地址或图片列表
3. 通过交互式 Config Wizard 让用户零配置生成爬虫规则

## 项目结构

```
site-crawler/
├── crawler.py                        # 主入口 CLI
├── site_manager.py                   # Flask Web UI（站点管理 + 爬取触发）
├── sites.yaml                        # 站点配置（当前只有 mimimi）
├── crawler/
│   ├── __init__.py                   # 导出 BrowserActClient, PageParser, JSONExporter
│   ├── browser_act.py                # browser-act CLI 封装层
│   ├── site_config.py                # YAML 配置加载（SiteConfig/LinkPatterns/ExtractChain 数据模型）
│   ├── parser.py                     # 页面解析（Markdown → 链接分类 + 下一页检测）
│   ├── exporter.py                   # JSON 导出（去重合并 + 摘要打印）
│   ├── config_wizard.py              # 配置向导（旧版，JS sessionStorage 状态管理）
│   └── config_wizard_refactored.py   # 配置向导（重构版，Python-centric 状态管理）
├── templates/                        # Flask 模板
└── 大量调试/测试脚本                  # fix_*, test_*, replace_cn*, research_* 等
```

## 核心模块分析

### 1. browser_act.py — CLI 封装层
- 封装 `browser-act` CLI 命令（navigate, get markdown, evaluate_js, click 等）
- **亮点**：超长 JS 通过临时文件 + PowerShell pipe 传入 stdin，绕过 shell 参数长度限制
- **问题**：`navigate()` 的 fallback 逻辑（先尝试 navigate，失败后 open browser）较脆弱

### 2. site_config.py — 配置数据模型
- 数据类：`SiteConfig → LinkPatterns + ExtractChain[] + EntryPoint[]`
- `LinkPatterns` 编译正则用于链接分类（video_detail / art_detail / exclude）
- `ExtractChain` 定义多步骤 JS 提取链（如 detail → play → stream）
- 从 `sites.yaml` 加载配置，自动安装 pyyaml

### 3. parser.py — 页面解析器
- 从 Markdown 提取所有 `[text](url)` 链接
- 按 URL 扩展名 + 站点 link_patterns 分类为 image/video/art
- 下一页检测：aria 属性 → 文本匹配（"下一页"/Next/>）→ URL 页码推断
- 合并 JS 提取的额外图片 URL（lazy-load 等）

### 4. exporter.py — JSON 导出
- 多页结果合并去重，按页面标题命名文件
- 输出结构：汇总信息 + 各页统计 + 分类链接列表 + 可选 deep_results

### 5. crawler.py — 主入口
- `crawl_list_pages()`: 逐页 navigate → get_markdown → parse → find_next
- `crawl_deep()`: 按 extract_chains 逐步执行 JS 提取（detail → play → stream）
- `_flatten_result()`: 将 steps 结果中的关键字段提升到顶层

### 6. config_wizard.py（旧版）— JS 状态管理
- 注入覆盖层 JS 到浏览器，用 sessionStorage 保存状态
- JS 端管理完整流程：选链接 → 跳详情页 → 选播放 → 提取流地址
- **问题**：页面跳转后 sessionStorage 状态恢复不稳定，已废弃

### 7. config_wizard_refactored.py（重构版）— Python 状态管理
- Python 维护 `wizard_state` 为唯一状态源
- 注入无状态 JS 覆盖层，JS 通过 `window.__cw_event` 发事件，Python 轮询
- **问题**：存在 JS 语法错误（onclick 属性中引号冲突），已修复但尚未验证

### 8. site_manager.py — Flask Web UI
- 站点列表/删除、启动配置向导、SSE 实时爬取进度推送

## 当前状态

- **核心爬虫功能**（列表爬取 + 深度提取 + JSON 导出）：✅ 可用
- **配置向导**：⚠️ 重构版未经测试验证，存在 JS 语法兼容性风险
- **站点配置**：仅有 mimimi 一个站点
- **代码质量**：大量调试/修复脚本散落在根目录，应清理

## 关键技术决策

1. browser-act CLI 而非 Playwright — 利用已安装的浏览器，保留登录状态
2. Markdown 解析而非 HTML — browser-act 的 `get markdown` 输出更稳定
3. JS 提取链 — 灵活但需要针对每个站点写 JS
4. Python-centric 状态管理 — 避免跨页面 JS 状态丢失问题

## 潜在改进方向

1. 清理根目录的调试脚本（~20个 fix_*/test_* 文件）
2. 配置向导需要端到端测试验证
3. stream 提取应支持 `<video>` 标签和 network 请求拦截
4. URL pattern 生成器不够通用（只替换数字）
5. requirements.txt 声称无依赖，实际需要 pyyaml（运行时自动安装）
