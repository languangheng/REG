# site-crawler 链接过滤升级记录

## 目标
将爬虫从"抓取所有链接"升级为"只抓取图片格式链接 + 视频详情页/视频格式链接"，同时将下一页检测从特定网站逻辑改为通用方案。

## 变更内容

### 1. 链接分类过滤 (parser.py)
- `PageLinks` 字段从 `links` 改为 `image_links` + `video_links` + `total_links`
- `_is_image_url()`: 匹配图片扩展名(.jpg/.png/.gif/.webp/.svg等) + 图片路径关键词(/image/,/img/,/pic/,/thumb/等)
- `_is_video_url()`: 匹配视频扩展名(.mp4/.m3u8等) + 视频详情页路径模式(/voddetail/,/video/,/play/,/movie/,/detail/等)
- 修复: `/vod[\w-]*/\d+\.html` 模式过于宽泛误匹配 `/vodtype/`，改为精确列出 `/voddetail/`、`/vod-play/`、`/vod-detail/`

### 2. 通用下一页检测 (parser.py - find_next_page_url)
5层策略依次尝试：
1. **ARIA/无障碍标记**: aria-label="next", rel="next"
2. **链接文本匹配**: 中英文+符号（下一页/Next/>/›/»/≫等），正则预编译缓存
3. **URL query参数**: ?page=2→3, ?p=2→3, ?pg=2→3 等10+常见参数名
4. **URL路径页码**: /page/2→3, /list-2.html→3.html, /p/2→3
5. **URL数字位递增**: 最后兜底，路径中最后一个数字递增

### 3. 导出适配 (exporter.py)
- JSON 输出字段: `image_links` + `video_links` (替代原 `links`)
- 页面统计: `image_count` + `video_count` + `total_on_page`

## 测试结果
- URL: mimimi.top 熟女人妻分类 2页
- 图片链接: 8条（logo/icon，封面图因懒加载未出现在Markdown中）
- 视频链接: 106条（全部为 /voddetail/ 详情页，无误分类）
- 下一页检测: 正确识别 ---.html → ---2---.html

## 已知限制
- browser-act Markdown 输出中懒加载图片URL缺失，需要后续通过页面滚动或JS执行来解决
