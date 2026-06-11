# Config Wizard 可行性论证与执行计划

> 时间：2026-06-10 22:30

---

## 一、两个方案对比

### 方案 A：旧版 `config_wizard.py`（JS 端状态管理）

```
Python 注入一次性 JS → JS 用 sessionStorage 跨页面保持状态 → 用户交互在 JS 内完成
→ 最终 JS 写 window.__cw_result → Python 轮询读取
```

**优点**：
- 页面跳转后 JS 自动重新执行（sessionStorage 持久化）
- 用户操作响应即时，无 2 秒轮询延迟

**致命问题**：
- sessionStorage 在 `window.load` 之前不可用，重新注入时机不确定
- 跨域跳转时 sessionStorage 丢失（不同域不共享）
- JS 状态恢复逻辑复杂，已产生多个 bug（state 丢失、覆盖层重复注入）

### 方案 B：重构版 `config_wizard_refactored.py`（Python 端状态管理）

```
Python 维护 wizard_state → 每次注入 JS 覆盖层（传入当前 state）
→ JS 渲染 UI + 用户操作写 window.__cw_event → Python 轮询（2秒）
→ handle_event() 更新 state → 下一轮注入
```

**优点**：
- Python 是唯一状态源，不会丢失
- 覆盖层是无状态的，注入即用

**致命问题**：
- **页面跳转后覆盖层消失**：用户点击链接 → 页面导航 → 注入的 JS/DOM 全部清除 → Python 需要重新注入
- **2 秒轮询延迟**：用户点按钮后最多等 2 秒才能响应
- **JS 注入不稳定**：`evaluate_js` 在页面导航中可能失败（页面未加载完）
- **已有 JS 语法错误**：`OVERLAY_JS_STATELESS` 中 CSS 通过 `%s` 字符串格式化注入，转义问题多

---

## 二、根本问题分析

两个方案的共同瓶颈是：**browser-act eval 的生命周期 < 页面导航的生命周期**。

```
eval 注入 JS → JS 在当前页面 DOM 中存活
→ 页面导航 → 新页面加载 → 注入的 JS 全部消失
→ Python 需要重新注入 → 但何时注入？（页面加载时机不确定）
```

旧版用 sessionStorage 尝试绕过，但跨域/时机问题太多。
重构版用 Python 轮询 + 重注入，但 2 秒间隔意味着 UI 体验差且可能漏事件。

**核心矛盾**：覆盖层（overlay）方案要求 JS 在浏览器中持续存在，但 browser-act 的 eval 机制不支持这一点。

---

## 三、可行方案重新梳理

### 方案 1：纯 Python CLI 向导（无覆盖层）

**思路**：完全不在浏览器中注入 UI，改用终端交互。

```
Python 打开入口页 → 调用 browser-act state 获取页面元素列表
→ 终端显示链接列表，用户输入编号选择
→ Python 调用 browser-act navigate 跳转
→ 终端显示详情页元素，用户选择播放按钮
→ Python 调用 browser-act network requests 捕获 m3u8
→ 生成配置写入 sites.yaml
```

**可行性**：✅ 高
- 完全避开 JS 注入问题
- `browser-act state` 返回可交互元素列表（带 index）
- `browser-act network requests --filter m3u8` 可捕获流地址
- 用户在终端操作，零延迟

**缺点**：
- 用户体验不如可视化（但作为 v1 够用）
- 需要终端交互（不能通过 webchat 远程操作）

### 方案 2：覆盖层 + remote-assist 混合

**思路**：利用 browser-act 的 `remote-assist` 生成远程链接，用户在真实浏览器中操作，覆盖层只做辅助提示。

```
Python 打开入口页 → 注入覆盖层（仅提示文字，不拦截交互）
→ 用户在浏览器中正常点击链接
→ Python 用 network requests 监控导航
→ 检测到页面变化后重新注入提示
```

