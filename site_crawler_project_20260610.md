# Site Crawler 项目创建

## 目标
基于 browser-act CLI 创建 Python 网站爬虫，抓取页面视频链接和图片 URL。

## 技术决策
- **底层**: browser-act CLI（通过 subprocess 调用），使用已有的 chrome-direct 浏览器
- **架构**: 分层模块 — browser_act(封装层) / parser(解析器) / exporter(导出)
- **输出**: JSON 文件
- **验证码**: 遇到 Cloudflare 暂停等用户手动处理
- **图片**: 只收集 URL，不下载；支持懒加载 (data-original)
- **视频**: 只收集详情页链接 (/voddetail/xxx.html)
- **去重**: 暂不做

## 测试结果
目标: mimimi.top 精品色情列表页
- 视频链接: 22 条 (voddetail)
- 图片 URL: 12 条 (懒加载缩略图)
- JSON 输出正常

## 项目路径
`C:\Users\languangheng\.qclaw\workspace-tfxjjhfnjialcuju\site-crawler\`

## 关键修复
1. browser-act `--session` 参数逻辑：browser open 需要但 browser list 不需要
2. Windows GBK 终端编码：用 io.TextIOWrapper 包装 stdout/stderr
3. 懒加载图片：markdown 无法获取，需额外获取 HTML 并用正则匹配 data-original
