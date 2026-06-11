# site-crawler 本地测试页面

## 任务
生成一套本地 HTML 测试页面，模拟视频网站完整流程，供 `config_wizard_refactored.py` 调试使用。

## 创建的文件
`site-crawler/test_pages/`
- `index.html` — 视频列表页，3 个测试视频链接
- `detail.html` — 详情页，显示视频标题 + 播放按钮
- `player.html` — 播放页，带 HLS 播放器（hls.js），加载公共测试流

## 流程
```
index.html → 点击"测试视频1"
    ↓
detail.html?id=1&title=测试视频1 → 点"▶ 播放"
    ↓
player.html?id=1&title=测试视频1&stream=...
    ↓
视频播放（m3u8 公共测试流）
```

## 技术细节
- 静态 HTML，URL 参数传递状态（无后端）
- 播放页使用 hls.js（CDN）播放 m3u8
- 测试流地址：`https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8`

## 使用方法
直接用浏览器打开 `test_pages/index.html`，或启动本地 HTTP 服务器：
```bash
cd site-crawler/test_pages && python -m http.server 8080
# 然后访问 http://localhost:8080/
```