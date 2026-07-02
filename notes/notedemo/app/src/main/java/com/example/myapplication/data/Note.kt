package com.example.myapplication.data

/**
 * 笔记数据类
 */
data class Note(
    val noteId: String,
    val title: String,
    val content: String,
    val inkPathData: String,  // 序列化的 Path 数据
    val pdfName: String,      // PDF 文件名，空表示无 PDF
    val createdAt: Long,
    val updatedAt: Long
) {
    /**
     * 判断笔记类型: TEXT / INK / PDF
     * 优先级: PDF > INK > TEXT
     */
    fun primarySourceType(): String {
        return when {
            pdfName.isNotEmpty() -> SearchDatabase.SOURCE_PDF
            inkPathData.isNotEmpty() -> SearchDatabase.SOURCE_INK
            else -> SearchDatabase.SOURCE_TEXT
        }
    }

    /**
     * 用于列表展示的摘要
     */
    fun summary(): String {
        val parts = mutableListOf<String>()
        if (title.isNotEmpty()) parts.add(title)
        if (content.isNotEmpty()) {
            parts.add(if (content.length > 40) content.substring(0, 40) + "..." else content)
        }
        if (inkPathData.isNotEmpty()) parts.add("[手写]")
        if (pdfName.isNotEmpty()) parts.add("[PDF]")
        return if (parts.isEmpty()) "空白笔记" else parts.joinToString(" ")
    }
}
