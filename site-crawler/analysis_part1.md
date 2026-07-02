# 快速验证 vs 完整爬取 逻辑差异分析

## 一、调用链路总览

| 维度 | 完整爬取 | 快速验证 |
|------|---------|---------|
| 前端按钮 | 完整爬取 | 验证 |
| API端点 | /api/crawl/key | /api/crawl/test/key |
| CLI模块 | crawler.group_crawler | crawler.engine_cli |
| 引擎模式 | bfs | dfs |

## 二、核心差异

### 1. 后端API差异

完整爬取 api_crawl():
- 调用: python -m crawler.group_crawler --site key --deep-limit 0
- mode=bfs, deep-limit=0(不限), max-pages=50

快速验证 api_crawl_test():
- 调用: python -m crawler.engine_cli --site key --mode dfs
- mode=dfs, deep-limit=1(默认