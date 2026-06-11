# 自动分析UI实时日志反馈

## Objective
修复"自动分析"功能点击后无UI反馈的问题，实现日志实时推送到前端。

## Key Changes
1. `crawler/auto_config.py`: 新增 `on_log` 回调参数，每条日志实时触发
2. `site_manager.py` `/api/analyze` SSE端点: 从"跑完再推"改为"边跑边推"，使用 `queue.Queue` + sentinel 实现线程间日志传递

## Conclusions
- 根因：后端在后台线程跑完 `auto_config` 后才一次性推送日志
- 方案：`on_log` 回调 → Queue → SSE 实时推送
- 前端无需修改，已支持实时渲染