**可行性**：⚠️ 中
- 覆盖层降级为"提示条"，不做事件拦截，JS 复杂度大幅降低
- 但仍然依赖 Python 轮询检测页面变化
- remote-assist 可能让用户在手机上操作，但增加了不确定性

### 方案 3：两阶段法（先录制，后生成配置）

**思路**：不在过程中注入任何 JS，而是用 HAR 录制用户的浏览路径，事后分析生成配置。

```
Python 启动 HAR 录制 → 用户自由浏览（入口页 → 详情页 → 播放页）
→ 用户完成后通知 Python → 停止录制
→ 分析 HAR：提取 URL pattern、m3u8 流地址、页面跳转链
→ 自动生成 sites.yaml
```

**可行性**：✅ 高
- browser-act 有 `network har start/stop` 命令
- 零 JS 注入，零状态管理
- 用户体验最自然：正常浏览即可

**缺点**：
- 需要事后分析 HAR 数据，逻辑较复杂
- URL pattern 生成可能不够精确（需要启发式规则）

### 方案 4：重构覆盖层方案（修复当前方案 B）

**思路**：在方案 B 基础上，修复 JS 注入时机问题。

```
Python 轮询 window.location.href 检测导航
→ 检测到变化后 wait stable → 重新注入覆盖层
→ 缩短轮询间隔到 0.5 秒（减少延迟）
```

**可行性**：⚠️ 中低
- 仍有轮询延迟
- `wait stable` 可能超时
- 页面快速跳转可能漏检
- JS 注入的编码问题（中文 → 英文已绕过，但仍有 CSS 格式化等坑）

---

## 四、推荐执行计划

### 推荐：方案 1（纯终端 CLI） + 方案 3（HAR 录制） 分步实施

理由：
1. 方案 1 最简单、最可靠，可以最快验证端到端流程
2. 方案 3 作为 v2 增强，用户体验最好
3. 两者不冲突，方案 1 的配置生成逻辑可以复用到方案 3

### 执行步骤（请你逐个确认）

---

**Step 1：验证 browser-act 关键能力**

在终端手动验证以下命令是否可用：
- `browser-act --session test state` → 确认能获取页面交互元素列表
- `browser-act --session test network requests --filter m3u8` → 确认能捕获网络请求
- `browser-act --session test network har start/stop` → 确认 HAR 录制能力
- `browser-act --session test click <index>` → 确认能按 index 点击元素

**目的**：确认方案 1 和方案 3 的技术基础

---

**Step 2：实现方案 1 的 CLI 向导原型**

用纯 Python 实现：
1. 打开入口页 → `state` 获取元素列表 → 终端打印链接
2. 用户输入编号 → `click <index>` 点击
3. 跳转详情页 → `state` → 用户选择播放按钮
4. `network requests --filter m3u8` 或 eval JS 提取流地址
5. 生成 URL pattern + 写入 sites.yaml

**输出**：`crawler/config_wizard_cli.py`

---

**Step 3：端到端测试**

用 mimimi.top 走一遍完整流程，确认生成的 sites.yaml 和手动写的等价

---

**Step 4（可选 v2）：实现方案 3 的 HAR 录制模式**

1. `network har start` → 用户自由浏览
2. `network har stop` → 解析 HAR JSON
3. 从 HAR 中提取：访问的 URL 序列 → URL pattern 生成；网络请求中的 m3u8 → 流地址
4. 自动生成 sites.yaml

---

**Step 5（可选 v3）：Web UI 集成**

将 CLI 向导集成到 `site_manager.py` 的 Flask UI 中，用 SSE 推送进度

---

## 五、需要你确认的决策

1. **方案选择**：你倾向方案 1（纯终端）、方案 3（HAR 录制），还是坚持修复覆盖层方案？
2. **Step 1 是否现在执行**：我可以立即帮你跑 browser-act 的验证命令
3. **mimimi.top 是否作为测试目标**：还是有其他网站？
4. **向导的最终交互形式**：终端 CLI？还是必须在浏览器 UI 中操作？
