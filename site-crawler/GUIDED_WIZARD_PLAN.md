# 引导式向导方案文档

## 1. 总体设计

### 核心理念

| 原则 | 说明 |
|------|------|
| **只录 URL 模式，不录按钮操作** | 按钮点击后的 URL 变化 = 下一级页面的模式 |
| **用户主动触发，不轮询** | 每一步都是用户点击按钮触发，系统只负责分析和反馈 |
| **引导式分步操作** | 翻页检测 → 添加路径 → 检测资源 → 完成 |
| **任意深度** | 添加路径按钮一直保留，用户可以添加任意深度的页面层级 |
| **资源检测 = 路径终结标志** | 检测到资源后提示完成，但用户可选择继续添加路径 |

### 交互概览

```
打开浏览器 → 输入起始URL → 自动导航
    ↓
[开始翻页检测] → 用户翻页 → [结束翻页检测] → 识别翻页模式
    ↓ (成功后出现)
[添加路径] → 用户进入下一级页面 → 点[添加路径] → 识别URL模式
    ↓ (添加路径后出现)
[检测资源] + [添加路径]  ← 两个按钮同时存在
    ↓
检测资源成功 → [确认保存] / [继续添加路径]
    ↓
[确认保存] → 生成配置 → 写入 sites.json
```

---

## 2. 引导式向导交互流程（详细）

### 步骤 0：打开浏览器

```
┌─────────────────────────────────────────────────────┐
│  添加网站                                            │
│                                                      │
│  网站名称: [          ]                              │
│  起始URL:  [https://example.com    ] [打开浏览器]     │
│                                                      │
│  点击"打开浏览器"后:                                   │
│  → 后端通过持久化 session 自动打开浏览器并导航到起始URL  │
│  → 页面下方出现引导区域                                │
└─────────────────────────────────────────────────────┘
```

- 复用 `site_manager.py` 的持久化 session（`_get_persistent_client()`）
- 用户输入起始URL → 后端 `navigate` 到该URL → 浏览器自动打开

### 步骤 1：翻页检测

```
┌─────────────────────────────────────────────────────┐
│  📍 Level 0: 列表页                                  │
│  URL: https://example.com/vodshow/1---------.html    │
│                                                      │
│  翻页模式: ❌ 未检测                                   │
│                                                      │
│  [开始翻页检测]     ← 点击后按钮变为 ↓                  │
│                                                      │
│  提示: "请在浏览器中翻页，完成后点击下方按钮"            │
│  [结束翻页检测]     ← 用户翻页后点击                    │
│                                                      │
│  ✅ 检测成功:                                         │
│  翻页模式: url_construct (MacCMS格式)                │
│  泛化结果: /vodshow/\d+-*-.html                      │
│  [编辑] [重新检测翻页]                                 │
│                                                      │
│  ❌ 检测失败:                                         │
│  "未能识别翻页模式，请确认已翻页后重试"                  │
│  [重新检测翻页]                                       │
└─────────────────────────────────────────────────────┘
```

**交互逻辑**：

1. 用户点击 **[开始翻页检测]** → 后端记录当前 URL (`url_before`)，按钮变为 **[结束翻页检测]**
2. 用户在浏览器中翻页
3. 用户点击 **[结束翻页检测]** → 后端获取当前 URL (`url_after`)，对比 `url_before` vs `url_after`
4. 识别结果：
   - **成功**：显示翻页模式 + 泛化结果（可编辑），出现 **[重新检测翻页]** 按钮
   - **失败**：提示用户重试，按钮恢复为 **[开始翻页检测]**
5. 用户可以多次 **[重新检测翻页]**，每次记录新的 URL 对比，覆盖之前的结果

**翻页模式识别算法**：

