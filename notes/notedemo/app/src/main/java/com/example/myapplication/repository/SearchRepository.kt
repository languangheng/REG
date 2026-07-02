package com.example.myapplication.repository

import android.content.ContentValues
import android.database.Cursor
import android.graphics.Path
import android.graphics.RectF
import android.util.Log
import com.example.myapplication.data.BBoxUtils
import com.example.myapplication.data.Note
import com.example.myapplication.data.SearchDatabase
import com.example.myapplication.data.SearchResult
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.flow.flowOn

/**
 * SearchRepository — 封装所有数据库搜索操作
 *
 * 核心职责:
 *   1. 分词入库: 使用 jieba-kmp 对中文文本分词 → 写入全文索引
 *   2. 全局搜索: 跨所有笔记查询，JOIN search_meta 获取位置
 *   3. 单笔记搜索: 全局搜索 + WHERE note_id = ?
 *   4. 删除索引: 根据 note_id 删除旧索引
 *
 * 兼容性:
 *   自动适配 FTS5 / FTS4 / LIKE 三种模式（由 SearchDatabase.ftsMode 决定）
 *
 * 线程安全:
 *   所有 DB 操作都在 Dispatchers.IO 中执行，禁止在主线程操作数据库
 */
class SearchRepository(private val db: SearchDatabase) {

    companion object {
        private const val TAG = "SearchRepository"
    }

    // ════════════════════════════════════════════════════════════════
    //  入库操作
    // ════════════════════════════════════════════════════════════════

    suspend fun insertTextIndex(
        noteId: String,
        pageIndex: Int = 0,
        text: String,
        bbox: RectF,
        logicalWidth: Float,
        logicalHeight: Float
    ) = flowOnIo {
        val normalizedBBox = BBoxUtils.normalize(bbox, logicalWidth, logicalHeight)
        insertIndexInternal(noteId, pageIndex, SearchDatabase.SOURCE_TEXT, text, normalizedBBox)
    }

    suspend fun insertPdfIndex(
        noteId: String,
        pageIndex: Int,
        text: String,
        pdfBBox: RectF,
        pageWidth: Float,
        pageHeight: Float
    ) = flowOnIo {
        // 1. 先归一化到 [0,1]（此时坐标系仍是左下角原点）
        val normalized = BBoxUtils.normalize(pdfBBox, pageWidth, pageHeight)
        // 2. Y 轴翻转: 将左下角原点 → 左上角原点
        val flippedBBox = BBoxUtils.flipYForPdf(normalized)
        insertIndexInternal(noteId, pageIndex, SearchDatabase.SOURCE_PDF, text, flippedBBox)
    }

    suspend fun insertInkIndex(
        noteId: String,
        pageIndex: Int,
        text: String,
        inkPath: Path,
        canvasWidth: Float,
        canvasHeight: Float
    ) = flowOnIo {
        val normalizedBBox = BBoxUtils.fromPath(inkPath, canvasWidth, canvasHeight)
        insertIndexInternal(noteId, pageIndex, SearchDatabase.SOURCE_INK, text, normalizedBBox)
    }

