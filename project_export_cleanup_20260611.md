# Site Crawler 项目导出与清理

## 任务
1. 导出整个项目为供其他 AI 理解的 MD 文档
2. 清理无关测试/临时文件

## 结果

### 1. 项目文档
- 文件: `site-crawler/PROJECT.md` (5855 bytes)
- 内容: 架构总览、核心约束、文件清单、关键流程（自动分析/HAR录制/爬取）、browser_act.py 设计、auto_config.py 关键函数、sites.yaml 结构、已知问题、环境要求

### 2. 文件清理
- 移动 55+ 个临时/测试文件到 `_archive/` 目录（不删除，可恢复）
- 清理 `__pycache__/` 目录
- 保留的核心文件:
  - `crawler.py` (CLI 入口)
  - `site_manager.py` (Flask Web)
  - `sites.yaml` (站点配置)
  - `requirements.txt`, `README.md`, `PROJECT.md`
  - `crawler/` 目录: 9 个核心模块 + `__init__.py`
  - `templates/` 目录: 3 个 HTML 模板
  - 归档了 `config_wizard_refactored.py`（备用，未移动，留着参考）

### 归档内容
test_*.py, fix_*.py, check_*.py, research_*.py, sim_*.py, quick_crawl.py, e2e_*.py, debug_*.py, find_bounds*.py, replace_cn*.py, extract_cn.py, show_remaining.py, simplify_overlay.py, init_browser.py, 各种 .json/.txt/.js 临时文件, test_pages/, test_site/, player.html