```python
def detect_pagination(url_before: str, url_after: str) -> dict | None:
    """对比两个URL，识别翻页模式。"""

    path_before = urlparse(url_before).path
    path_after = urlparse(url_after).path

    # 模式1: MacCMS格式 /vodshow/1--------2---.html
    # before: /vodshow/1---------.html    (无页码=第1页)
    # after:  /vodshow/1--------2---.html (有页码=第2页)
    maccms_pattern = r'^(.+?/\d+)(-+)(\d+)?(-*)(\.html)?$'
    m_after = re.match(maccms_pattern, path_after)
    m_before = re.match(maccms_pattern, path_before)
    if m_after and m_before:
        # 骨架相同，只有页码数字不同
        if m_after.group(1) == m_before.group(1):
            return {"method": "url_construct", "format": "maccms"}

    # 模式2: ?page=1 → ?page=2
    params_before = parse_qs(urlparse(url_before).query)
    params_after = parse_qs(urlparse(url_after).query)
    if 'page' in params_after:
        return {"method": "url_construct", "format": "query_param"}

    # 模式3: /page/1 → /page/2
    if re.search(r'/page/\d+', path_after):
        return {"method": "url_construct", "format": "path_page"}

    # 模式4: /category/1.html → /category/1-2.html
    m = re.match(r'^(.+?/\d+)(?:-(\d+))?(\.html)?$', path_after)
    if m and m.group(2):
        return {"method": "url_construct", "format": "suffix_page"}

    # 模式5: 同路径，query参数变化（非page参数）
    if path_before == path_after and url_before != url_after:
        return {"method": "url_construct", "format": "query_other"}

    return None  # 未识别
```

### 步骤 2：添加路径（可重复）

```
┌─────────────────────────────────────────────────────┐
│  ➕ 添加路径                                          │
│  提示: "请进入下一级页面，然后点击[添加路径]"            │
│  [添加路径]                                          │
└─────────────────────────────────────────────────────┘

用户点击后 → 后端获取当前URL → 泛化 → 显示结果 ↓

┌─────────────────────────────────────────────────────┐
│  ✅ Level 1: 详情页                                  │
│  原始URL: /voddetail/456.html                        │
│  URL模式: /voddetail/\d+\.html                       │
│  [编辑]                                              │
│                                                      │
│  [检测资源]  [添加路径]     ← 两个按钮同时存在          │
└─────────────────────────────────────────────────────┘
```

**交互逻辑**：

1. 用户在浏览器中进入下一级页面（比如从列表页点进详情页）
2. 用户点击 **[添加路径]** → 后端获取当前 URL → 泛化 URL 模式
3. 显示泛化结果 + **[编辑]** 按钮（点击展开编辑框，直接修改正则）
4. **[检测资源]** 和 **[添加路径]** 同时出现

**URL 泛化算法**：

```python
def generalize_path(path: str) -> str:
    """将URL路径泛化为正则模式。"""

    # 去掉 query string
    path = path.split('?')[0]

    # MacCMS 特殊处理:
    # /vodshow/1--------2---.html → /vodshow/\d+-*-.html
    maccms = re.match(r'^(.+?/\d+)(-+)(\d+)?(-*)(\.html)?$', path)
    if maccms:
        return f"{re.sub(r'\d+', r'\\d+', maccms.group(1))}-*-.html"

    # 通用处理: 逐段替换数字为 \d+
    # /voddetail/456.html → /voddetail/\d+\.html
    # /vodplay/456-1-1.html → /vodplay/\d+-\d+-\d+\.html
    parts = path.split('/')
    generalized = []
    for part in parts:
        # 数字段 → \d+
        if re.match(r'^\d+$', part):
            generalized.append('\\d+')
        # 带数字的段 → 替换数字
        elif re.search(r'\d', part):
            generalized.append(re.sub(r'\d+', r'\\d+', part))
        else:
            generalized.append(part)

    result = '/'.join(generalized)

    # 转义 .html 等
    result = re.sub(r'\.html$', r'\\.html', result)

    return result
```

**层级自动命名**：

```python
def guess_level_name(path: str, level: int) -> str:
    """根据URL路径和层级推断名称。"""
    keywords = {
        'detail': '详情页', 'voddetail': '详情页',
        'play': '播放页', 'vodplay': '播放页',
        'video': '视频页', 'episode': '剧集页',
        'download': '下载页',
    }
    for kw, name in keywords.items():
        if kw in path.lower():
            return name
    if level == 0:
        return '列表页'
    return f'第{level}级页面'
```