    /**
     * 内部入库方法 — 所有入库操作的公共逻辑
     *
     * 关键: 所有操作包裹在 transaction 中，确保原子性
     */
    private suspend fun insertIndexInternal(
        noteId: String,
        pageIndex: Int,
        sourceType: String,
        text: String,
        normalizedBBox: RectF
    ) {
        val writable = db.writableDatabase

        // ── jieba 分词 ──
        val tokens = JiebaHelper.segment(text)
        if (tokens.isEmpty()) return

        // ── 开启 transaction（高性能写入关键） ──
        writable.beginTransaction()
        try {
            // 1. 先删除该笔记的旧索引（更新场景）
            deleteNoteIndexInternal(writable, noteId)

            // 2. 写入 search_meta
            val metaValues = ContentValues().apply {
                put(SearchDatabase.COL_NOTE_ID, noteId)
                put(SearchDatabase.COL_PAGE_INDEX, pageIndex)
                put(SearchDatabase.COL_SOURCE_TYPE, sourceType)
                put(SearchDatabase.COL_BBOX, BBoxUtils.toDbString(normalizedBBox))
                put(SearchDatabase.COL_ORIGINAL_TEXT, text)
            }
            val metaRowId = writable.insert(SearchDatabase.TABLE_META, null, metaValues)
            if (metaRowId == -1L) {
                Log.e(TAG, "Failed to insert search_meta for note=$noteId")
                return
            }

            // 3. 写入 search_index，关联 meta_rowid
            val indexValues = ContentValues().apply {
                put(SearchDatabase.COL_TOKEN, tokens)
                put(SearchDatabase.COL_META_ROWID, metaRowId)
            }
            writable.insert(SearchDatabase.TABLE_INDEX, null, indexValues)

            // 4. 标记 transaction 成功
            writable.setTransactionSuccessful()
        } finally {
            writable.endTransaction()
        }
    }

    // ════════════════════════════════════════════════════════════════
    //  删除操作
    // ════════════════════════════════════════════════════════════════

    suspend fun deleteNoteIndex(noteId: String) = flowOnIo {
        val writable = db.writableDatabase
        writable.beginTransaction()
        try {
            deleteNoteIndexInternal(writable, noteId)
            writable.setTransactionSuccessful()
        } finally {
            writable.endTransaction()
        }
    }

    private fun deleteNoteIndexInternal(db: android.database.sqlite.SQLiteDatabase, noteId: String) {
        // 1. 先删索引表中关联的记录
        db.execSQL(
            "DELETE FROM ${SearchDatabase.TABLE_INDEX} " +
                    "WHERE ${SearchDatabase.COL_META_ROWID} IN " +
                    "(SELECT ${SearchDatabase.COL_ROWID} FROM ${SearchDatabase.TABLE_META} " +
                    "WHERE ${SearchDatabase.COL_NOTE_ID} = ?)",
            arrayOf(noteId)
        )
        // 2. 再删 meta 表中的记录
        db.delete(SearchDatabase.TABLE_META, "${SearchDatabase.COL_NOTE_ID} = ?", arrayOf(noteId))
    }

    // ════════════════════════════════════════════════════════════════
    //  搜索操作
    // ════════════════════════════════════════════════════════════════

    fun searchGlobal(query: String): Flow<List<SearchResult>> = flow {
        val results = executeSearch(query, null)
        emit(results)
    }.flowOn(Dispatchers.IO)

    fun searchInNote(query: String, noteId: String): Flow<List<SearchResult>> = flow {
        val results = executeSearch(query, noteId)
        emit(results)
    }.flowOn(Dispatchers.IO)

