# 爬虫方案重构 Plan — 基于 browser-act 全能力评估

> 时间：2026-06-10 22:50
> 目标：视频资源 + 图片资源爬取，最大化利用 browser-act 现有能力

---

## 一、当前代码的问题诊断

### 现有架构（crawler.py）

```
列表页爬取循环:
  navigate(url) → wait(8s) → get_markdown() → PageParser 解析 markdown 文本
  → 正则匹配链接 → 分类(video/art/image) → 找下一页 URL → 循环

深度爬取:
  navigate(详情页URL) → wait(6s) → evaluate_js(extract_js) → 解析 JS 返回
  → navigate(播放页URL) → wait(6s) → evaluate_js(extract_js) → 获取 stream_url
```

### 核心瓶颈

| 问题 | 原因 | 影响 |
|------|------|------|
| **每页等 8 秒** | `wait stable` 等页面完全加载 | 100 页 = 800 秒 ≈ 13 分钟仅列表页 |
| **markdown 解析丢失信息** | `get_markdown()` 把 DOM 转文本，丢失 class、data-* 等属性 | 无法按 UI 语义分类链接 |
| **链接分类靠正则猜** | `PageParser` 用 URL 路径正则 + 扩展名匹配 | 误分类、漏分类严重 |
| **深度爬取逐页串行** | 每个详情页都要 navigate + wait + eval | 50 个视频 = 50 × 12s = 10 分钟 |
| **extract_js 脆弱** | JS 写死在 YAML 里，页面改版就废 | 维护成本高 |
| **stealth-extract 被 CF 拦截** | 无 cookie 的无头浏览器过不了 CF | 此路不通 |

---

## 二、browser-act 能力 vs 当前使用情况

| 能力 | 当前是否使用 | 可替代什么 | 价值 |
|------|:---:|------|------|
| `state` — 获取交互元素列表（带 index、class、role） | ❌ | `get_markdown` + 正则解析 | **极高** — 直接拿到结构化元素，零解析 |
| `click <index>` — 按序号点击 | ❌ | `navigate(下一页URL)` | **高** — 不用猜下一页 URL |
| `network requests --filter` — 按关键词过滤网络请求 | ❌ | `evaluate_js(提取m3u8)` | **极高** — 直接拿到流地址，不用写 JS |
| `network requests --type xhr,fetch` — 过滤 AJAX 请求 | ❌ | 无 | **高** — 发现 API 端点 |
| `network har start/stop` — HAR 录制 | ❌ | 无 | **高** — 全程录制，事后分析 |
| `network request <id>` — 单请求详情（含响应体） | ❌ | `evaluate_js(fetch)` | **中** — 可拿到 API 返回的 JSON |
| `get markdown` — 页面转 Markdown | ✅ | — | 已用，但信息丢失 |
| `evaluate_js` — 执行 JS | ✅ | — | 已用，但脆弱 |
| `stealth-extract` — 无头抓取 | ❌ | 整个浏览器 | CF 拦截，不可用 |
| `scroll` — 滚动 | ❌ | 无 | **中** — 触发懒加载 |
| `remote-assist` — 生成远程操作链接 | ❌ | 无 | **中** — 用户手动操作时配合 |

---

## 三、方案设计（4 个，从激进到保守）

---

### 方案 A：Network-First（纯网络请求驱动）⭐ 推荐

**核心思想**：不解析页面内容，只监控网络请求。浏览器负责渲染和点击，Python 只关心"出来了什么请求"。

```
1. 打开入口页 → network clear → 点击分类筛选 → network requests
   → 发现 API 端点（XHR/JSON）→ 直接调 API 拿列表

2. 如果没有 API：
   打开列表页 → state 获取视频链接 index → 逐个 click
   → 每次点击后 network requests --filter m3u8 → 收集流地址

3. 图片：打开详情页 → scroll 触发懒加载
   → network requests --type image → 收集图片 URL
   → 或 evaluate_js 提取 img src（简单可靠）
```

