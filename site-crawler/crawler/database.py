"""SQLite 数据库存储层 — 爬取结果的持久化、搜索、断点续抓。

设计：
  - SQLite WAL 模式，支持并发读
  - FTS5 全文索引（title + stream_url）
  - crawled_urls 表实现断点续抓（SHA256[:16] 哈希去重）
  - 连接线程本地化（threading.local），多线程安全

表结构：
  crawl_sessions     — 每次爬取会话
  crawl_results      — 单条爬取结果
  crawl_images       — 结果关联的图片
  crawl_log          — 步骤日志
  crawled_urls       — URL 爬取历史（断点续抓核心）
  crawl_results_fts  — FTS5 全文索引
"""

import hashlib
import os
import sqlite3
import threading
from datetime import datetime, timezone, timedelta

from crawler.logger import get_logger

_log = get_logger("database")

_TZ = timezone(timedelta(hours=8))


def _db_path() -> str:
    proj = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(proj, "data")
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, "crawler.db")


# ── 连接管理（线程本地） ──────────────────────────────────

_local = threading.local()


def get_conn() -> sqlite3.Connection:
    if not hasattr(_local, "conn") or _local.conn is None:
        conn = sqlite3.connect(_db_path(), timeout=30)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.row_factory = sqlite3.Row
        _local.conn = conn
    return _local.conn


def close_conn():
    if hasattr(_local, "conn") and _local.conn:
        _local.conn.close()
        _local.conn = None


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS crawl_sessions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    site_key        TEXT NOT NULL,
    site_name       TEXT NOT NULL,
    base_url        TEXT NOT NULL DEFAULT '',
    mode            TEXT NOT NULL DEFAULT 'bfs',
    group_name      TEXT NOT NULL DEFAULT '',
    workers         INTEGER NOT NULL DEFAULT 1,
    started_at      TEXT NOT NULL,
    finished_at     TEXT,
    status          TEXT NOT NULL DEFAULT 'running',
    total_results   INTEGER NOT NULL DEFAULT 0,
    total_streams   INTEGER NOT NULL DEFAULT 0,
    total_images    INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS crawl_results (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      INTEGER NOT NULL REFERENCES crawl_sessions(id) ON DELETE CASCADE,
    group_name      TEXT NOT NULL DEFAULT '',
    resource_type   TEXT NOT NULL DEFAULT 'video',
    title           TEXT NOT NULL DEFAULT '',
    detail_url      TEXT NOT NULL DEFAULT '',
    stream_url      TEXT NOT NULL DEFAULT '',
    stream_format   TEXT NOT NULL DEFAULT '',
    page_url        TEXT NOT NULL DEFAULT '',
    crawled_at      TEXT NOT NULL,
    crawl_status    TEXT NOT NULL DEFAULT 'done'
);
CREATE INDEX IF NOT EXISTS idx_results_session ON crawl_results(session_id);
CREATE INDEX IF NOT EXISTS idx_results_group ON crawl_results(session_id, group_name);
CREATE INDEX IF NOT EXISTS idx_results_resource ON crawl_results(resource_type);
CREATE INDEX IF NOT EXISTS idx_results_crawled_at ON crawl_results(crawled_at);