    /**
     * 执行搜索的内部方法
     *
     * 根据 SearchDatabase.ftsMode 选择不同的搜索策略:
     *   - fts4: MATCH + snippet()
     *   - like: LIKE 查询 + 手动高亮
     */
    private suspend fun executeSearch(query: String, noteId: String?): List<SearchResult> {
        val readable = db.readableDatabase

        // jieba 分词后构建查询表达式
        val matchQuery = JiebaHelper.segment(query)
        if (matchQuery.isEmpty()) return emptyList()

        val mode = SearchDatabase.ftsMode
        Log.d(TAG, "Search mode=$mode, query='$query', matchQuery='$matchQuery', noteId=$noteId")

        var sql: String
        var args: Array<String>

        when (mode) {
            "fts4" -> {
                // FTS4 模式: 使用 MATCH + snippet()
                // FTS4 snippet 参数: (table, column_index, start_match, end_match, ellipsis, token_count)
                val snippetFunc = "snippet(${SearchDatabase.TABLE_INDEX})"

                sql = """
                    SELECT si.${SearchDatabase.COL_TOKEN},
                           $snippetFunc AS snippet,
                           sm.${SearchDatabase.COL_NOTE_ID},
                           sm.${SearchDatabase.COL_PAGE_INDEX},
                           sm.${SearchDatabase.COL_SOURCE_TYPE},
                           sm.${SearchDatabase.COL_BBOX},
                           sm.${SearchDatabase.COL_ORIGINAL_TEXT}
                    FROM ${SearchDatabase.TABLE_INDEX} si
                    JOIN ${SearchDatabase.TABLE_META} sm
                      ON si.${SearchDatabase.COL_META_ROWID} = sm.${SearchDatabase.COL_ROWID}
                    WHERE ${SearchDatabase.TABLE_INDEX} MATCH ?
                """.trimIndent()

                if (noteId != null) {
                    sql += " AND sm.${SearchDatabase.COL_NOTE_ID} = ?"
                    args = arrayOf(matchQuery, noteId)
                } else {
                    args = arrayOf(matchQuery)
                }
            }
            else -> {
                // LIKE 模式: 普通表 LIKE 查询 + 手动高亮
                // 对 token 列做 LIKE 查询，每个分词用 % 连接
                val likePattern = "%" + matchQuery.replace(" ", "%") + "%"
                sql = """
                    SELECT si.${SearchDatabase.COL_TOKEN},
                           si.${SearchDatabase.COL_TOKEN} AS snippet,
                           sm.${SearchDatabase.COL_NOTE_ID},
                           sm.${SearchDatabase.COL_PAGE_INDEX},
                           sm.${SearchDatabase.COL_SOURCE_TYPE},
                           sm.${SearchDatabase.COL_BBOX},
                           sm.${SearchDatabase.COL_ORIGINAL_TEXT}
                    FROM ${SearchDatabase.TABLE_INDEX} si
                    JOIN ${SearchDatabase.TABLE_META} sm
                      ON si.${SearchDatabase.COL_META_ROWID} = sm.${SearchDatabase.COL_ROWID}
                    WHERE si.${SearchDatabase.COL_TOKEN} LIKE ?
                """.trimIndent()

                if (noteId != null) {
                    sql += " AND sm.${SearchDatabase.COL_NOTE_ID} = ?"
                    args = arrayOf(likePattern, noteId)
                } else {
                    args = arrayOf(likePattern)
                }
            }
        }

        val results = mutableListOf<SearchResult>()
        val cursor: Cursor = readable.rawQuery(sql, args)
        cursor.use {
            while (it.moveToNext()) {
                val rawSnippet = it.getString(it.getColumnIndexOrThrow("snippet"))
                val resultNoteId = it.getString(it.getColumnIndexOrThrow(SearchDatabase.COL_NOTE_ID))
                val pageIndex = it.getInt(it.getColumnIndexOrThrow(SearchDatabase.COL_PAGE_INDEX))
                val sourceType = it.getString(it.getColumnIndexOrThrow(SearchDatabase.COL_SOURCE_TYPE))
                val bboxStr = it.getString(it.getColumnIndexOrThrow(SearchDatabase.COL_BBOX))
                val originalText = it.getString(it.getColumnIndexOrThrow(SearchDatabase.COL_ORIGINAL_TEXT))

                // LIKE 模式下手动生成高亮摘要
                val finalSnippet = if (mode == "like") {
                    generateLikeSnippet(originalText, query)
                } else {
                    rawSnippet
                }

                results.add(
                    SearchResult(
                        noteId = resultNoteId,
                        pageIndex = pageIndex,
                        sourceType = sourceType,
                        bbox = BBoxUtils.fromDbString(bboxStr),
                        originalText = originalText,
                        snippet = finalSnippet
                    )
                )
            }
        }
        Log.d(TAG, "Search '$query' in note=$noteId → ${results.size} results (mode=$mode)")
        return results
    }

