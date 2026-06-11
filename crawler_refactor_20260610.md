# 爬虫通用化重构

## 目标
将网站特定规则从代码中抽出，做成配置驱动，新站点只需写 YAML 配置即可。

## 架构变更

### 之前
- `browser_act.py` 硬编码 `get_voddetail_play_links()`、`get_vodplay_stream_url()`、`get_artdetail_images()`
- `parser.py` 硬编码 `VIDEO_DETAIL_PATTERNS`、`ART_DETAIL_PATTERNS`、`EXCLUDE_PATTERNS`
- 换网站 = 改代码

### 之后
- **`sites.yaml`** — 站点配置文件，定义：
  - `link_patterns`: 列表页链接分类正则（video_detail/art_detail/exclude）
  - `extract_chains`: 详情页提取链（每步是 JS 代码）
  - `entry_points`: 爬取入口
- **`site_config.py`** — 加载 YAML，编译正则，提供 `SiteConfig` 数据类
- **`browser_act.py`** — 只保留通用方法，新增 `execute_step(step)` 执行配置中的 JS
- **`parser.py`** — 接受 `SiteConfig`，用其 `link_patterns` 做分类
- **`crawler.py`** — `crawl_deep()` 按 `extract_chains` 配置驱动深度爬取

### 关键设计：ExtractChain
```yaml
extract_chains:
  video:
    steps:
      - name: "detail"
        extract_js: |  # 提取播放链接列表
      - name: "play"
        extract_js: |  # 提取 m3u8 流地址
  art:
    steps:
      - name: "detail"
        extract_js: |  # 提取图片 URL 列表
```

链式执行：前一步返回的链接列表，第一个 href 自动作为下一步的导航 URL。

## 验证结果
- 配置加载 ✅
- 链接分类 ✅（7个video_detail正则, 1个art_detail正则, 7个exclude正则）
- 深度爬取链 ✅（detail → play → stream_url = m3u8地址）

## 新站点接入
只需在 `sites.yaml` 中添加新站点配置，写好 link_patterns 和 extract_chains 即可，无需改代码。
