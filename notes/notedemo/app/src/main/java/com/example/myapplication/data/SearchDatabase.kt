package com.example.myapplication.data

import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper

/**
 * SearchDatabase — 基于 SQLiteOpenHelper 的全文索引数据库
 *
 * 架构说明:
 * ┌─────────────────────────────────────────────────┐
 * │              search_meta (普通表)                  │
 * │  rowid PK AUTOINCREMENT                          │
 * │  note_id          — 笔记 ID                       │
 * │  page_index       — 页码 (文本笔记=0)              │
 * │  source_type      — TEXT / PDF / INK              │
 * │  bbox             — "x,y,w,h" 归一化到 [0,1]      │
 * │  original_text    — 原始文本                       │
 * ├─────────────────────────────────────────────────┤
 * │          search_index (FTS4 虚拟表)               │
 * │  token             — jieba 分词后空格分隔的文本    │
 * │  meta_rowid        — 外键 → search_meta.rowid     │
 * │  (tokenize='simple' — 空格分隔的 token 分词)      │
 * └─────────────────────────────────────────────────┘
 *
 * 注意: 使用 FTS4 全文索引（兼容性好，Android API 16+ 普遍可用）。
 *       如果设备不支持 FTS4，降级到普通表 + LIKE 查询。
 *
 * 坐标归一化规则:
 *   所有 bbox 统一归一化到页面逻辑坐标系（原点左上角，y 轴朝下）
 *   取值范围 [0, 1]，存储格式 "x,y,w,h"
 *   - TEXT: 相对于 TextView 文本区域
 *   - PDF:  相对于页面尺寸（注意 Y 轴翻转，见 Repository 注释）
 *   - INK:  相对于画布尺寸（Path.computeBounds 后归一化）
 */