    /**
     * LIKE 模式下手动生成高亮摘要
     * 在原始文本中查找查询关键词，用 <b> 标签包裹
     */
    private fun generateLikeSnippet(originalText: String, query: String): String {
        // 简单实现: 截取包含关键词的片段
        val lowerText = originalText.lowercase()
        val lowerQuery = query.lowercase()
        val idx = lowerText.indexOf(lowerQuery)
        return if (idx >= 0) {
            val start = maxOf(0, idx - 20)
            val end = minOf(originalText.length, idx + query.length + 20)
            val prefix = if (start > 0) "..." else ""
            val suffix = if (end < originalText.length) "..." else ""
            val segment = originalText.substring(start, end)
            val highlightStart = idx - start
            val highlightEnd = highlightStart + query.length
            "$prefix${segment.substring(0, highlightStart)}<b>${segment.substring(highlightStart, highlightEnd)}</b>${segment.substring(highlightEnd)}$suffix"
        } else {
            // 没找到直接截取前 50 字符
            if (originalText.length > 50) originalText.substring(0, 50) + "..." else originalText
        }
    }

    // ════════════════════════════════════════════════════════════════
    //  笔记主表 CRUD
    // ════════════════════════════════════════════════════════════════

    /**
     * 保存笔记到 notes 表，并自动建立搜索索引
     *
     * @param note 笔记对象
     * @param inkPath 手写笔迹 Path (可为 null)
     * @param canvasWidth 画布宽度 (用于 INK bbox 归一化)
     * @param canvasHeight 画布高度
     */
    suspend fun saveNote(
        note: Note,
        inkPath: Path? = null,
        canvasWidth: Float = 1080f,
        canvasHeight: Float = 1920f
    ) = flowOnIo {
        val db = db.writableDatabase
        val now = System.currentTimeMillis()

        // ── 在 transaction 之前完成所有 jieba 分词 ──
        // 因为 JiebaHelper.segment 是 suspend 函数，在 transaction 内调用会导致
        // 协程切换线程时数据库连接被占用，引发 "database is locked" 错误
        val contentTokens = if (note.content.isNotBlank()) JiebaHelper.segment(note.content) else ""
        val titleTokens = if (note.title.isNotBlank()) JiebaHelper.segment(note.title) else ""

        // 计算手写笔迹 bbox（如果有的话）
        val inkBBox = if (inkPath != null) {
            BBoxUtils.fromPath(inkPath, canvasWidth, canvasHeight)
        } else null
        val inkText = if (note.content.isNotBlank()) note.content
                      else if (note.title.isNotBlank()) note.title
                      else ""
        val inkTokens = if (inkPath != null && inkText.isNotBlank()) JiebaHelper.segment(inkText) else ""

        val pdfTokens = if (note.pdfName.isNotBlank() && note.content.isNotBlank())
                            JiebaHelper.segment(note.content) else ""

        // ── 所有分词完成后，开始数据库事务 ──
        db.beginTransaction()
        try {
            // 1. 写入 notes 表
            val values = ContentValues().apply {
                put(SearchDatabase.COL_NOTE_ID, note.noteId)
                put(SearchDatabase.COL_TITLE, note.title)
                put(SearchDatabase.COL_CONTENT, note.content)
                put(SearchDatabase.COL_INK_PATH, note.inkPathData)
                put(SearchDatabase.COL_PDF_NAME, note.pdfName)
                put(SearchDatabase.COL_CREATED_AT, note.createdAt)
                put(SearchDatabase.COL_UPDATED_AT, now)
            }
            db.insertWithOnConflict(SearchDatabase.TABLE_NOTES, null, values,
                android.database.sqlite.SQLiteDatabase.CONFLICT_REPLACE)

            // 2. 删除旧搜索索引
            deleteNoteIndexInternal(db, note.noteId)

            // 3. 为文本内容建立索引
            if (contentTokens.isNotEmpty()) {
                val metaValues = ContentValues().apply {
                    put(SearchDatabase.COL_NOTE_ID, note.noteId)
                    put(SearchDatabase.COL_PAGE_INDEX, 0)
                    put(SearchDatabase.COL_SOURCE_TYPE, SearchDatabase.SOURCE_TEXT)
                    put(SearchDatabase.COL_BBOX, "0.05,0.05,0.9,0.15")
                    put(SearchDatabase.COL_ORIGINAL_TEXT, note.content)
                }
                val metaRowId = db.insert(SearchDatabase.TABLE_META, null, metaValues)
                val indexValues = ContentValues().apply {
                    put(SearchDatabase.COL_TOKEN, contentTokens)
                    put(SearchDatabase.COL_META_ROWID, metaRowId)
                }
                db.insert(SearchDatabase.TABLE_INDEX, null, indexValues)
            }

            // 4. 为标题建立索引
            if (titleTokens.isNotEmpty()) {
                val metaValues = ContentValues().apply {
                    put(SearchDatabase.COL_NOTE_ID, note.noteId)
                    put(SearchDatabase.COL_PAGE_INDEX, 0)
                    put(SearchDatabase.COL_SOURCE_TYPE, SearchDatabase.SOURCE_TEXT)
                    put(SearchDatabase.COL_BBOX, "0.05,0.0,0.9,0.05")
                    put(SearchDatabase.COL_ORIGINAL_TEXT, note.title)
                }
                val metaRowId = db.insert(SearchDatabase.TABLE_META, null, metaValues)
                val indexValues = ContentValues().apply {
                    put(SearchDatabase.COL_TOKEN, titleTokens)
                    put(SearchDatabase.COL_META_ROWID, metaRowId)
                }
                db.insert(SearchDatabase.TABLE_INDEX, null, indexValues)
            }

            // 5. 为手写笔迹建立索引
            if (inkBBox != null && inkTokens.isNotEmpty()) {
                val metaValues = ContentValues().apply {
                    put(SearchDatabase.COL_NOTE_ID, note.noteId)
                    put(SearchDatabase.COL_PAGE_INDEX, 0)
                    put(SearchDatabase.COL_SOURCE_TYPE, SearchDatabase.SOURCE_INK)
                    put(SearchDatabase.COL_BBOX, BBoxUtils.toDbString(inkBBox))
                    put(SearchDatabase.COL_ORIGINAL_TEXT, inkText)
                }
                val metaRowId = db.insert(SearchDatabase.TABLE_META, null, metaValues)
                val indexValues = ContentValues().apply {
                    put(SearchDatabase.COL_TOKEN, inkTokens)
                    put(SearchDatabase.COL_META_ROWID, metaRowId)
                }
                db.insert(SearchDatabase.TABLE_INDEX, null, indexValues)
            }

            // 6. 为 PDF 建立索引
            if (pdfTokens.isNotEmpty()) {
                val metaValues = ContentValues().apply {
                    put(SearchDatabase.COL_NOTE_ID, note.noteId)
                    put(SearchDatabase.COL_PAGE_INDEX, 0)
                    put(SearchDatabase.COL_SOURCE_TYPE, SearchDatabase.SOURCE_PDF)
                    put(SearchDatabase.COL_BBOX, "0.1,0.1,0.8,0.15")
                    put(SearchDatabase.COL_ORIGINAL_TEXT, note.content)
                }
                val metaRowId = db.insert(SearchDatabase.TABLE_META, null, metaValues)
                val indexValues = ContentValues().apply {
                    put(SearchDatabase.COL_TOKEN, pdfTokens)
                    put(SearchDatabase.COL_META_ROWID, metaRowId)
                }
                db.insert(SearchDatabase.TABLE_INDEX, null, indexValues)
            }

            db.setTransactionSuccessful()
        } finally {
            db.endTransaction()
        }
        Log.d(TAG, "笔记已保存: ${note.noteId}")
    }

