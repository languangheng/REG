## 翻页检测策略升级：HTTP 枚举 → DOM 提取页码链接 → find_next_page() 回退

### 目标
解决 mimimi 类网站第一页 URL 无页码时的翻页检测问题。

### 改动
文件: `site-crawler/crawler/auto_config.py`

1. **删除**: `_try_click_next_page()` — 手动写的点击函数，逻辑弱
2. **新增**: `_extract_page_links_from_dom(client)` — 从翻页区域提取数字页码链接（只遍历 DOM，不 navigate）
3. **重写策略 2**: 
   - 从 DOM 提取第 2、3 页的 href
   - 用 `_detect_url_increment()` 比对两个 URL 差异
   - 识别页码位置，生成 template
   - **全程不需要 navigate/点击**
4. **策略 3**: `find_next_page()` + click — 当策略 2 拿不到页码链接时回退
5. **策略 4**: 纯 DOM 翻页检测 — 最终回退

### 关键代码
```python
# 策略2: 从 DOM 提取页码链接 → 比对 URL
page_links = _extract_page_links_from_dom(client)
if len(page_links) >= 2:
    url2 = page_links[0]
    url3 = page_links[1]
    # 比对 url2 和 url3，识别 template
```

### 测试场景
- mimimi: `/vodshow/12-----------.html` → 策略2 直接从翻页区域拿 href 比对
- 普通站: 页码已在 URL → 策略1 直接搞定
- SPA 站: URL 不变 → 策略3/4 回退