### 步骤 3：检测资源

```
┌─────────────────────────────────────────────────────┐
│  🔍 检测资源                                         │
│  提示: "请确保视频已开始播放，然后点击[检测资源]"        │
│  [检测资源]                                          │
└─────────────────────────────────────────────────────┘

检测成功 ↓

┌─────────────────────────────────────────────────────┐
│  🎬 资源已捕获！                                     │
│  资源类型: m3u8                                      │
│  资源地址: https://xxx.com/playlist.m3u8              │
│                                                      │
│  ✅ 采集路径已完成！                                  │
│                                                      │
│  路径概览:                                           │
│  Level 0: 列表页 /vodshow/\d+-*-.html                │
│    翻页: url_construct (MacCMS)                      │
│  Level 1: 详情页 /voddetail/\d+\.html                │
│  Level 2: 播放页 /vodplay/\d+-\d+-\d+\.html (资源页) │
│                                                      │
│  [确认保存]  [继续添加路径]                           │
└─────────────────────────────────────────────────────┘

检测失败 ↓

┌─────────────────────────────────────────────────────┐
│  ❌ 未检测到资源                                      │
│  提示: "请确认视频已开始播放，或尝试其他页面"            │
│  [重新检测资源]                                      │
└─────────────────────────────────────────────────────┘
```

**交互逻辑**：

1. 用户点击 **[检测资源]** → 后端通过 `network_requests()` 检测 m3u8/mp4/flv
2. **成功**：显示资源信息，当前 Level 标记为资源页，出现 **[确认保存]** 和 **[继续添加路径]**
3. **失败**：提示重试

**资源匹配当前 Level 的逻辑**：

```python
def match_current_level(current_url: str, levels: list[GuidedLevel]) -> int | None:
    """当前URL匹配哪个Level？"""
    path = urlparse(current_url).path
    for level in levels:
        if re.search(level.path_pattern, path):
            return level.level
    return None
```

### 步骤 4：确认保存

用户点击 **[确认保存]**：

1. 遍历所有 levels，生成完整的 `crawl_pattern` + `link_patterns` + `entry_points`
2. 写入 `sites.json`
3. 返回首页，新站点出现在列表中

用户点击 **[继续添加路径]**：

1. 资源检测结果保留但不作为终结标志
2. 回到"添加路径"步骤，用户可以继续深入

### [完成] 按钮

任意时候可点击，有确认提示：

| 状态 | 提示 |
|------|------|
| 还没检测翻页 | "尚未检测翻页模式，确认跳过？翻页功能将不可用。" |
| 还没添加路径 | "尚未添加任何路径，无法生成采集配置。" → 阻止完成 |
| 还没检测资源 | "尚未检测到资源，确认保存？资源采集可能失败。" |
| 都完成了 | 直接保存 |

---

## 3. 后端 API 设计

### 新增 API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/guided/start` | POST | 开始引导：创建 session + 打开浏览器 + 导航到起始URL |
| `/api/guided/status` | GET | 获取当前引导状态（所有 levels + 翻页信息） |
| `/api/guided/pagination/start` | POST | 开始翻页检测：记录当前URL |
| `/api/guided/pagination/end` | POST | 结束翻页检测：获取当前URL + 对比识别翻页模式 |
| `/api/guided/path/add` | POST | 添加路径：获取当前URL + 泛化 + 添加新 Level |
| `/api/guided/resource/detect` | POST | 检测资源：获取网络请求中的 m3u8/mp4 |
| `/api/guided/complete` | POST | 完成引导：生成配置 + 写入 sites.json |
| `/api/guided/cancel` | POST | 取消引导：清理 session |

### 请求/响应格式

