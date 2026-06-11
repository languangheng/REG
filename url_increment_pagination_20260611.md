# URL递增翻页 + CF复用修复

## 目标
1. CF 复用：自动分析时复用已有浏览器会话，避免重复 CF 验证
2. URL 递增翻页：快速识别 URL 数字递增模式（如 3-6.html → 3-7.html），无需浏览器交互

## 实现

### CF 复用 (site_manager.py)
- `api_analyze` 的 BrowserActClient 加了 `browser_id="direct_local_100797252049567848"`
- 复用 HAR 录制已通过 CF 的浏览器会话

### URL 递增翻页 (auto_config.py)
- 新增 `_detect_url_increment(url)` 函数：
  - 正则匹配 URL path 中最后一个数字段
  - 排除 >500 的大数字（可能是 ID 而非页码）
  - 构建下一页 URL 并 HTTP 验证是否存在
  - 返回 template、current_val、next_url

- Step 1.5 流程改为：
  1. 先尝试 URL 递增检测（纯 HTTP，不走 CF）
  2. 验证成功 → ptype="url_increment"，跳过 DOM 检测
  3. 验证失败 → 回退到滚动+DOM 翻页检测

- 配置输出新增 pagination.url_template 和 pagination.start_page

## 测试
- 服务已重启 (localhost:5050)
- 待用户实际测试 mimimi 站点
