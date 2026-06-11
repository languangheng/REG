"""数据导出层 - JSON 输出，按页面标题命名文件"""

import json
import re
from pathlib import Path
from crawler.parser import PageLinks


def sanitize_filename(title: str, max_length: int = 50) -> str:
    """将标题转为安全的文件名。"""
    name = re.sub(r'[\\/:*?"<>|]', '_', title)
    name = re.sub(r'\s+', ' ', name).strip()
    name = name.strip('.')
    if len(name) > max_length:
        name = name[:max_length]
    if not name:
        name = "crawl_result"
    return name


class JSONExporter:
    """将多页爬取结果导出为 JSON 文件。"""

    def save(self, pages: list[PageLinks], start_url: str, output_dir: str = ".",
             deep_results: dict | None = None, **kwargs) -> str:
        """保存所有页面爬取结果到 JSON 文件。"""
        title = pages[0].page_title if pages else "crawl_result"
        short_title = title.split('-')[0].strip() if '-' in title else title
        filename = sanitize_filename(short_title) + ".json"

        # 合并所有链接（分类去重）
        all_images: list[dict] = []
        all_videos: list[dict] = []
        all_arts: list[dict] = []
        seen_img: set[str] = set()
        seen_vid: set[str] = set()
        seen_art: set[str] = set()

        for page in pages:
            for link in page.image_links:
                if link["url"] not in seen_img:
                    seen_img.add(link["url"])
                    all_images.append(link)
            for link in page.video_links:
                if link["url"] not in seen_vid:
                    seen_vid.add(link["url"])
                    all_videos.append(link)
            for link in page.art_links:
                if link["url"] not in seen_art:
                    seen_art.add(link["url"])
                    all_arts.append(link)

        data = {
            "start_url": start_url,
            "title": title,
            "total_pages": len(pages),
            "total_images": len(all_images),
            "total_videos": len(all_videos),
            "total_art_details": len(all_arts),
            "pages": [
                {
                    "page_number": i + 1,
                    "page_url": p.page_url,
                    "page_title": p.page_title,
                    "image_count": len(p.image_links),
                    "video_count": len(p.video_links),
                    "art_count": len(p.art_links),
                    "total_on_page": p.total_links,
                }
                for i, p in enumerate(pages)
            ],
            "image_links": all_images,
            "video_links": all_videos,
            "art_detail_links": all_arts,
        }

        if deep_results:
            data["deep_results"] = deep_results

        out_path = Path(output_dir) / filename
        out_path.parent.mkdir(parents=True, exist_ok=True)

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return str(out_path)

    @staticmethod
    def print_summary(pages: list[PageLinks], output_path: str) -> None:
        """打印爬取摘要。"""
        total_img = sum(len(p.image_links) for p in pages)
        total_vid = sum(len(p.video_links) for p in pages)
        total_art = sum(len(p.art_links) for p in pages)

        unique_img: set[str] = set()
        unique_vid: set[str] = set()
        unique_art: set[str] = set()
        for p in pages:
            for link in p.image_links:
                unique_img.add(link["url"])
            for link in p.video_links:
                unique_vid.add(link["url"])
            for link in p.art_links:
                unique_art.add(link["url"])

        print(f"\n{'='*50}")
        print(f"  爬取完成！")
        print(f"  总页数: {len(pages)}")
        print(f"  图片链接: {len(unique_img)} 条 (去重后)")
        print(f"  视频链接: {len(unique_vid)} 条 (去重后)")
        print(f"  图片详情页: {len(unique_art)} 条 (去重后)")
        print(f"  输出文件: {output_path}")
        print(f"{'='*50}")

        for i, p in enumerate(pages, 1):
            print(f"  第{i}页: {p.page_url} (图片:{len(p.image_links)} 视频:{len(p.video_links)} 图详情:{len(p.art_links)} 总:{p.total_links})")

        # 图片链接预览
        if unique_img:
            img_list = []
            seen = set()
            for p in pages:
                for link in p.image_links:
                    if link["url"] not in seen:
                        seen.add(link["url"])
                        img_list.append(link)
            print(f"\n🖼️ 图片链接预览 (前10条):")
            for i, link in enumerate(img_list[:10], 1):
                print(f"  {i}. {link['url']}")
            if len(img_list) > 10:
                print(f"  ... 还有 {len(img_list) - 10} 条")

        # 视频链接预览
        if unique_vid:
            vid_list = []
            seen = set()
            for p in pages:
                for link in p.video_links:
                    if link["url"] not in seen:
                        seen.add(link["url"])
                        vid_list.append(link)
            print(f"\n🎬 视频链接预览 (前10条):")
            for i, link in enumerate(vid_list[:10], 1):
                text = link["text"][:40] if link["text"] else "(无文本)"
                print(f"  {i}. {text}")
                print(f"     {link['url']}")
            if len(vid_list) > 10:
                print(f"  ... 还有 {len(vid_list) - 10} 条")

        # 图片详情页预览
        if unique_art:
            art_list = []
            seen = set()
            for p in pages:
                for link in p.art_links:
                    if link["url"] not in seen:
                        seen.add(link["url"])
                        art_list.append(link)
            print(f"\n🖼️ 图片详情页预览 (前10条):")
            for i, link in enumerate(art_list[:10], 1):
                text = link["text"][:50] if link["text"] else "(无文本)"
                print(f"  {i}. {text}")
                print(f"     {link['url']}")
            if len(art_list) > 10:
                print(f"  ... 还有 {len(art_list) - 10} 条")
