# site-crawler 图片提取修复记录

## 问题
arttype/8.html 图片分类页只提取到 8 条 logo/icon 图片，封面图全部缺失。

## 根因
封面图不是 `<img>` 标签，而是 **CSS `background-image`** 属性。browser-act 的 `get-markdown` 只输出 Markdown 链接，不包含 background-image 信息。

## 解决方案
在 `BrowserActClient.get_all_image_urls()` 中，JS 提取逻辑增加：
1. `<img>` 标签的 src + data-src + data-original + data-lazySrc（原有）
2. **所有含 `style*="background"` 元素的 `getComputedStyle(el).backgroundImage`**（新增）

JS 代码通过正则 `url(["']?([^"')]+)["']?)` 从 `backgroundImage` 值中提取实际 URL。

## 结果
- 图片链接: 8 条 → **32 条**（2页去重后）
- 封面图域名: `pic.milfxbase.icu`（`/picart/` 和 `/pic/` 路径）
- 视频链接: 21 条 voddetail（无误分类）

## 修改文件
- `crawler/browser_act.py` — `get_all_image_urls()` 增加 background-image 提取