```json
// POST /api/guided/start
{
  "site_name": "我的网站",
  "start_url": "https://example.com/vodshow/1---------.html"
}
// Response
{
  "ok": true,
  "session_id": "guided_xxx",
  "current_url": "https://example.com/vodshow/1---------.html"
}

// POST /api/guided/pagination/start
// Response
{
  "ok": true,
  "url_before": "https://example.com/vodshow/1---------.html"
}

// POST /api/guided/pagination/end
// Response (成功)
{
  "ok": true,
  "pagination": {
    "method": "url_construct",
    "format": "maccms",
    "url_before": "https://example.com/vodshow/1---------.html",
    "url_after": "https://example.com/vodshow/1--------2---.html"
  },
  "generalized": "/vodshow/\\d+-*-.html"
}
// Response (失败)
{
  "ok": false,
  "error": "未能识别翻页模式，URL变化不足以推断翻页方式"
}

// POST /api/guided/path/add
// Response
{
  "ok": true,
  "level": 1,
  "name": "详情页",
  "original_url": "https://example.com/voddetail/456.html",
  "path_pattern": "/voddetail/\\d+\\.html"
}

// POST /api/guided/resource/detect
// Response (成功)
{
  "ok": true,
  "matched_level": 2,
  "resources": [
    {"type": "m3u8", "url": "https://xxx.com/playlist.m3u8"}
  ]
}
// Response (失败)
{
  "ok": false,
  "error": "未检测到 m3u8/mp4/flv 资源，请确认视频已开始播放"
}

// POST /api/guided/complete
{
  "site_name": "我的网站",
  "start_url": "https://example.com/vodshow/1---------.html",
  "levels": [
    {"level": 0, "path_pattern": "/vodshow/\\d+-*-.html", "name": "列表页", "pagination": {...}},
    {"level": 1, "path_pattern": "/voddetail/\\d+\\.html", "name": "详情页"},
    {"level": 2, "path_pattern": "/vodplay/\\d+-\\d+-\\d+\\.html", "name": "播放页", "is_resource": true}
  ]
}
// Response
{
  "ok": true,
  "site_key": "my_site",
  "config": { ... }  // 生成的完整 sites.json 配置
}

// GET /api/guided/status
// Response
{
  "ok": true,
  "session_id": "guided_xxx",
  "site_name": "我的网站",
  "start_url": "https://example.com/vodshow/1---------.html",
  "current_url": "https://example.com/vodplay/456-1-1.html",
  "levels": [...],
  "pagination": {...} or null,
  "pagination_detecting": false,
  "resource_detected": true
}
```

---

## 4. 配置生成映射

### 引导数据 → sites.json 映射规则

