package com.example.myapplication.util

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Color
import android.graphics.pdf.PdfRenderer
import android.os.ParcelFileDescriptor
import android.util.Log
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File
import java.io.FileOutputStream

/**
 * PdfPageRenderer — 封装 Android 原生 PdfRenderer
 *
 * 职责:
 *   1. 从 assets 目录加载 PDF 文件到缓存目录
 *   2. 使用 PdfRenderer 打开 PDF
 *   3. 渲染指定页为 Bitmap（在 Dispatchers.IO 中执行）
 *   4. 支持渲染所有页面
 *
 * 权限说明:
 *   - 使用 assets 目录下的 PDF 不需要运行时存储权限
 *   - 如果从外部存储加载 PDF，需要申请 READ_EXTERNAL_STORAGE 权限
 */
class PdfPageRenderer(private val context: Context) {

    companion object {
        private const val TAG = "PdfPageRenderer"
    }

    /**
     * 从 assets 加载指定 PDF 到缓存目录
     */
    private suspend fun copyAssetToCache(assetName: String): File = withContext(Dispatchers.IO) {
        val cacheFile = File(context.cacheDir, assetName)
        if (!cacheFile.exists()) {
            context.assets.open(assetName).use { input ->
                FileOutputStream(cacheFile).use { output ->
                    input.copyTo(output)
                }
            }
            Log.d(TAG, "Copied $assetName to cache: ${cacheFile.absolutePath}")
        }
        cacheFile
    }

    /**
     * 渲染指定 PDF 文件的某一页
     *
     * @param pdfName  PDF 文件名（assets 中的文件名或 cache 中的文件名）
     * @param pageIndex 页码（从 0 开始）
     * @param width     目标 Bitmap 宽度（像素）
     * @param height    目标 Bitmap 高度（像素）
     * @return 渲染后的 Bitmap，如果失败返回 null
     */
    suspend fun renderPageForFile(pdfName: String, pageIndex: Int, width: Int, height: Int): Bitmap? =
        withContext(Dispatchers.IO) {
            try {
                val pdfFile = copyAssetToCache(pdfName)
                val pfd = ParcelFileDescriptor.open(pdfFile, ParcelFileDescriptor.MODE_READ_ONLY)

                pfd.use { descriptor ->
                    PdfRenderer(descriptor).use { renderer ->
                        if (pageIndex < 0 || pageIndex >= renderer.pageCount) {
                            Log.e(TAG, "Invalid page index: $pageIndex, total: ${renderer.pageCount}")
                            return@use null
                        }

                        renderer.openPage(pageIndex).use { page ->
                            val bitmap = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888)
                            val canvas = android.graphics.Canvas(bitmap)
                            canvas.drawColor(Color.WHITE)
                            page.render(bitmap, null, null, PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY)
                            Log.d(TAG, "Rendered $pdfName page $pageIndex → ${width}x${height}")
                            bitmap
                        }
                    }
                }
            } catch (e: Exception) {
                Log.e(TAG, "Failed to render PDF page $pageIndex of $pdfName", e)
                null
            }
        }

    /**
     * 获取指定 PDF 文件的页数
     */
    suspend fun getPageCountForFile(pdfName: String): Int = withContext(Dispatchers.IO) {
        try {
            val pdfFile = copyAssetToCache(pdfName)
            val pfd = ParcelFileDescriptor.open(pdfFile, ParcelFileDescriptor.MODE_READ_ONLY)
            pfd.use { descriptor ->
                PdfRenderer(descriptor).use { renderer ->
                    renderer.pageCount
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Failed to get page count for $pdfName", e)
            0
        }
    }

    // ════════════════════════════════════════════════════════════════
    //  兼容旧 API: 默认使用 "sample.pdf"
    // ════════════════════════════════════════════════════════════════

    suspend fun renderPage(pageIndex: Int, width: Int, height: Int): Bitmap? =
        renderPageForFile("sample.pdf", pageIndex, width, height)

    suspend fun getPageCount(): Int =
        getPageCountForFile("sample.pdf")

    suspend fun getPageSize(pageIndex: Int): FloatArray = withContext(Dispatchers.IO) {
        try {
            val pdfFile = copyAssetToCache("sample.pdf")
            val pfd = ParcelFileDescriptor.open(pdfFile, ParcelFileDescriptor.MODE_READ_ONLY)
            pfd.use { descriptor ->
                PdfRenderer(descriptor).use { renderer ->
                    if (pageIndex < 0 || pageIndex >= renderer.pageCount) {
                        return@use floatArrayOf(1f, 1f)
                    }
                    renderer.openPage(pageIndex).use { page ->
                        floatArrayOf(page.width.toFloat(), page.height.toFloat())
                    }
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Failed to get page size", e)
            floatArrayOf(1f, 1f)
        }
    }
}
