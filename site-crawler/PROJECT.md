# Site Crawler 项目文档

> 给接手 AI 的快速上手指南。所有核心逻辑、架构决策、已知问题都在这里。

## 一句话概括

基于 browser-act CLI 的 CF 站点爬虫：Web UI 管理 → 自动/手动配置 → 网络优先爬取流地址和图片。

## 架构总览

```
┌─────────────────────────────────────────────┐
│  Web UI (Flask :5050)                        │
│  index.html / wizard_har.html                │
│  ┌──────────┐ ┌──────────┐ ┌──────────────┐ │
│  │站点管理   │ │HAR 录制  │ │自动分析       │ │
│  │CRUD+爬取 │ │用户操作→ │ │URL→一键配置   │ │
│  └──────────┘ └──────────┘ └──────────────┘ │
├─────────────────────────────────────────────┤
│  后端 API (site_manager.py)                   │
│  /api/sites  /api/crawl/<key>  /api/analyze  │
│  /api/har/start|stop|generate                 │
├─────────────────────────────────────────────┤
│  Crawler 核心 (crawler/)                      │
│  browser_act.py → auto_config.py              │
│  fast_crawler.py → config_wizard_har.py       │
│  site_config.py → parser.py → exporter.py     │
├─────────────────────────────────────────────┤
│  browser-act CLI (外部依赖)                    │
│  Chrome CDP 会话管理 + CF 绕过                 │
│  安装: uv tool install browser-act-cli --python 3.12 │
└─────────────────────────────────────────────┘
```

## 核心约束

1. **CF 一票否决**：目标站点有 Cloudflare 保护，逆向 API、直接 HTTP、Playwright 都过不了，只有 browser-act 驱动真实 Chrome 能行
2. **browser-act 会话持久化**：Chrome 侧会话持久，CLI 只是连接器。`ensure_session` 误判是因为 `parsed_state()` 超时而非会话真丢
3. **网络优先**：流地址提取策略是 `network requests` 捕获 > JS eval > DOM 解析
4. **会话复用**：所有 BrowserActClient 实例统一用 `browser_id="direct_local_100797252049567848"` 复用同一浏览器，避免重复 CF 验证

## 文件清单（核心）

### 后端
| 文件 | 职责 |
|------|------|
| `site_manager.py` | Flask Web 服务，所有 API 端点，站点 CRUD，SSE 推送 |
| `crawler/auto_config.py` | 一键自动配置生成器：URL→翻页→链接聚类→流捕获→配置 |
| `crawler/browser_act.py` | browser-act CLI 封装层：会话管理、state 解析、网络捕获 |
| `crawler/fast_crawler.py` | 网络优先爬虫 v2：markdown 提链接 + network 提流 |
| `crawler/config_wizard_har.py` | HAR 录制向导：用户操作浏览器→自动生成配置 |
| `crawler/config_wizard.py` | 覆盖层注入式配置向导（UI 2，备用方案） |
| `crawler/site_config.py` | 站点配置加载器：从 YAML 读取 link_patterns / extract_chains |
| `crawler/parser.py` | 页面解析器：从 Markdown 提取和分类链接 |
| `crawler/exporter.py` | 数据导出：JSON 文件输出 |
| `crawler.py` | CLI 入口：配置驱动的爬虫（调用 fast_crawler） |

### 前端
| 文件 | 职责 |
|------|------|
| `templates/index.html` | 主 UI：站点卡片 + 添加/分析/爬取 |
| `templates/wizard_har.html` | HAR 录制窗口：开始→录制中→停止→一次性展示结果 |
| `templates/wizard_overlay.html` | 覆盖层向导（备用） |

### 配置
| 文件 | 职责 |
|------|------|
| `sites.yaml` | 站点配置：link_patterns、extract_chains、entry_points |
| `requirements.txt` | 无第三方依赖（browser-act 是外部 CLI） |

## 关键流程

### 1. 自动分析 (`/api/analyze`)
```
用户输入列表页 URL
  → BrowserActClient 复用已有会话（browser_id）
  → ensure_session: session list 检查 → navigate → 等 CF
  → Step 1.5: _detect_url_increment (纯 HTTP 验证翻页)
              失败 → scroll + DOM 翻页检测
  → Step 2: get_markdown → extract_links → 聚类
            启发式评分选最佳详情页链接模式
  → Step 3: 进入详情页 → _try_capture_stream (6 层降级)
            network 直接查 → 点播放按钮 → 点 video/iframe
            → 选集数 → 选线路 → JS 提取兜底
  → Step 4: 生成 sites.yaml 配置片段
```

