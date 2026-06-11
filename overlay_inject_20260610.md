# 覆盖层注入验证通过

## 目标
验证 `config_wizard.py` 的 `OVERLAY_JS` 能否成功注入到浏览器页面，显示配置向导弹窗。

## 问题链
1. **`browser-act eval -` 不支持** — 正确参数是 `--stdin`
2. **Python subprocess stdin 传超长 JS 报 surrogate 编码错误** — `browser-act` 内部 Node.js 无法处理 Python 传入的 UTF-8 bytes
3. **解决方案**：写临时 `.js` 文件 → 用 PowerShell `Get-Content | browser-act eval --stdin` pipe 传递

## 修复内容
- `browser_act.py` 的 `_eval_via_stdin` 方法：改用临时文件 + PowerShell pipe 方式传递超长 JS
- `browser_act.py` 的 `evaluate_js`：`len > 500` 时走 stdin 路径

## 验证结果
- 极简 JS 注入：✅
- OVERLAY_JS 注入：✅（返回 `(no return value)`，IIFE 无返回值正常）
- `cw-panel` 元素：FOUND ✅
- `__crawler_wizard` 标记：true ✅

## 待办
- 用户确认浏览器中能看到配置向导面板
- 测试完整 `run_wizard` 流程（从 Flask 界面触发）