    /**
     * 获取所有笔记列表（按更新时间倒序）
     */
    suspend fun getAllNotes(): List<Note> = kotlinx.coroutines.withContext(Dispatchers.IO) {
        val readable = db.readableDatabase
        val cursor = readable.query(
            SearchDatabase.TABLE_NOTES,
            null, null, null, null, null,
            "${SearchDatabase.COL_UPDATED_AT} DESC"
        )
        val notes = mutableListOf<Note>()
        cursor.use {
            while (it.moveToNext()) {
                notes.add(Note(
                    noteId = it.getString(it.getColumnIndexOrThrow(SearchDatabase.COL_NOTE_ID)),
                    title = it.getString(it.getColumnIndexOrThrow(SearchDatabase.COL_TITLE)),
                    content = it.getString(it.getColumnIndexOrThrow(SearchDatabase.COL_CONTENT)),
                    inkPathData = it.getString(it.getColumnIndexOrThrow(SearchDatabase.COL_INK_PATH)),
                    pdfName = it.getString(it.getColumnIndexOrThrow(SearchDatabase.COL_PDF_NAME)),
                    createdAt = it.getLong(it.getColumnIndexOrThrow(SearchDatabase.COL_CREATED_AT)),
                    updatedAt = it.getLong(it.getColumnIndexOrThrow(SearchDatabase.COL_UPDATED_AT))
                ))
            }
        }
        Log.d(TAG, "获取笔记列表: ${notes.size} 条")
        notes
    }

