# HAR录制UI简化：去掉实时刷新，停止后一次性展示

## 目标
简化录制 UI：开始录制只提示状态，停止后一次性展示全部结果，去掉 SSE 实时推送和定时刷新。

## 改动

### wizard_har.html (完全重写)
- 去掉 SSE 连接 (`EventSource`)、定时轮询、`handleEvent`、`logPanel`
- 开始录制 → 显示红色 ⏺ 覆盖层"录制中..."
- 停止录制 → 调 `/api/har/stop`，一次性渲染 summary
- 左侧：浏览路径（步骤、页面类型标签）
- 右侧：流地址 / API / 图片分组展示
- 生成配置 → 追加 YAML 到右侧

### site_manager.py
- `/api/har/start`：去掉 `_har_broadcast` 调用，后台 poll 只收集数据
- `/api/har/stop`：返回 `summary` 字段（steps/streams/images/apis）
- SSE 端点 `/api/har/events` 暂保留（不影响）

## 用户体验变化
- 录制中：无任何 UI 更新，只有红色覆盖层提示
- 停止后：瞬间渲染全部结果，干净利落
