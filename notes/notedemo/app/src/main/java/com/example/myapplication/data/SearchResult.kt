package com.example.myapplication.data

import android.graphics.RectF

/**
 * 搜索结果数据类
 *
 * @param noteId       笔记 ID
 * @param pageIndex    页码 (文本笔记为 0，PDF 从 0 开始)
 * @param sourceType   来源类型: "TEXT" | "PDF" | "INK"
 * @param bbox         归一化的 Bounding Box (RectF)，取值范围 [0, 1]
 *                     坐标系: 原点左上角，x 向右，y 向下
 * @param originalText 原始文本
 * @param snippet      FTS5 snippet 函数返回的高亮摘要
 */
data class SearchResult(
    val noteId: String,
    val pageIndex: Int,
    val sourceType: String,
    val bbox: RectF,
    val originalText: String,
    val snippet: String
) {
    companion object {
        const val SOURCE_TEXT = "TEXT"
        const val SOURCE_PDF = "PDF"
        const val SOURCE_INK = "INK"
    }

    /**
     * source_type 中文描述（用于 UI 显示）
     */
    fun sourceTypeLabel(): String = when (sourceType) {
        SOURCE_TEXT -> "文本"
        SOURCE_PDF -> "PDF"
        SOURCE_INK -> "手写"
        else -> sourceType
    }
}
