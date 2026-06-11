# 自动分析 UI 功能实现

## 目标
在站点管理 UI 加"输入 URL → auto_config 自动分析"功能，替代手动配置向导。

## 实现

### 前端 (templates/index.html)
- 顶部新增 **🔍 自动分析** 按钮（替代原"添加网站"按钮）
- Auto Analyze Modal：输入 URL → SSE 实时显示日志 → 展示分析结果
- 结果展示：网站名、翻页类型、提取链等，一键保存
- 可展开查看 YAML 原文

### 后端 (site_manager.py)
- `GET /api/analyze?url=xxx` — SSE 端点，运行 auto_config 并实时推送日志
- `POST /api/analyze/save` — 保存分析结果到 sites.yaml
- `_analyze_result_cache` — 缓存分析结果，保存时取出

### 用户体验
1. 输入列表页 URL
2. 点"开始分析" → 实时看日志（翻页识别、链接聚类、流地址捕获）
3. 分析完成看结果摘要
4. 一键保存配置

## 待优化
- 当前日志是分析完后一次性推送（auto_config 是同步函数，无法流式推送）
- 可考虑重构 auto_config 为生成器或回调模式实现真正的实时流
