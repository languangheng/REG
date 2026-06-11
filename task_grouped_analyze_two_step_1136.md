# 两步式分组分析 — 实施与测试

## 目标
将自动分析从"一键分析"改为两步交互：发现分组 → 用户勾选 → 按勾选分析

## 改动文件
1. **`crawler/auto_config.py`** — 新增 `discover_groups()` 函数
2. **`site_manager.py`** — 新增 `/api/analyze/discover` + `/api/analyze/groups`，删除旧 `/api/analyze`
3. **`templates/index.html`** — 两步 UI + fetch SSE 读取

## 用户要求
- YAML 只保留新格式（dict of dicts），不做旧格式兼容
- 首页复选框删除，统一走 discover + groups 流程
- 分组默认全不勾选，用户手动勾选

## 测试结果
- ✅ `/api/analyze/discover` 返回 36 个分组，JSON 格式正确
- ✅ Flask 重启后前端正常加载

## 教训
修改后端代码后必须自己重启 Flask 并测试验证，不要等用户反馈错误。