**优势**：
- ✅ **零 markdown 解析** — 不再丢失信息
- ✅ **零 extract_js** — 不再维护脆弱的 JS 脚本
- ✅ **`network requests --filter m3u8` 直接出流地址** — 已验证可用
- ✅ **发现隐藏 API** — 很多网站前端调 API，直接抓 API 效率提升 10x
- ✅ **`state` 代替 `get_markdown`** — 结构化元素列表，精准点击
- ✅ **`click` 代替 URL 拼接** — 不用猜下一页

**劣势**：
- ⚠️ 需要浏览器全程在线（不能 stealth-extract 走无头）
- ⚠️ 部分网站 API 有签名/token，不能直接调
- ⚠️ 需要先探索再爬取（两阶段）

**适用场景**：大部分有 JS 渲染的视频/图片站

**预估提速**：
- 列表页：`state`(1-2s) vs `get_markdown+wait`(8-10s) → **4-5x**
- 流地址：`network requests`(1s) vs `navigate+wait+eval`(12s) → **10x+**
- 如果发现 API：直接调 API → **50x+**

---

### 方案 B：HAR 录制 + 事后分析（用户引导式）

**核心思想**：用户手动操作浏览器浏览一个完整路径，Python 录制全程 HAR，事后分析生成配置和提取数据。

```
1. browser open → network har start
2. 用户在浏览器中自由操作（可给 remote-assist 链接）
3. Python 每 3 秒轮询 state，记录 URL 变化序列
4. 用户说"完成" → network har stop
5. 分析：
   - URL 序列 → 生成 URL pattern → sites.yaml 的 link_patterns
   - m3u8 请求 → 生成 extract_chains 的规则
   - 图片请求 → 生成 art 的提取规则
6. 用生成的配置跑方案 A 的自动爬取
```

**优势**：
- ✅ **配置向导的最优解** — 不用写 JS，不用猜正则
- ✅ **用户体验好** — 只需正常浏览一次
- ✅ **自动生成 sites.yaml** — 新站点零配置
- ✅ **和方案 A 互补** — B 生成配置，A 执行爬取

**劣势**：
- ⚠️ 每个新站点需要人工操作一次
- ⚠️ 事后分析 HAR 的逻辑复杂（URL pattern 生成需要启发式）
- ⚠️ 不能批量爬取（只是配置工具，不是爬虫本身）

**适用场景**：添加新站点的配置向导

---

### 方案 C：API 优先探测 + 降级策略

**核心思想**：先探测网站是否有可用的后端 API，有则直接调 API（最快），没有则降级到浏览器方案。

```
Phase 1: API 探测
  打开列表页 → network clear → 等待加载
  → network requests --type xhr,fetch --status 200
  → 检查响应中是否有 JSON 数据（含列表/分页信息）
  → 如果发现 API：记录 endpoint、参数格式

Phase 2: API 模式（如果 Phase 1 成功）
  直接用 requests/httpx 调 API
  → 无需浏览器 → 速度极快
  → 需要处理：cookie/token/签名

Phase 3: 浏览器降级（如果 API 不可用）
  走方案 A 的 state + click + network requests 流程
```

**优势**：
- ✅ **最优情况极快** — 纯 API 调用，秒级爬完
- ✅ **渐进式** — 自动选择最优路径
- ✅ **降级安全** — API 不行就走浏览器

**劣势**：
- ⚠️ API 签名/鉴权可能很复杂
- ⚠️ 三个 Phase 的代码量较大
- ⚠️ API 格式各站不同，难以通用化

**适用场景**：有后端 API 的现代网站（React/Vue SPA）

---

### 方案 D：混合方案（当前代码渐进改造）⭐ 务实

**核心思想**：在现有代码基础上，逐步用 browser-act 新能力替换慢路径，不重写。

