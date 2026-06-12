# 项目任务状态文档

> **目的**：记录项目当前所有任务的状态，供 AI 交接时快速了解工作进展，避免重复劳动或遗漏。
> **维护规则**：每次完成任务、开始新任务、或任务状态发生变化时，**必须立即更新本文档**。

---

## 📊 总体状态

| 项目 | 状态 |
|------|------|
| 上次更新 | 2026-06-12 |
| 当前活跃 Sprint | 爬取链路验证 + 优化 |
| 阻塞问题 | 翻页 URL 构造 bug（第2页 URL 变成首页） |

---

## ✅ 已完成任务

### [DONE] 一键启动脚本
- **文件**：`start.py`, `run.bat`
- **内容**：检查 Python/Flask/browser-act 依赖 → 杀死 5050 端口占用进程 → 启动 Flask → 自动打开浏览器
- **完成时间**：2026-06-12

### [DONE] 项目约束文档
- **文件**：`PROJECT_CONSTRAINTS.md`
- **内容**：工作流规范、文件组织规范、日志规范、测试规范
- **完成时间**：2026-06-12

### [DONE] 根目录清理
- **内容**：旧文档 → `tmp/doc/`，测试文件 → `tmp/`，废弃文件 → `tmp/old/`
- **完成时间**：2026-06-12

### [DONE] 统一日志框架
- **文件**：`crawler/logger.py`
- **内容**：每次启动自动创建时间戳目录（`log/YYYYMMDD_HHMMSS/`），双文件日志（`all.log` + `err.log`），`get_logger(name)` + `get_latest_log_dir()` 工具函数
- **集成**：`site_manager.py`, `crawler/group_crawler.py`, `crawler/browser_act.py`, `crawler/config_wizard_har.py`, `crawler/exporter.py`
- **完成时间**：2026-06-12

### [DONE] 前端爬取弹窗修复
- **文件**：`templates/index.html`
- **内容**：去掉自动关闭 → 新增"⏹ 停止"按钮（`_crawlSource.close()`）→ 新增"✕ 关闭"按钮，SSE 事件全部在弹窗日志中展示，错误时引导查看 `err.log`
- **完成时间**：2026-06-12

### [DONE] .gitignore 更新
- **内容**：添加 `log/` 和 `out/` 到忽略列表
- **完成时间**：2026-06-12

### [DONE] 日志集成补全
- **文件**：`crawler/config_wizard_har.py`, `crawler/exporter.py`, `crawler/group_crawler.py`, `crawler/browser_act.py`
- **内容**：
  - `config_wizard_har.py`：print() → `get_logger("config_wizard_har")`
  - `exporter.py`：print() → `get_logger("exporter")`
  - `group_crawler.py`：清理 main() 中 3 处 print()，改为 `_logger.info()`
  - `browser_act.py`：添加关键节点日志（初始化、session 检查、CF 验证、navigate 失败、浏览器创建、Cookie 操作）
- **完成时间**：2026-06-12

### [DONE] 验证后端爬取链路
- **验证结果**：
  - ✅ 服务启动正常，日志写入 `log/<时间戳>/` 独立目录
  - ✅ 列表页爬取成功（2页，232个视频链接）
  - ✅ 视频流地址提取成功（m3u8 流地址）
  - ✅ SSE 事件正常传递到前端
  - ⚠️ `wait_selector` 超时是非致命错误（`_smart_sleep` 忽略，不影响爬取）
  - ⚠️ 翻页 URL 构造 bug：第2页 URL 变成了 `https://www.mimimi.top/`（首页而非列表页第2页）
- **完成时间**：2026-06-12

---

## 🔄 进行中任务

> 当前无进行中的任务。

---

## 📋 待办任务（Backlog）

### [TODO] 修复翻页 URL 构造 bug
- **优先级**：🔴 高
- **背景**：`_construct_next_page_url()` 在 `group_crawler.py` 中构造的下一页 URL 错误，第2页变成了首页
- **问题日志**：`[Page 2] https://www.mimimi.top/`（应该是 `https://www.mimimi.top/vodshow/12----------2.html`）
- **修复方向**：调试 `_construct_next_page_url()` 的正则匹配逻辑

### [TODO] 深度爬取性能优化
- **优先级**：🟡 中
- **背景**：232个视频逐个深入非常慢（每个约30秒），全量爬取需要 ~2 小时
- **优化方向**：并行爬取、限制 deep-limit 默认值、缓存已有结果

---

## 🐛 已知问题 / 阻塞项

### 翻页 URL 构造 bug
- **症状**：第2页 URL 变成 `https://www.mimimi.top/`（首页），而非 `https://www.mimimi.top/vodshow/12----------2.html`
- **影响**：第2页爬到的是首页内容（318链接，190个视频链接），而非分类列表第2页
- **定位**：`crawler/group_crawler.py` 的 `_construct_next_page_url()` 函数
- **日志证据**：`log/20260612_093830/all.log` 中 `[Page 2] https://www.mimimi.top/`

### wait_selector 超时
- **症状**：`a[href*='/vodplay/'], a[href*='/arttype/']` 等选择器超时
- **影响**：非致命，`_smart_sleep` 忽略错误后继续
- **优化方向**：根据目标网站调整选择器，或缩短超时时间

---

## 📝 上下文备忘（AI 交接必读）

### 项目简介
Site Crawler：Flask WebUI + `browser-act` CLI 驱动 Chrome 爬取视频流/图片资源。

### 关键文件路径
| 文件 | 作用 |
|------|------|
| `site_manager.py` | Flask 主程序，提供 WebUI 和 API |
| `crawler/group_crawler.py` | 核心爬取逻辑，调用 browser-act |
| `crawler/logger.py` | 统一日志框架 |
| `crawler/browser_act.py` | browser-act CLI 封装层 |
| `crawler/config_wizard_har.py` | HAR 录制向导 |
| `crawler/exporter.py` | JSON 数据导出 |
| `templates/index.html` | 前端 UI，含爬取进度弹窗 |
| `sites.json` | 站点配置持久化文件 |
| `start.py` | 一键启动脚本 |
| `PROJECT_CONSTRAINTS.md` | 工作流和开发规范 |
| `TASKS.md` | 任务状态文档（本文档） |

### 开发工作流（必须遵守）
```
Plan → 用户确认 → 实现 → 测试（browser-act 端到端）→ 验收 → 提交
```

### 排错入口
1. 最新异常 → `log/<最新时间戳>/err.log`
2. 完整流程 → `log/<最新时间戳>/all.log`
3. 获取最新日志目录 → `from crawler.logger import get_latest_log_dir`

### 服务地址
- WebUI：`http://127.0.0.1:5050`
- 启动方式：`python start.py` 或双击 `run.bat`

---

## 📅 历史记录

| 日期 | 操作摘要 |
|------|----------|
| 2026-06-12 | 创建本文档；完成框架搭建（start.py、日志框架、前端弹窗修复、根目录清理） |
| 2026-06-12 | 日志集成补全（config_wizard_har.py、exporter.py、group_crawler.py、browser_act.py） |
| 2026-06-12 | 验证后端爬取链路：列表页+流提取成功，发现翻页 URL bug |

---

**⚠️ 维护提醒**：每次 AI 完成任务后，必须将对应条目从"待办"移到"已完成"，并更新"上次更新"日期。