### 2. HAR 录制
```
用户点击"开始录制"
  → HarWizard.start (复用已有浏览器，不 navigate)
  → 后台 poll_loop 每 2s 调 poll() 收集数据
  → 用户在浏览器自由浏览（过 CF、翻页、播放视频）
  → 用户点击"停止录制"
  → har_stop → 构建 summary（steps/streams/images/apis）
  → 前端一次性渲染所有结果
  → 点击"生成配置" → ConfigGenerator → 写入 sites.yaml
```

### 3. 爬取 (`/api/crawl/<key>`)
```
加载 sites.yaml 中的站点配置
  → crawl_list_pages: markdown 提链接 + state 翻页
  → 可选 deep: crawl_video_streams / crawl_art_images
  → JSONExporter 输出结果文件
```

## browser_act.py 关键设计

### StateSnapshot 解析
browser-act `state` 命令输出文本格式：
```
url=...
title=...
|SCROLL|<html />
  [1]<tag attrs />text
  [2]<tag attrs>text
```
解析为 `StateSnapshot(url, title, elements: list[StateElement])`。

### ensure_session 三层检测
1. `_session_exists()`: 调 `session list` 检查 session name → 最可靠
2. `parsed_state()`: 验证页面可用 → 可能超时误判
3. 都失败 → `browser open` 重建

### network_requests
CSV 格式输出，解析为 `[dict]`。支持 `--filter`（URL 子串）、`--type`（xhr,fetch）、`--clear`。

## auto_config.py 关键函数

### _detect_url_increment(url)
- 正则匹配 URL path 最后一个数字段
- 排除 >500 的大数字（可能是 ID 不是页码）
- HTTP 验证下一页是否存在
- 返回 `{template, current_val, next_url}`

### _try_capture_stream(client, snap, result)
6 层降级策略，每层都轮询等待流地址出现：
1. 直接查 network（页面可能自动播放）
2. 点播放按钮
3. 点 video/iframe 元素
4. 选第一个集数标签
5. 选第一个线路标签
6. JS 提取兜底

### _cluster_links(links, base_url)
- URL 路径数字段替换为 `{id}` 得 pattern
- 按 pattern 聚类，含 `{id}` 的才保留
- 启发式评分：DETAIL_KEYWORDS 加分、EXCLUDE_KEYWORDS 减分、路径深度/数量加分

## sites.yaml 结构

```yaml
sites:
  <site_key>:
    name: 显示名
    base_url: https://...
    link_patterns:
      video_detail: [正则...]
      art_detail: [正则...]
      exclude: [正则...]
    extract_chains:
      video:
        steps:
          - name: detail
            extract_js: "..."
          - name: play
            extract_js: "..."
    entry_points:
      - name: 入口名
        url: https://...
        type: video|art
    network_first: true
    pagination:
      type: url_increment|button_next|number_group|...
      url_template: /path/{page}.html
      start_page: 1
```

## 已知问题

1. **auto_config.py 有语法错误**：`_detect_url_increment` 插入后，config 构建代码中有一行 `"extract_chains": [],` 漂浮在 dict 字面量外，需要修复
2. **SSE 端点残留**：`/api/har/events` 和 `_har_broadcast` 还在 site_manager.py 中，但前端不再使用，可清理
3. **config_wizard_refactored.py** 是备用方案，与 config_wizard.py 功能重叠
4. **翻页 URL 构造**：`_construct_next_page_url` 在 fast_crawler.py 中，模式匹配较脆弱，对非常规格式会失败

## 环境要求

- Python 3.12+
- browser-act CLI: `uv tool install browser-act-cli --python 3.12`
- Chrome/Chromium 浏览器（CDP 直连模式）
- Flask（Web UI）
- PyYAML（配置读写）
- 启动: `python site_manager.py` → 访问 `http://localhost:5050`

## 开发注意事项

- Windows 环境，PowerShell 语法
- `browser-act` CLI 在 `~/.local/bin/`，PATH 需包含
- 所有 BrowserActClient 必须指定 `browser_id="direct_local_100797252049567848"` 以复用会话
- CF 站点访问间隔至少 2-3 秒，避免触发验证
- 中文编码：`sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")`