    /**
     * 根据 noteId 获取单个笔记
     */
    suspend fun getNoteById(noteId: String): Note? = kotlinx.coroutines.withContext(Dispatchers.IO) {
        val readable = db.readableDatabase
        val cursor = readable.query(
            SearchDatabase.TABLE_NOTES,
            null,
            "${SearchDatabase.COL_NOTE_ID} = ?",
            arrayOf(noteId),
            null, null, null
        )
        var note: Note? = null
        cursor.use {
            if (it.moveToFirst()) {
                note = Note(
                    noteId = it.getString(it.getColumnIndexOrThrow(SearchDatabase.COL_NOTE_ID)),
                    title = it.getString(it.getColumnIndexOrThrow(SearchDatabase.COL_TITLE)),
                    content = it.getString(it.getColumnIndexOrThrow(SearchDatabase.COL_CONTENT)),
                    inkPathData = it.getString(it.getColumnIndexOrThrow(SearchDatabase.COL_INK_PATH)),
                    pdfName = it.getString(it.getColumnIndexOrThrow(SearchDatabase.COL_PDF_NAME)),
                    createdAt = it.getLong(it.getColumnIndexOrThrow(SearchDatabase.COL_CREATED_AT)),
                    updatedAt = it.getLong(it.getColumnIndexOrThrow(SearchDatabase.COL_UPDATED_AT))
                )
            }
        }
        Log.d(TAG, "获取笔记: $noteId → ${if (note != null) "找到" else "未找到"}")
        note
    }

    /**
     * 删除笔记（含主表和搜索索引）
     */
    suspend fun deleteNote(noteId: String) = flowOnIo {
        val writable = db.writableDatabase
        writable.beginTransaction()
        try {
            deleteNoteIndexInternal(writable, noteId)
            writable.delete(SearchDatabase.TABLE_NOTES, "${SearchDatabase.COL_NOTE_ID} = ?", arrayOf(noteId))
            writable.setTransactionSuccessful()
        } finally {
            writable.endTransaction()
        }
    }

    // ════════════════════════════════════════════════════════════════
    //  辅助方法
    // ════════════════════════════════════════════════════════════════

    private suspend fun flowOnIo(block: suspend () -> Unit) {
        kotlinx.coroutines.withContext(Dispatchers.IO) { block() }
    }
}