CREATE TABLE IF NOT EXISTS crawl_images (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    result_id       INTEGER NOT NULL REFERENCES crawl_results(id) ON DELETE CASCADE,
    url             TEXT NOT NULL,
    idx             INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_images_result ON crawl_images(result_id);

CREATE TABLE IF NOT EXISTS crawl_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      INTEGER NOT NULL REFERENCES crawl_sessions(id) ON DELETE CASCADE,
    result_id       INTEGER,
    step_name       TEXT NOT NULL DEFAULT '',
    message         TEXT NOT NULL DEFAULT '',
    level           TEXT NOT NULL DEFAULT 'info',
    created_at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_log_session ON crawl_log(session_id);

CREATE TABLE IF NOT EXISTS crawled_urls (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    url_hash        TEXT NOT NULL UNIQUE,
    url             TEXT NOT NULL,
    site_key        TEXT NOT NULL,
    group_name      TEXT NOT NULL DEFAULT '',
    resource_type   TEXT NOT NULL DEFAULT '',
    crawl_status    TEXT NOT NULL DEFAULT 'pending',
    first_seen      TEXT NOT NULL,
    last_crawled    TEXT,
    result_id       INTEGER REFERENCES crawl_results(id) ON DELETE SET NULL,
    error_msg       TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_urls_site ON crawled_urls(site_key, group_name);
CREATE INDEX IF NOT EXISTS idx_urls_status ON crawled_urls(crawl_status);

CREATE VIRTUAL TABLE IF NOT EXISTS crawl_results_fts USING fts5(
    title,
    stream_url,
    detail_url,
    content='crawl_results',
    content_rowid='id'
);

CREATE TRIGGER IF NOT EXISTS results_ai AFTER INSERT ON crawl_results BEGIN
    INSERT INTO crawl_results_fts(rowid, title, stream_url, detail_url)
    VALUES (new.id, new.title, new.stream_url, new.detail_url);
END;

CREATE TRIGGER IF NOT EXISTS results_ad AFTER DELETE ON crawl_results BEGIN
    INSERT INTO crawl_results_fts(crawl_results_fts, rowid, title, stream_url, detail_url)
    VALUES ('delete', old.id, old.title, old.stream_url, old.detail_url);
END;

CREATE TRIGGER IF NOT EXISTS results_au AFTER UPDATE ON crawl_results BEGIN
    INSERT INTO crawl_results_fts(crawl_results_fts, rowid, title, stream_url, detail_url)
    VALUES ('delete', old.id, old.title, old.stream_url, old.detail_url);
    INSERT INTO crawl_results_fts(rowid, title, stream_url, detail_url)
    VALUES (new.id, new.title, new.stream_url, new.detail_url);
END;
"""


def init_db():
    conn = get_conn()
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    _log.info("数据库初始化完成: %s", _db_path())


# ── URL 哈希 ─────────────────────────────────────────────

def _url_hash(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def _now() -> str:
    return datetime.now(_TZ).isoformat(timespec="seconds")


# ── 会话操作 ─────────────────────────────────────────────

def create_session(
    site_key: str,
    site_name: str,
    base_url: str = "",
    mode: str = "bfs",
    group_name: str = "",
    workers: int = 1,
) -> int:
    conn = get_conn()
    cur = conn.execute(
        """INSERT INTO crawl_sessions (site_key, site_name, base_url, mode, group_name, workers, started_at, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, 'running')""",
        (site_key, site_name, base_url, mode, group_name, workers, _now()),
    )
    conn.commit()
    sid = cur.lastrowid
    _log.info("会话创建: id=%d, site=%s, mode=%s, group=%s, workers=%d",
              sid, site_key, mode, group_name, workers)
    return sid


def finish_session(session_id: int, total_results: int = 0,
                   total_streams: int = 0, total_images: int = 0,
                   status: str = "done"):
    conn = get_conn()
    conn.execute(
        """UPDATE crawl_sessions
           SET finished_at = ?, status = ?, total_results = ?,
               total_streams = ?, total_images = ?
           WHERE id = ?""",
        (_now(), status, total_results, total_streams, total_images, session_id),
    )
    conn.commit()
    _log.info("会话结束: id=%d, status=%s, results=%d, streams=%d",
              session_id, status, total_results, total_streams)


# ── 结果写入 ─────────────────────────────────────────────

def insert_result(
    session_id: int,
    group_name: str = "",
    resource_type: str = "video",
    title: str = "",
    detail_url: str = "",
    stream_url: str = "",
    stream_format: str = "",
    page_url: str = "",
    images: list | None = None,
    crawl_status: str = "done",
) -> int:
    conn = get_conn()
    now = _now()

    cur = conn.execute(
        """INSERT INTO crawl_results
           (session_id, group_name, resource_type, title, detail_url,
            stream_url, stream_format, page_url, crawled_at, crawl_status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (session_id, group_name, resource_type, title, detail_url,
         stream_url, stream_format, page_url, now, crawl_status),
    )
    result_id = cur.lastrowid

    if images:
        for idx, img_url in enumerate(images):
            conn.execute(
                "INSERT INTO crawl_images (result_id, url, idx) VALUES (?, ?, ?)",
                (result_id, img_url, idx),
            )

    if detail_url:
        _upsert_crawled_url(conn, detail_url, "", group_name, resource_type, "done", result_id)
    if stream_url:
        _upsert_crawled_url(conn, stream_url, "", group_name, resource_type, "done", result_id)

    conn.commit()
    return result_id


def _upsert_crawled_url(conn, url, site_key, group_name, resource_type,
                        crawl_status, result_id=0):
    uh = _url_hash(url)
    now = _now()
    existing = conn.execute(
        "SELECT id, crawl_status FROM crawled_urls WHERE url_hash = ?", (uh,)
    ).fetchone()
    if existing:
        conn.execute(
            """UPDATE crawled_urls
               SET crawl_status = ?, last_crawled = ?, result_id = ?
               WHERE url_hash = ?""",
            (crawl_status, now, result_id or None, uh),
        )
    else:
        conn.execute(
            """INSERT INTO crawled_urls
               (url_hash, url, site_key, group_name, resource_type,
                crawl_status, first_seen, last_crawled, result_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (uh, url, site_key, group_name, resource_type,
             crawl_status, now, now, result_id or None),
        )


def mark_url_failed(url: str, site_key: str = "", group_name: str = "",
                    resource_type: str = "", error_msg: str = ""):
    conn = get_conn()
    uh = _url_hash(url)
    now = _now()
    existing = conn.execute(
        "SELECT id FROM crawled_urls WHERE url_hash = ?", (uh,)
    ).fetchone()
    if existing:
        conn.execute(
            "UPDATE crawled_urls SET crawl_status = 'failed', last_crawled = ?, error_msg = ? WHERE url_hash = ?",
            (now, error_msg, uh),
        )
    else:
        conn.execute(
            """INSERT INTO crawled_urls
               (url_hash, url, site_key, group_name, resource_type,
                crawl_status, first_seen, last_crawled, error_msg)
               VALUES (?, ?, ?, ?, ?, 'failed', ?, ?, ?)""",
            (uh, url, site_key, group_name, resource_type, now, now, error_msg),
        )
    conn.commit()


def insert_log(session_id: int, step_name: str = "", message: str = "",
               level: str = "info", result_id: int = 0):
    conn = get_conn()
    conn.execute(
        """INSERT INTO crawl_log (session_id, result_id, step_name, message, level, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (session_id, result_id or None, step_name, message, level, _now()),
    )
    conn.commit()


# ── 断点续抓 ─────────────────────────────────────────────

def is_url_crawled(url: str) -> bool:
    conn = get_conn()
    uh = _url_hash(url)
    row = conn.execute(
        "SELECT crawl_status FROM crawled_urls WHERE url_hash = ?", (uh,)
    ).fetchone()
    return row is not None and row["crawl_status"] == "done"


def filter_uncrawled(urls: list) -> list:
    if not urls:
        return []
    conn = get_conn()
    hashes = {_url_hash(u): u for u in urls}
    placeholders = ",".join("?" for _ in hashes)
    rows = conn.execute(
        f"SELECT url_hash FROM crawled_urls WHERE url_hash IN ({placeholders}) AND crawl_status = 'done'",
        list(hashes.keys()),
    ).fetchall()
    done_hashes = {r["url_hash"] for r in rows}
    return [u for u in urls if _url_hash(u) not in done_hashes]


# ── 查询与搜索 ───────────────────────────────────────────

def _has_cjk(text: str) -> bool:
    """检测文本是否包含 CJK 字符。"""
    return any('\u4e00' <= c <= '\u9fff' or '\u3040' <= c <= '\u30ff' or '\uac00' <= c <= '\ud7af' for c in text)


def _build_fts_query(user_query: str) -> str:
    """构建 FTS5 查询（仅用于纯英文/数字查询）。"""
    q = user_query.strip().replace('"', '')
    if not q:
        return q
    terms = q.split()
    return " OR ".join(f"{t}*" for t in terms if t)


def _build_search_condition(query: str) -> tuple[str, list]:
    """根据查询内容构建搜索条件。

    中文/CJK：使用 LIKE 模糊匹配（title + stream_url）。
    英文/数字：使用 FTS5 全文索引。

    返回 (sql_condition, params)。
    """
    if not query:
        return "", []

    if _has_cjk(query):
        # 中文：LIKE 模糊匹配
        like_pattern = f"%{query}%"
        return "(r.title LIKE ? OR r.stream_url LIKE ? OR r.detail_url LIKE ?)", [
            like_pattern, like_pattern, like_pattern,
        ]
    else:
        # 英文/数字：FTS5
        fts_q = _build_fts_query(query)
        if not fts_q:
            return "", []
        return "r.id IN (SELECT rowid FROM crawl_results_fts WHERE crawl_results_fts MATCH ?)", [fts_q]


def search_results(
    query: str = "",
    site_key: str = "",
    group_name: str = "",
    resource_type: str = "",
    crawl_status: str = "",
    offset: int = 0,
    limit: int = 50,
) -> list:
    conn = get_conn()
    conditions = []
    params = []

    if query:
        cond, p = _build_search_condition(query)
        if cond:
            conditions.append(cond)
            params.extend(p)
    if site_key:
        conditions.append("s.site_key = ?")
        params.append(site_key)
    if group_name:
        conditions.append("r.group_name = ?")
        params.append(group_name)
    if resource_type:
        conditions.append("r.resource_type = ?")
        params.append(resource_type)
    if crawl_status:
        conditions.append("r.crawl_status = ?")
        params.append(crawl_status)

    where = " AND ".join(conditions) if conditions else "1=1"
    sql = f"""
        SELECT r.*, s.site_key, s.site_name
        FROM crawl_results r
        JOIN crawl_sessions s ON r.session_id = s.id
        WHERE {where}
        ORDER BY r.crawled_at DESC
        LIMIT ? OFFSET ?
    """
    params.extend([limit, offset])

    rows = conn.execute(sql, params).fetchall()
    results = []
    for row in rows:
        d = dict(row)
        img_rows = conn.execute(
            "SELECT url FROM crawl_images WHERE result_id = ? ORDER BY idx",
            (d["id"],),
        ).fetchall()
        d["images"] = [r2["url"] for r2 in img_rows]
        results.append(d)

    return results


def search_count(
    query: str = "",
    site_key: str = "",
    group_name: str = "",
    resource_type: str = "",
    crawl_status: str = "",
) -> int:
    conn = get_conn()
    conditions = []
    params = []

    if query:
        cond, p = _build_search_condition(query)
        if cond:
            conditions.append(cond)
            params.extend(p)
    if site_key:
        conditions.append("s.site_key = ?")
        params.append(site_key)
    if group_name:
        conditions.append("r.group_name = ?")
        params.append(group_name)
    if resource_type:
        conditions.append("r.resource_type = ?")
        params.append(resource_type)
    if crawl_status:
        conditions.append("r.crawl_status = ?")
        params.append(crawl_status)

    where = " AND ".join(conditions) if conditions else "1=1"
    sql = f"SELECT COUNT(*) FROM crawl_results r JOIN crawl_sessions s ON r.session_id = s.id WHERE {where}"
    row = conn.execute(sql, params).fetchone()
    return row[0] if row else 0


def get_results_by_session(session_id: int, limit: int = 500, offset: int = 0) -> list:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM crawl_results WHERE session_id = ? ORDER BY crawled_at DESC LIMIT ? OFFSET ?",
        (session_id, limit, offset),
    ).fetchall()
    results = []
    for row in rows:
        d = dict(row)
        img_rows = conn.execute(
            "SELECT url FROM crawl_images WHERE result_id = ? ORDER BY idx",
            (d["id"],),
        ).fetchall()
        d["images"] = [r2["url"] for r2 in img_rows]
        results.append(d)
    return results


def get_sessions(site_key: str = "", limit: int = 20, offset: int = 0) -> list:
    conn = get_conn()
    if site_key:
        rows = conn.execute(
            "SELECT * FROM crawl_sessions WHERE site_key = ? ORDER BY started_at DESC LIMIT ? OFFSET ?",
            (site_key, limit, offset),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM crawl_sessions ORDER BY started_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
    return [dict(r) for r in rows]


def get_site_stats() -> list:
    conn = get_conn()
    rows = conn.execute("""
        SELECT s.site_key, s.site_name, s.base_url,
               COUNT(r.id) AS total_results,
               SUM(CASE WHEN r.stream_url != '' THEN 1 ELSE 0 END) AS total_streams,
               SUM(CASE WHEN r.resource_type = 'art' THEN 1 ELSE 0 END) AS total_arts,
               MAX(r.crawled_at) AS last_crawled
        FROM crawl_sessions s
        LEFT JOIN crawl_results r ON r.session_id = s.id
        WHERE s.status = 'done'
        GROUP BY s.site_key
        ORDER BY last_crawled DESC
    """).fetchall()
    return [dict(r) for r in rows]


def export_session_to_dict(session_id: int) -> dict:
    conn = get_conn()
    session = conn.execute("SELECT * FROM crawl_sessions WHERE id = ?", (session_id,)).fetchone()
    if not session:
        return {}

    results = get_results_by_session(session_id, limit=10000)
    videos = []
    arts = []
    for r in results:
        if r["stream_url"]:
            videos.append({
                "title": r["title"],
                "detail_url": r["detail_url"],
                "stream_url": r["stream_url"],
                "stream_format": r["stream_format"],
            })
        elif r["images"]:
            arts.append({
                "title": r["title"],
                "detail_url": r["detail_url"],
                "images": r["images"],
                "image_count": len(r["images"]),
            })

    deep_results = {}
    if videos:
        deep_results["video"] = videos
    if arts:
        deep_results["art"] = arts

    s = dict(session)
    return {
        "start_url": s.get("base_url", ""),
        "title": s.get("site_name", ""),
        "total_pages": 0,
        "total_images": sum(len(a.get("images", [])) for a in arts),
        "total_videos": len(videos),
        "total_art_details": len(arts),
        "total_streams": s.get("total_streams", 0),
        "pages": [],
        "video_links": videos,
        "art_detail_links": arts,
        "image_links": [],
        "deep_results": deep_results,
    }
