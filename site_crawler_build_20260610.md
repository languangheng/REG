# site-crawler 项目构建记录

## 目标
创建基于 browser-act CLI 的 Python 网站链接爬虫，自动翻页抓取所有链接直到最后一页。

## 实现方案
- **底层**: browser-act CLI（subprocess 调用），通过 Chrome Direct 浏览器处理 JS 渲染和 Cloudflare 验证
- **模块划分**:
  - `crawler/browser_act.py` — browser-act CLI 封装（navigate/get_markdown/wait/close 等）
  - `crawler/parser.py` — 页面解析：提取所有链接 + 识别"下一页"URL（文本匹配 + URL 页码递增推断）
  - `crawler/exporter.py` — JSON 导出，按页面标题短名命名文件，处理 Windows 特殊字符和长度限制
  - `crawler.py` — 入口，自动翻页循环

## 关键设计
1. **自动翻页**: 先匹配链接文本（"下一页"/"Next"等），再从 URL 页码模式推断下一页
2. **URL 页码推断**: mimimi.top 格式 `/vodshow/12-----------.html`（第1页）→ `/vodshow/12--------2---.html`（第2页），通过替换倒数第4个`-`为页码
3. **去重**: 全局 URL 集合去重，每页链接也各自去重
4. **文件名安全**: 取标题第一个`-`前部分，限制50字符，替换 Windows 非法字符

## 测试结果
- URL: `https://www.mimimi.top/vodshow/12-----------.html`
- 2页共 430 条链接，去重后 263 条，其中 voddetail 链接 106 条
- 输出文件: `熟女人妻.json`

## 默认测试地址
`https://www.mimimi.top/vodshow/12-----------.html`
