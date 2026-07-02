package com.example.myapplication.repository

import android.util.Log
import cn.erolc.jieba.Jieba
import cn.erolc.jieba.Mode
import kotlinx.coroutines.flow.firstOrNull
import kotlinx.coroutines.flow.toList

/**
 * JiebaHelper — jieba-kmp 分词工具类
 *
 * 使用 jieba-kmp-android 库对中文文本进行分词
 * 分词后用空格拼接，用于插入 FTS (tokenize='ascii'/'simple')
 *
 * jieba-kmp API:
 *   Jieba.INSTANCE — 单例入口
 *   Jieba.cut(text, Mode) : Flow<String> — 返回 Flow
 *   Jieba.lCut(text, Mode) : suspend List<String> — suspend 返回 List
 *   Jieba.init(DiskHelper) — 初始化（加载词典）
 *
 * 依赖: cn.erolc.jieba:jieba-kmp-android:1.0.0
 */
object JiebaHelper {

    private const val TAG = "JiebaHelper"

    @Volatile
    private var initialized = false

    /**
     * 初始化 jieba（加载词典）
     * jieba-kmp 在 Android 上自动使用内置词典，但首次调用可能较慢
     */
    private fun ensureInit() {
        if (!initialized) {
            try {
                // jieba-kmp Android 版自带词典，init 可传 null 使用默认
                Jieba.init(null)
                initialized = true
                Log.i(TAG, "Jieba 初始化成功")
            } catch (e: Exception) {
                // init 可能已经内部初始化了，忽略错误
                Log.w(TAG, "Jieba init 异常（可能已自动初始化）: ${e.message}")
                initialized = true
            }
        }
    }

    /**
     * 对文本进行 jieba 分词（suspend 方法）
     *
     * @param text 待分词文本
     * @return 空格分隔的分词结果字符串，用于 FTS MATCH
     *
     * 示例: "高性能笔记搜索模块" → "高性能 笔记 搜索 模块"
     */
    suspend fun segment(text: String): String {
        if (text.isBlank()) return ""

        ensureInit()

        return try {
            // 使用 jieba-kmp 的 lCut 方法（suspend，返回 List<String>）
            // Mode.Full = 精确模式 + HMM
            val tokens = Jieba.lCut(text, Mode.Full)
            val result = tokens.filter { it.isNotBlank() }.joinToString(" ")
            Log.d(TAG, "分词成功: '$text' → '$result'")
            result
        } catch (e: Throwable) {
            Log.w(TAG, "jieba lCut 失败: ${e.message}")
            try {
                // 尝试 cut Flow 方式
                val tokens = Jieba.cut(text, Mode.Full).toList()
                val result = tokens.filter { it.isNotBlank() }.joinToString(" ")
                Log.d(TAG, "分词成功(Flow): '$text' → '$result'")
                result
            } catch (e2: Throwable) {
                Log.w(TAG, "jieba cut 也失败，降级为简单分词: ${e2.message}")
                segmentFallback(text)
            }
        }
    }

    /**
     * 降级分词方案（jieba 完全不可用时）
     * 中文按字分词，英文按空格分词
     */
    private fun segmentFallback(text: String): String {
        val result = StringBuilder()

        for (char in text) {
            when {
                char.isWhitespace() -> {
                    if (result.isNotEmpty() && result.last() != ' ') {
                        result.append(' ')
                    }
                }
                char.code >= 0x4E00 && char.code <= 0x9FFF -> {
                    // 中文字符: 每个字作为一个 token
                    if (result.isNotEmpty() && result.last() != ' ') {
                        result.append(' ')
                    }
                    result.append(char).append(' ')
                }
                else -> {
                    // 非中文字符: 连续拼接（英文单词）
                    result.append(char)
                }
            }
        }

        return result.toString().trim()
    }
}
