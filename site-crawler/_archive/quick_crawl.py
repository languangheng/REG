"""Quick crawl: each type 1 page list, deep into 3 videos for stream URLs."""
import sys, io, json, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from crawler.browser_act import BrowserActClient
from crawler.parser import PageParser
from crawler.exporter import JSONExporter

# 网站分类
CATEGORIES = {
    "movie":  {"name": "电影", "url": "https://www.mimimi.top/vodshow/1-----------.html"},
    "series": {"name": "剧集", "url": "https://www.mimimi.top/vodshow/2-----------.html"},
    "anime":  {"name": "动漫", "url": "https://www.mimimi.top/vodshow/4-----------.html"},
    "variety":{"name": "综艺", "url": "https://www.mimimi.top/vodshow/5-----------.html"},
}

DEEP_COUNT = 3  # 每类深入3个视频
WAIT = 6        # 等待秒数（缩短）

def main():
    client = BrowserActClient(session="quick_crawl", browser_id=None)
    all_results = {}

    for cat_key, cat_info in CATEGORIES.items():
        cat_name = cat_info["name"]
        cat_url = cat_info["url"]
        print(f"\n{'='*50}")
        print(f"[{cat_name}] 列表页: {cat_url}")
        print(f"{'='*50}")

        # 第1步：列表页
        try:
            client.navigate(cat_url)
            client.wait(WAIT)
            md = client.get_markdown()
            parser = PageParser(base_url=cat_url)
            page = parser.parse(md)
            vod_links = page.video_links[:DEEP_COUNT]
            print(f"  共 {len(page.video_links)} 个视频, 取前 {DEEP_COUNT} 个深入")
        except Exception as e:
            print(f"  列表页失败: {e}")
            all_results[cat_key] = {"error": str(e)}
            continue

        # 第2步：深入每个视频
        vod_results = []
        for i, link in enumerate(vod_links, 1):
            title = link.get("text", "")[:50]
            url = link["url"]
            print(f"\n  [{i}/{len(vod_links)}] {title}")
            print(f"         detail: {url}")

            try:
                client.navigate(url)
                client.wait(WAIT)
                play_links = client.get_voddetail_play_links()

                # 进入第一个播放页取流地址
                stream_url = None
                player_iframe = None
                if play_links:
                    play_url = play_links[0]["href"]
                    print(f"         play: {play_url}")
                    client.navigate(play_url)
                    client.wait(WAIT)
                    stream = client.get_vodplay_stream_url()
                    stream_url = stream.get("stream_url")
                    player_iframe = stream.get("player_iframe")

                vod_results.append({
                    "title": title,
                    "detail_url": url,
                    "play_count": len(play_links),
                    "stream_url": stream_url,
                    "player_iframe": player_iframe,
                })
                s = stream_url or "(none)"
                print(f"         stream: {s[:80]}")
            except Exception as e:
                print(f"         失败: {e}")
                vod_results.append({
                    "title": title, "detail_url": url,
                    "play_count": 0, "stream_url": None,
                    "player_iframe": None, "error": str(e),
                })

        all_results[cat_key] = {
            "category": cat_name,
            "list_url": cat_url,
            "total_on_page": len(page.video_links),
            "deep_crawled": len(vod_results),
            "results": vod_results,
        }

    # 关闭会话
    try:
        client.close_session()
    except Exception:
        pass

    # 保存结果
    output_file = "quick_crawl_results.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    # 打印摘要
    print(f"\n{'='*60}")
    print("  SUMMARY")
    print(f"{'='*60}")
    for cat_key, data in all_results.items():
        if "error" in data:
            print(f"  [{data.get('category', cat_key)}] FAILED: {data['error']}")
            continue
        results = data.get("results", [])
        streams = [r for r in results if r.get("stream_url")]
        print(f"  [{data['category']}] {len(results)} crawled, {len(streams)} got stream URL")
        for r in results:
            mark = "OK" if r.get("stream_url") else "MISS"
            print(f"    [{mark}] {r['title'][:40]}")

    print(f"\nResults saved to {output_file}")


if __name__ == "__main__":
    main()
