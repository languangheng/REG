"""数据导出层 - JSON 输出，按页面标题命名文件"""

import json
import re
from pathlib import Path
from crawler.parser import PageLinks
from crawler.logger import get_logger

_log = get_logger("exporter")


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

        _log.info("导出开始: title=%s, filename=%s, pages=%d", title, filename, len(pages))

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
            # 统计 deep_results 中的资源数量，更新 top-level 字段
            deep_video = deep_results.get("video", [])
            deep_art = deep_results.get("art", [])
            deep_streams = sum(1 for v in deep_video if v.get("stream_url"))
            deep_images = sum(len(v.get("images", [])) for v in deep_video)
            deep_images += sum(len(v.get("images", [])) for v in deep_art)
            data["total_videos"] = max(data["total_videos"], len(deep_video))
            data["total_images"] = max(data["total_images"], deep_images)
            # 流数量是独立维度
            data["total_streams"] = deep_streams

        out_path = Path(output_dir) / filename
        out_path.parent.mkdir(parents=True, exist_ok=True)

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        _log.info("导出完成: path=%s, images=%d, videos=%d, arts=%d, streams=%d",
                  str(out_path), data["total_images"], data["total_videos"], data["total_art_details"], data.get("total_streams", 0))
        return str(out_path)

