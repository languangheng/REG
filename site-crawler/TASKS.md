# 项目任务看板

> 本文件记录所有待办/进行中/已完成的任务，与 WORKFLOW.md 流程绑定。
> 每个任务必须走：Plan → 审批 → 实现 → 验证 → 提交。

## 已完成任务

| # | 任务 | 类型 | Commit |
|---|------|------|--------|
| F1 | screenshot — 页面截图 | 🔧 底层 | `6d3bac5` |
| F2 | back / forward / reload — 浏览器导航 | 🔧 底层 | `5e3cf23` |
| F3 | input_text + press_key — 表单输入 | 🔧 底层 | `040fc9e` |
| F4 | wait_selector — 精确等待元素 | 🔧 底层 | `91173ac` |
| F5 | Cookie 持久化 — cookies get/set/export/import | 🔧 底层 | `2de67f8` |
| I5 | Cookie 自动复用集成到 ensure_session | 🔗 接入 | `63d345d` |
| I4 | wait_selector 替换 time.sleep | 🔗 接入 | `5404689` |
| 整理 | 项目临时文件整理到 tmp/_archive | 🧹 运维 | `ee070b7` |
| 文档 | TASKS.md + WORKFLOW.md 更新 | 📝 文档 | `ab6a346` |

## 暂停任务

| # | 任务 | 类型 | 原因 |
|---|------|------|------|
| F6 | select 下拉选择 | 🔧 底层 | mimimi.top 无原生 select，验证场景不匹配，代码已回滚 |

## 当前任务

无（I4 待用户验收后提交）

## 待办任务（按执行顺序）

| # | 任务 | 类型 | 依赖 | 预期收益 |
|---|------|------|------|---------|
| I1 | screenshot 调试截图集成 | 🔗 接入 | F1✅ | 翻页/出错时截图，调试更直观 |
| I2 | back 返回列表页集成 | 🔗 接入 | F2✅ | 详情页爬完 back() 返回，避免重加载过 CF |
| F7 | dialog 弹窗处理（底层封装） | 🔧 底层 | — | 3 个方法：accept/dismiss/status |
| I7 | dialog 自动关闭弹窗集成 | 🔗 接入 | F7 | 自动关闭 Cookie 同意/广告弹窗 |
| F8 | 精确元素提取（底层封装） | 🔧 底层 | — | get_text/get_value/get_html --selector |
| I8 | 精确提取替代正则集成 | 🔗 接入 | F8 | 提升提取准确率 |
| I6 | select 多线路视频抓取集成 | 🔗 接入 | F6 | 依赖 F6 完成，当前暂停 |

## 执行原则

- **底层封装 → 业务接入 → 立即看到收益**
- 每个任务独立 commit，可独立回滚
- 验证脚本统一放 `tmp/` 目录
- 任务状态变更必须同步更新本文件
- 未验证通过的功能代码必须回滚
