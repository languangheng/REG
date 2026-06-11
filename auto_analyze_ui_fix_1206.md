# 自动分析 UI 实时日志推送修复

## 问题
1. UI 按钮在日志下方，会被日志内容覆盖
2. 点击「发现分组」后，日志没有实时推送到前端，用户无法看到当前分析状态

## 修复内容

### 1. UI 布局调整（templates/index.html）
- 按钮区移到顶部：所有按钮（取消、发现分组、开始分析勾选项）放在输入框下方、分组列表上方
- 按钮区始终可见，不受日志区域影响

### 2. SSE 实时推送修复（site_manager.py）
**根因**：Flask SSE 响应在 `generate()` 产出第一个数据前不会发送响应头，导致前端无法建立连接

**修复**：
1. 在 `t.start()` 后立即 yield 一个心跳：`yield ": connected\n\n"`，确保 SSE 连接立即建立
2. 添加 SSE 响应头：
   - `X-Accel-Buffering: no` - 禁用 Nginx 缓冲
   - `Cache-Control: no-cache` - 禁用缓存
   - `Connection: keep-alive` - 保持连接

## 验证方式
重启服务后，打开 http://localhost:5050，点击「自动分析」，输入 URL 后点击「发现分组」，观察日志是否实时出现在右侧区域。

## 文件修改
- `templates/index.html` - 按钮布局调整
- `site_manager.py` - SSE 连接立即建立 + 响应头优化