```
Step 1: 列表页提速
  现有: navigate → wait(8s) → get_markdown → 正则解析
  改为: navigate → wait(3s) → state → 按元素 class/index 分类链接
  → 找下一页: state 中找 "下一页" 按钮的 index → click

Step 2: 流地址提取提速
  现有: navigate(详情页) → wait → navigate(播放页) → wait → eval JS
  改为: navigate(播放页) → wait(3s) → network requests --filter m3u8
  → 不用写 extract_js，直接从网络请求拿

Step 3: 图片提取提速
  现有: navigate → wait → eval JS 提取 img src
  改为: navigate → wait → scroll 触发懒加载
  → network requests --type image（或保留简单 eval JS，这个本来就可靠）

Step 4: 配置向导
  用方案 B 的 HAR 录制生成 sites.yaml
```

**优势**：
- ✅ **风险最低** — 渐进式改造，每步可验证
- ✅ **向后兼容** — sites.yaml 格式不变
- ✅ **立竿见影** — Step 1+2 就能大幅提速

**劣势**：
- ⚠️ 架构不够干净（混合新旧方式）
- ⚠️ 不会发现隐藏 API（没有 Phase 1 探测）

---

## 四、方案对比总表

| 维度 | A: Network-First | B: HAR 向导 | C: API 优先 | D: 渐进改造 |
|------|:---:|:---:|:---:|:---:|
| **爬取速度** | ⭐⭐⭐⭐ | N/A（配置工具） | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **代码量** | 中 | 中 | 大 | 小 |
| **维护成本** | 低 | 中 | 高 | 低 |
| **新站点适配** | 需配置 | 自动生成 | 自动探测 | 需配置 |
| **风险** | 中 | 低 | 高 | 最低 |
| **兼容现有 sites.yaml** | 需调整 | 生成配置 | 需调整 | 完全兼容 |

---

## 五、我的推荐

### 🏆 最优组合：D（渐进改造）+ B（HAR 向导）

理由：
1. **D 立刻见效** — Step 1+2 改造后，现有爬虫速度提升 3-5x
2. **B 解决新站点** — 添加新站点不再手写配置
3. **A 的核心思想融入 D** — 用 `state` + `network requests` 替代 `get_markdown` + `eval JS`
4. **C 作为未来增强** — API 探测可以在 D 稳定后加入

### 具体执行顺序

1. **BrowserActClient 补充方法**（`network_requests`, `har_start/stop`, `parse_state`）
2. **Step 1: 列表页改造** — `state` 替代 `get_markdown`，`click` 替代 URL 拼接
3. **Step 2: 流地址改造** — `network requests --filter m3u8` 替代 `eval JS`
4. **Step 3: 图片提取改造** — `scroll` + `network requests --type image` 或保留 eval
5. **Step 4: HAR 配置向导** — `config_wizard_har.py`
6. **Step 5（可选）: API 探测** — Phase 1 探测逻辑

---

## 六、browser-act 补充方法设计

需要给 `BrowserActClient` 新增的方法：

```python
def network_requests(self, filter_str="", req_type="", method="", status="") -> list[dict]:
    """获取网络请求列表，返回结构化数据。"""
    
def network_request_detail(self, request_id: str) -> dict:
    """获取单个请求的详情（含响应体）。"""
    
def network_clear(self) -> str:
    """清除已跟踪的网络请求。"""
    
def har_start(self) -> str:
    """开始 HAR 录制。"""
    
def har_stop(self, path: str = "") -> str:
    """停止 HAR 录制并保存。"""

def parse_state(self) -> StateSnapshot:
    """解析 state 输出为结构化对象。"""
    # 返回: url, title, elements: [{index, tag, class, text, title, href, role, ...}]
```

`parse_state` 是关键 — 把 `state` 的文本输出解析成结构化数据，后续所有操作都基于它。

---

## 七、需要你决策

1. **选哪个方案？** A / B / D / D+B / 其他组合？
2. **sites.yaml 格式是否可以改？** 如果走方案 A，extract_chains 中的 extract_js 可以简化或删除
3. **先改哪一步？** 推荐从 Step 1（列表页提速）开始，还是你想先做 HAR 向导？
4. **API 探测（方案 C）要不要？** 还是先不碰？