```python
def generate_site_config(site_name, start_url, levels, pagination) -> dict:
    """从引导数据生成完整的 sites.json 配置。"""

    chains = {}
    chain_order = []
    link_patterns = {}

    for i, level in enumerate(levels):
        if i == 0:
            # Level 0 = list_crawl
            chain_name = "list_crawl"
            link_type = f"level_1" if len(levels) > 1 else "resource"

            chain = {
                "steps": [
                    {"action": "navigate"},
                    {"action": "smart_wait", "selector": _infer_selector(level.path_pattern)},
                    {"action": "extract_links", "source": "markdown", "link_type": link_type}
                ]
            }
            if pagination:
                chain["pagination"] = {
                    "methods": [pagination["method"]],
                    "max_pages": 100
                }

            chains[chain_name] = chain
            chain_order.append(chain_name)

        elif level.is_resource:
            # 资源页 = stream_capture
            chain_name = "stream_capture"
            chains[chain_name] = {
                "steps": [
                    {"action": "navigate"},
                    {"action": "smart_wait", "selector": "video, iframe[src], .player"},
                    {"action": "network_capture", "filter": ".m3u8,.mp4,.flv", "wait_seconds": 5}
                ]
            }
            chain_order.append(chain_name)

        else:
            # 中间层级 = level_N
            chain_name = f"level_{i}"
            next_level = levels[i + 1] if i + 1 < len(levels) else None
            link_type = f"level_{i+1}" if next_level and not next_level.is_resource else "resource"

            chain = {
                "steps": [
                    {"action": "navigate"},
                    {"action": "smart_wait", "selector": _infer_selector(level.path_pattern)},
                    {"action": "extract_links", "source": "markdown", "link_type": link_type}
                ]
            }
            chains[chain_name] = chain
            chain_order.append(chain_name)

    # link_patterns: 每个非资源 Level 的 path_pattern
    for i, level in enumerate(levels):
        if not level.is_resource:
            key = f"level_{i+1}" if i + 1 < len(levels) and not levels[i+1].is_resource else "resource"
            if i == 0:
                key = f"level_1" if len(levels) > 1 else "resource"
            if key not in link_patterns:
                link_patterns[key] = []
            link_patterns[key].append(level.path_pattern)

    # 修正: link_patterns 的 key 应该对应 extract_links 的 link_type
    link_patterns_fixed = {}
    for i, level in enumerate(levels):
        if not level.is_resource and i + 1 < len(levels):
            next_level = levels[i + 1]
            # link_type 用下一个 level 的语义名称
            lt = _guess_link_type(next_level.path_pattern)
            if lt not in link_patterns_fixed:
                link_patterns_fixed[lt] = []
            link_patterns_fixed[lt].append(next_level.path_pattern)

    return {
        "name": site_name,
        "entry_points": [start_url],
        "link_patterns": link_patterns_fixed,
        "crawl_pattern": {
            "chain_order": chain_order,
            "chains": chains
        }
    }


def _infer_selector(path_pattern: str) -> str:
    """从 path_pattern 推断 smart_wait 选择器。"""
    # 提取路径中的关键词
    # /voddetail/\d+\.html → a[href*='/voddetail/']
    parts = path_pattern.strip('/').split('/')
    for part in parts:
        # 跳过纯数字占位符
        clean = re.sub(r'\\d\+', '', part).replace('\\.', '.').replace('.html','').replace('.htm','')
        if clean and clean not in ['', '-']:
            return f"a[href*='/{clean}/']"
    return "body"


def _guess_link_type(path_pattern: str) -> str:
    """从 path_pattern 推断 link_type 名称。"""
    keywords = {
        'detail': 'video_detail', 'voddetail': 'video_detail',
        'play': 'play_page', 'vodplay': 'play_page',
        'download': 'download_page',
        'episode': 'episode_page',
    }
    for kw, lt in keywords.items():
        if kw in path_pattern.lower():
            return lt
    # 通用: 用路径第一段
    parts = path_pattern.strip('/').split('/')
    for part in parts:
        clean = re.sub(r'\\d\+', '', part).replace('\\.', '').replace('.html','')
        if clean and clean not in ['', '-']:
            return f"{clean}_page"
    return "next_page"
```

---

## 5. 前端页面设计

### 页面布局

```
┌──────────────────────────────────────────────────────────────┐
│  ← 返回首页                                        添加网站  │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  网站名称: [          ]                                      │
│  起始URL:  [https://example.com    ] [打开浏览器]             │
│                                                              │
│  ─────────────── 浏览器打开后显示以下内容 ───────────────     │
│                                                              │
│  📍 采集路径                                                 │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Level 0: 列表页                                      │   │
│  │ URL: https://example.com/vodshow/1---------.html      │   │
│  │ 翻页模式: ❌ 未检测                                    │   │
│  │ [开始翻页检测]                                         │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ ➕ 请进入下一级页面，然后点击[添加路径]                 │   │
│  │ [添加路径]                                            │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  (添加路径后，Level 卡片和 检测资源 按钮出现)                │
│                                                              │
│  ───────────────────────────────────────────────────────     │
│  [完成]                                                      │
└──────────────────────────────────────────────────────────────┘
```

### Level 卡片

每个已添加的 Level 显示为一个卡片：

