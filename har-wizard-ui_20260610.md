# HAR 录制向导 Web UI 实施

> 时间: 2026-06-10 23:45

## 目标
为 HAR 配置向导添加实时录制面板，让用户看到录制状态和浏览路径

## 已完成

### 1. 新增 `templates/wizard_har.html`
- 顶栏：录制状态（红色脉冲动画"录制中"）+ 开始/停止/生成配置按钮
- 左侧面板：实时浏览路径树（显示页面序号、URL path、标题、页面类型标签、检测到的资源标签）
- 右侧面板：检测结果分组展示（m3u8/mp4/图片/API）+ 底部实时日志
- 底栏：统计数据（页面数/m3u8/mp4/图片/API）+ 当前 URL
- SSE 实时推送：页面变化、流地址检测、图片检测

### 2. 新增 API 端点（site_manager.py）
- `GET /wizard_har` — HAR 向导页面
- `POST /api/har/start` — 开始录制（启动后台轮询线程）
- `GET /api/har/events` — SSE 实时事件流
- `POST /api/har/stop` — 停止录制
- `POST /api/har/generate` — 生成配置并保存到 sites.yaml

### 3. 修改 `templates/index.html`
- 顶栏添加 "🎬 HAR 录制" 绿色按钮
- 点击弹出新窗口打开向导

### 4. 修改 `config_wizard_har.py`
- HarWizard 新增 `_broadcast` 属性，支持外部注入广播函数

## 页面类型自动识别
- `/vodshow|/vodtype|/arttype` → 列表页
- `/voddetail|/detail` → 详情页
- `/vodplay|/play|/video/play` → 播放页
- `/artdetail` → 图集页

## 架构
```
浏览器 ←→ site_manager.py (Flask) ←→ HarWizard ←→ BrowserActClient ←→ browser-act
     ↕ SSE                ↕ Python 轮询线程
wizard_har.html     _har_broadcast → SSE → 前端 handleEvent
```

## 验证
- Flask app 加载成功，所有路由注册 ✅
- `GET /wizard_har` 返回 200，页面 14KB ✅
- 完整录制流程待端到端验证（需手动操作浏览器）