class SearchDatabase(context: Context) :
    SQLiteOpenHelper(context, DB_NAME, null, DB_VERSION, null) {

    companion object {
        private const val DB_NAME = "note_search.db"
        private const val DB_VERSION = 4  // v4: 修复并发锁问题

        // 笔记主表
        const val TABLE_NOTES = "notes"
        const val COL_NOTE_ID = "note_id"
        const val COL_TITLE = "title"
        const val COL_CONTENT = "content"       // 文本内容
        const val COL_INK_PATH = "ink_path"     // 手写笔迹序列化 (Path 的 SVG-like 字符串)
        const val COL_PDF_NAME = "pdf_name"     // PDF 文件名 (assets 或 cache)
        const val COL_CREATED_AT = "created_at"
        const val COL_UPDATED_AT = "updated_at"

        // 搜索元数据表
        const val TABLE_META = "search_meta"
        const val COL_ROWID = "rowid"
        const val COL_PAGE_INDEX = "page_index"
        const val COL_SOURCE_TYPE = "source_type"
        const val COL_BBOX = "bbox"
        const val COL_ORIGINAL_TEXT = "original_text"

        const val TABLE_INDEX = "search_index"
        const val COL_TOKEN = "token"
        const val COL_META_ROWID = "meta_rowid"

        // source_type 枚举值
        const val SOURCE_TEXT = "TEXT"
        const val SOURCE_PDF = "PDF"
        const val SOURCE_INK = "INK"

        @Volatile
        var ftsMode: String = "fts4"
            private set
    }

    override fun onCreate(db: SQLiteDatabase) {
        // ── 0. 笔记主表 ──
        db.execSQL("""
            CREATE TABLE IF NOT EXISTS $TABLE_NOTES (
                $COL_NOTE_ID TEXT PRIMARY KEY,
                $COL_TITLE TEXT NOT NULL DEFAULT '',
                $COL_CONTENT TEXT NOT NULL DEFAULT '',
                $COL_INK_PATH TEXT NOT NULL DEFAULT '',
                $COL_PDF_NAME TEXT NOT NULL DEFAULT '',
                $COL_CREATED_AT INTEGER NOT NULL DEFAULT 0,
                $COL_UPDATED_AT INTEGER NOT NULL DEFAULT 0
            )
        """.trimIndent())
        db.execSQL("""
            CREATE INDEX IF NOT EXISTS idx_notes_updated
            ON $TABLE_NOTES($COL_UPDATED_AT DESC)
        """.trimIndent())

        // ── 1. 搜索元数据表 ──
        db.execSQL("""
            CREATE TABLE IF NOT EXISTS $TABLE_META (
                $COL_ROWID INTEGER PRIMARY KEY AUTOINCREMENT,
                $COL_NOTE_ID TEXT NOT NULL,
                $COL_PAGE_INDEX INTEGER NOT NULL DEFAULT 0,
                $COL_SOURCE_TYPE TEXT NOT NULL CHECK($COL_SOURCE_TYPE IN ('TEXT','PDF','INK')),
                $COL_BBOX TEXT NOT NULL,
                $COL_ORIGINAL_TEXT TEXT NOT NULL
            )
        """.trimIndent())
        db.execSQL("CREATE INDEX IF NOT EXISTS idx_meta_note_id ON $TABLE_META($COL_NOTE_ID)")

        // ── 2. 全文索引表 ──
        createFtsTable(db)
    }

    /**
     * 创建 FTS4 全文索引表
     * FTS4 在 Android API 16+ 上普遍可用，兼容性好
     */
    private fun createFtsTable(db: SQLiteDatabase) {
        // 直接使用 FTS4
        if (tryCreateTable(db, """
            CREATE VIRTUAL TABLE IF NOT EXISTS $TABLE_INDEX USING fts4(
                $COL_TOKEN,
                $COL_META_ROWID,
                tokenize='simple'
            )
        """.trimIndent())) {
            ftsMode = "fts4"
            android.util.Log.i("SearchDatabase", "FTS4 模式已启用")
            return
        }

        // 降级为普通表 + LIKE 查询
        db.execSQL("""
            CREATE TABLE IF NOT EXISTS $TABLE_INDEX (
                $COL_ROWID INTEGER PRIMARY KEY AUTOINCREMENT,
                $COL_TOKEN TEXT NOT NULL,
                $COL_META_ROWID INTEGER NOT NULL
            )
        """.trimIndent())
        db.execSQL("""
            CREATE INDEX IF NOT EXISTS idx_index_meta_rowid
            ON $TABLE_INDEX($COL_META_ROWID)
        """.trimIndent())
        ftsMode = "like"
        android.util.Log.w("SearchDatabase", "LIKE 模式已启用（FTS4 不可用）")
    }

    override fun onConfigure(db: SQLiteDatabase) {
        super.onConfigure(db)
        // 启用 WAL 模式，允许多线程并发读写，解决 database is locked 问题
        db.enableWriteAheadLogging()
    }

    override fun onDowngrade(db: SQLiteDatabase, oldVersion: Int, newVersion: Int) {
        // 允许降级（安装旧版 APK 时不崩溃）
        onUpgrade(db, oldVersion, newVersion)
    }

    /**
     * 尝试执行建表 SQL，返回是否成功
     */
    private fun tryCreateTable(db: SQLiteDatabase, sql: String): Boolean {
        return try {
            db.execSQL(sql)
            true
        } catch (e: Exception) {
            android.util.Log.w("SearchDatabase", "建表失败，尝试降级: ${e.message}")
            // 清理可能残留的表
            try { db.execSQL("DROP TABLE IF EXISTS $TABLE_INDEX") } catch (_: Exception) {}
            false
        }
    }

    override fun onUpgrade(db: SQLiteDatabase, oldVersion: Int, newVersion: Int) {
        db.execSQL("DROP TABLE IF EXISTS $TABLE_INDEX")
        db.execSQL("DROP TABLE IF EXISTS $TABLE_META")
        db.execSQL("DROP TABLE IF EXISTS $TABLE_NOTES")
        onCreate(db)
    }
}