```
┌──────────────────────────────────────────────────────┐
│ ✅ Level 1: 详情页                                    │
│ 原始URL: /voddetail/456.html                         │
│ URL模式: /voddetail/\d+\.html                        │
│ [编辑]  ← 点击展开编辑框                               │
│ ┌────────────────────────────────────────────────┐   │
│ │ [/voddetail/\d+\.html                        ] │   │ ← 编辑框
│ │ [确认] [取消]                                   │   │
│ └────────────────────────────────────────────────┘   │
│                                                      │
│ [检测资源]  [添加路径]                                │
└──────────────────────────────────────────────────────┘
```

资源页卡片：

```
┌──────────────────────────────────────────────────────┐
│ 🎬 Level 2: 播放页 (资源页)                           │
│ 原始URL: /vodplay/456-1-1.html                       │
│ URL模式: /vodplay/\d+-\d+-\d+\.html                 │
│ [编辑]                                               │
│                                                      │
│ 资源: m3u8 - https://xxx.com/playlist.m3u8            │
│                                                      │
│ ✅ 采集路径已完成！                                   │
│ [确认保存]  [继续添加路径]                            │
└──────────────────────────────────────────────────────┘
```

---

## 6. 改动文件清单

| 文件 | 改动类型 | 说明 |
|------|----------|------|
| `crawler/guided_wizard.py` | **新增** | GuidedWizard 类：管理引导状态、层级、翻页检测、URL泛化、配置生成 |
| `site_manager.py` | **修改** | 新增 8 个 `/api/guided/*` 端点；删除 `/api/analyze` 端点 |
| `templates/wizard_guided.html` | **新增** | 引导式向导前端页面 |
| `templates/index.html` | **修改** | "HAR 录制"按钮 → "添加网站"；删除"自动分析"按钮及弹窗 |
| `crawler/config_wizard_har.py` | **保留不删** | 旧代码保留，暂不删除，但不再作为主入口 |

---

## 7. 明确不做的功能

| 功能 | 原因 |
|------|------|
| URL 不变的翻页检测（AJAX/load_more/scroll） | 实现复杂，后续迭代 |
| 多路径支持（同一层级多个 URL 模式） | 简化首次实现，后续可扩展 |
| 泛化结果实时预览 | 复杂度高，编辑框已足够 |
| 录制用户操作（点击/滚动） | browser-act 是命令式工具，无法监听用户操作 |
| 下拉框翻页 | 后续迭代 |
| 无限滚动翻页 | 后续迭代 |
| "加载更多"循环翻页 | 后续迭代 |

---

## 8. 测试场景

### 场景 1：MacCMS 网站（3级页面）

```
操作: 列表页1 → 翻到第2页 → 点进详情 → 点播放
预期:
  - 翻页模式: url_construct (maccms)
  - Level 0: 列表页 /vodshow/\d+-*-.html
  - Level 1: 详情页 /voddetail/\d+\.html
  - Level 2: 播放页(资源页) /vodplay/\d+-\d+-\d+\.html
  - 生成3条链: list_crawl + level_1 + stream_capture
```

### 场景 2：2级页面（详情页即播放页）

```
操作: 列表页 → 翻到第2页 → 点进详情(自带播放器)
预期:
  - 翻页模式: url_construct (maccms)
  - Level 0: 列表页
  - Level 1: 详情页(资源页) ← 添加路径后直接检测资源
  - 生成2条链: list_crawl + stream_capture
```

### 场景 3：4级页面

```
操作: 列表页 → 翻页 → 详情 → 剧集列表 → 播放
预期:
  - Level 0: 列表页 + 翻页
  - Level 1: 详情页
  - Level 2: 剧集列表
  - Level 3: 播放页(资源页)
  - 生成4条链: list_crawl + level_1 + level_2 + stream_capture
```

### 场景 4：翻页检测失败

```
操作: 用户未翻页就点"结束翻页检测"
预期:
  - 提示"URL未变化，请确认已翻页"
  - 按钮恢复为"开始翻页检测"，可重试
```

### 场景 5：检测资源失败

```
操作: 用户在非播放页点"检测资源"
预期:
  - 提示"未检测到资源"
  - 可重试
```
