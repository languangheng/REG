# Site Crawler 项目掌握报告

## 一、项目定位

网站爬虫管理系统，两大核心能力：
1. 引导用户配置新网站的采集规则（向导式交互）
2. 按规则自动爬取网站资源（视频流 m3u8/mp4、图片等）

技术栈：Python + Flask + browser-act CLI（Playwright 浏览器自动化）
运行地址：http://localhost:5050，无第三方依赖（仅标准库+Flask）。

## 二、架构

```
用户浏览器 (localhost:5050)
    ↓ HTTP API / SSE
Flask 后端 (site_manager.py) ─ 20+ API 端点
    ↓ CLI 调用
browser-act ─ 持久化 Playwright 会话
    ↓ 真实渲染
目标网站
```

## 三、核心模块

| 文件 |
