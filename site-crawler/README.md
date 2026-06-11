# Site Crawler

基于 browser-act CLI 的网站链接爬虫，自动翻页抓取所有链接直到最后一页。

## 安装

```bash
# 无第三方 Python 依赖，仅需 browser-act CLI
uv tool install browser-act-cli --python 3.12
```

## 使用

```bash
# 默认爬取 mimimi.top 熟女人妻分类
python crawler.py

# 指定 URL
python crawler.py "https://www.example.com/list/1"

# 限制最大页数
python crawler.py --max-pages 5

# 指定输出目录
python crawler.py -d ./output

# 指定 browser-act 会话和浏览器
python crawler.py --session mysession --browser-id direct_local_xxx
```

## 参数

| 参数 | 简写 | 默认值 | 说明 |
|------|------|--------|------|
| url | | `https://www.mimimi.top/vodshow/12-----------.html` | 起始页 URL |
| --output-dir | -d | `.` | JSON 输出目录 |
| --session | -s | `crawl` | browser-act 会话名 |
| --browser-id | -b | 自动检测 | 已有浏览器 ID |
| --wait | -w | 10 | 每页等待秒数 |
| --max-pages | | 100 | 最大爬取页数 |
| --no-close | | | 完成后不关闭浏览器会话 |

## 输出

JSON 文件，以页面标题短名命名，包含：
- `start_url`: 起始 URL
- `total_pages`: 总页数
- `total_links`: 去重后总链接数
- `pages`: 各页信息（URL、标题、链接数）
- `links`: 所有去重链接（text + url）

## 项目结构

```
site-crawler/
├── crawler.py              # 入口脚本
├── crawler/
│   ├── __init__.py
│   ├── browser_act.py      # browser-act CLI 封装
│   ├── parser.py           # 页面解析（链接提取 + 下一页检测）
│   └── exporter.py         # JSON 导出（文件名安全处理）
└── requirements.txt
```
