# 翻页检测优化：scroll_to_bottom()

## 目标
优化 `_find_page_number_buttons()` 的滚动性能，从 8次 `scroll_down()` (9秒+) 改为 1次 JS 跳转 (~1.5秒)

## 改动

### 1. browser_act.py
新增 `scroll_to_bottom()` 方法：
```python
def scroll_to_bottom(self) -> str:
    """滚动到页面底部（JS 一次跳到底，比多次 scroll_down 快）。"""
    return self._run("eval", "window.scrollTo(0, document.body.scrollHeight)", timeout=10)
```

### 2. auto_config.py
重写 `_find_page_number_buttons()` 为 3 级策略：
1. **预检**：先快照 DOM，看页码按钮是否已存在（避免不必要滚动）
2. **JS 跳到底部**：`scroll_to_bottom()` 一次跳转
3. **兜底**：遍历全 DOM（最慢）

## 测试结果
- ✅ mimimi.top 翻页检测成功
- ✅ 模板推断正确：`/vodshow/12-----{page}------.html`
- ✅ 端到端 auto_config 成功（链接提取→详情页→流捕获→配置生成）

## 性能提升
- 之前：8次 `scroll_down()` + 额外 sleep = ~9秒
- 现在：`scroll_to_bottom()` + 1.5秒 = ~1.5秒
- **提升 ~6 倍**