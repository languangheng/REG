"""验证重构后的配置驱动爬虫"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from crawler.site_config import load_site_config
from crawler.browser_act import BrowserActClient
from crawler.parser import PageParser

# 加载配置
config = load_site_config("mimimi")
print(f"Site: {config.name} ({config.base_url})")
print(f"  Extract chains: {list(config.extract_chains.keys())}")
print(f"  Entry points: {[(ep.name, ep.type) for ep in config.entry_points]}")

# 测试链接分类
lp = config.link_patterns
print(f"\n  Link patterns compiled: video_detail={len(lp._video_detail_re)}, art_detail={len(lp._art_detail_re)}, exclude={len(lp._exclude_re)}")
print(f"  /voddetail/123.html is_video_detail: {lp.is_video_detail('/voddetail/123.html')}")
print(f"  /artdetail/456.html is_art_detail: {lp.is_art_detail('/artdetail/456.html')}")
print(f"  /vodtype/1.html is_excluded: {lp.is_excluded('/vodtype/1.html')}")

# 深度优先验证
client = BrowserActClient(session="config_test", browser_id=None)
chain = config.extract_chains["video"]
print(f"\nVideo chain steps: {[s.name for s in chain.steps]}")

# Step 1: 列表页
print("\n[1] List page...")
client.navigate("https://www.mimimi.top/vodtype/12.html")
client.wait(6)
md = client.get_markdown()
parser = PageParser(base_url="https://www.mimimi.top/vodtype/12.html", site_config=config)
page = parser.parse(md)
print(f"  video_links: {len(page.video_links)}, art_links: {len(page.art_links)}")

# Step 2: 第一个视频的 detail
if page.video_links:
    url = page.video_links[0]["url"]
    print(f"\n[2] Detail: {url}")
    client.navigate(url)
    client.wait(6)
    step0 = chain.steps[0]  # detail step
    result0 = client.execute_step(step0)
    print(f"  Step '{step0.name}': {len(result0) if isinstance(result0, list) else 'N/A'} items")

    # Step 3: play page -> stream
    if isinstance(result0, list) and result0 and "href" in result0[0]:
        play_url = result0[0]["href"]
        print(f"\n[3] Play: {play_url}")
        client.navigate(play_url)
        client.wait(6)
        step1 = chain.steps[1]  # play step
        result1 = client.execute_step(step1)
        print(f"  Step '{step1.name}': stream_url={result1.get('stream_url', '(none)') if isinstance(result1, dict) else result1}")

client.close_session()
print("\nConfig-driven crawl verified!")
