# HAR 录制模式验证报告

> 时间：2026-06-10 22:40

## 验证结论：✅ 全部通过，方案可行

### 已验证的 browser-act 关键能力

| 能力 | 命令 | 结果 |
|------|------|------|
| 列表页元素获取 | `state` | ✅ 返回带 index 的可交互元素列表，链接文本清晰 |
| 点击元素 | `click <index>` | ✅ 正常跳转（注意：需先 `state` 刷新 snapshot，否则报 "previous frame document" 错误） |
| HAR 开始录制 | `network har start` | ✅ |
| HAR 停止并保存 | `network har stop <path>` | ✅ 输出标准 HAR JSON，205 条请求 |
| 网络请求过滤 | `network requests --filter m3u8` | ✅ 直接捕获 m3u8 流地址（含 mime_type、timestamp） |
| 页面导航 | `navigate <url>` | ✅ |
| 会话管理 | `browser open` / `session close` | ✅ |

### 关键发现

1. **`network requests --filter m3u8` 比 HAR 更直接**：能直接获取 m3u8 URL，无需解析整个 HAR 文件
2. **HAR 作为完整录制方案**：记录用户浏览全路径，可事后分析 URL pattern
3. **`state` 的 snapshot 时效性**：页面导航后必须重新 `state` 才能点击，否则报错 "Snapshot element belongs to a previous frame document"
4. **HAR 数据结构**：标准 HAR 1.2 JSON 格式，PowerShell `ConvertFrom-Json` 可直接解析
5. **m3u8 提取路径**：从 HAR 中可通过 `request.url -match "m3u8"` 直接提取

### mimimi.top 站点 URL 结构（从验证中确认）

- 列表页：`/vodshow/{cate}-----------.html`
- 详情页：`/voddetail/{id}.html`
- 播放页：`/vodplay/{id}-{line}-{ep}.html`
- m3u8 域名：`lbbf9.com`（解析服务 `aojiexi.com`）

### 下一步：实现 HAR 录制向导

设计思路：
1. Python 启动 browser-act session + `network har start`
2. 用户在浏览器中自由浏览（入口页 → 详情页 → 播放页）
3. Python 轮询 `state` 检测页面变化，记录 URL 序列
4. 用户完成后 Python 调 `network har stop` 保存
5. 分析 HAR 数据：
   - URL 序列 → 生成 URL pattern（正则替换数字/ID 为捕获组）
   - m3u8 请求 → 提取流地址规则
6. 自动生成 sites.yaml 配置

### 仍需验证

- [ ] `network requests --filter` 支持哪些过滤条件（域名？资源类型？）
- [ ] 多个视频的 m3u8 域名是否一致（决定是否需要动态提取）
- [ ] CF 验证页面的处理策略（当前需等待 5-10 秒自动通过）
