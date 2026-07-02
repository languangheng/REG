package com.example.myapplication.ui

import android.graphics.Color
import android.graphics.RectF
import android.os.Bundle
import android.util.Log
import android.view.Gravity
import android.widget.FrameLayout
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.example.myapplication.data.Note
import com.example.myapplication.data.SearchDatabase
import com.example.myapplication.data.SearchResult
import com.example.myapplication.databinding.ActivityNoteDetailBinding
import com.example.myapplication.repository.SearchRepository
import com.example.myapplication.util.PdfPageRenderer
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/**
 * NoteDetailActivity — 笔记详情页
 *
 * 统一展示所有笔记类型:
 * 1. 标题（如果有的话）
 * 2. 文本内容（如果有的话）
 * 3. 手写笔迹（如果有的话）
 * 4. PDF 所有页面（如果有的话）
 *
 * 搜索时在对应区域高亮显示
 */
class NoteDetailActivity : AppCompatActivity() {

    companion object {
        const val EXTRA_NOTE_ID = "extra_note_id"
        const val EXTRA_SEARCH_QUERY = "extra_search_query"
        const val EXTRA_SOURCE_TYPE = "extra_source_type"
        const val EXTRA_PAGE_INDEX = "extra_page_index"
        private const val TAG = "NoteDetailActivity"
    }

    private lateinit var binding: ActivityNoteDetailBinding
    private lateinit var repository: SearchRepository
    private lateinit var pdfRenderer: PdfPageRenderer

    // PDF 每页的 Overlay 和 ImageView
    private val pageOverlays = mutableListOf<HighlightOverlayView>()
    private val pageImageViews = mutableListOf<ImageView>()
    // 文本区域的 Overlay
    private var textOverlay: HighlightOverlayView? = null
    // 手写区域的 Overlay
    private var inkOverlay: HighlightOverlayView? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityNoteDetailBinding.inflate(layoutInflater)
        setContentView(binding.root)

        val database = SearchDatabase(this)
        repository = SearchRepository(database)
        pdfRenderer = PdfPageRenderer(this)

        val noteId = intent.getStringExtra(EXTRA_NOTE_ID) ?: return
        val searchQuery = intent.getStringExtra(EXTRA_SEARCH_QUERY) ?: ""

        lifecycleScope.launch {
            val note = withContext(Dispatchers.IO) { repository.getNoteById(noteId) }
            if (note == null) {
                Toast.makeText(this@NoteDetailActivity, "笔记不存在", Toast.LENGTH_SHORT).show()
                finish()
                return@launch
            }

            binding.tvDetailTitle.text = if (note.title.isNotEmpty()) note.title else "无标题笔记"

            // 统一加载所有内容
            loadAllContent(note, searchQuery)
        }
    }

    /**
     * 统一加载笔记所有内容:
     * 文本 → 手写笔迹 → PDF（按顺序展示）
     */
    private fun loadAllContent(note: Note, searchQuery: String) {
        val density = resources.displayMetrics.density
        val spDensity = resources.displayMetrics.scaledDensity

        // ── 1. 文本内容 ──
        if (note.content.isNotEmpty()) {
            val tvContent = TextView(this).apply {
                text = note.content
                textSize = 16f * spDensity / density  // 16sp
                setPadding(32, 48, 32, 48)
                setTextColor(Color.parseColor("#333333"))
                setBackgroundColor(Color.parseColor("#FFFFFF"))
            }

            textOverlay = createOverlay()
            val frame = FrameLayout(this).apply {
                layoutParams = LinearLayout.LayoutParams(
                    LinearLayout.LayoutParams.MATCH_PARENT,
                    LinearLayout.LayoutParams.WRAP_CONTENT
                )
            }
            frame.addView(tvContent)
            frame.addView(textOverlay!!.apply {
                layoutParams = FrameLayout.LayoutParams(
                    FrameLayout.LayoutParams.MATCH_PARENT,
                    FrameLayout.LayoutParams.MATCH_PARENT
                )
            })
            binding.llContentWrapper.addView(frame)
        }

        // ── 2. 手写笔迹 ──
        if (note.inkPathData.isNotEmpty()) {
            val tvInkLabel = TextView(this).apply {
                text = "✎ 手写笔迹"
                textSize = 14f * spDensity / density
                setPadding(32, 24, 32, 8)
                setTextColor(Color.parseColor("#888888"))
            }
            binding.llContentWrapper.addView(tvInkLabel)

            val inkView = InkCanvasView(this).apply {
                layoutParams = LinearLayout.LayoutParams(
                    LinearLayout.LayoutParams.MATCH_PARENT,
                    dpToPx(400)
                )
                restoreFromSerializedData(note.inkPathData)
            }

            inkOverlay = createOverlay()
            val inkFrame = FrameLayout(this).apply {
                layoutParams = LinearLayout.LayoutParams(
                    LinearLayout.LayoutParams.MATCH_PARENT,
                    dpToPx(400)
                )
            }
            inkFrame.addView(inkView)
            inkFrame.addView(inkOverlay!!.apply {
                layoutParams = FrameLayout.LayoutParams(
                    FrameLayout.LayoutParams.MATCH_PARENT,
                    FrameLayout.LayoutParams.MATCH_PARENT
                )
            })
            binding.llContentWrapper.addView(inkFrame)
        }

        // ── 3. PDF 页面 ──
        if (note.pdfName.isNotEmpty()) {
            val tvPdfLabel = TextView(this).apply {
                text = "📄 PDF 文档: ${note.pdfName}"
                textSize = 14f * spDensity / density
                setPadding(32, 24, 32, 8)
                setTextColor(Color.parseColor("#888888"))
            }
            binding.llContentWrapper.addView(tvPdfLabel)

            lifecycleScope.launch {
                loadPdfPages(note.pdfName)
                if (searchQuery.isNotEmpty()) {
                    performSearch(note.noteId, searchQuery)
                }
            }
        } else {
            if (searchQuery.isNotEmpty()) {
                performSearch(note.noteId, searchQuery)
            }
        }
    }

    /**
     * 加载 PDF 所有页面
     */
    private suspend fun loadPdfPages(pdfName: String) {
        val spDensity = resources.displayMetrics.scaledDensity
        val density = resources.displayMetrics.density

        val pageCount = try {
            pdfRenderer.getPageCountForFile(pdfName)
        } catch (e: Exception) {
            Log.e(TAG, "无法获取 PDF 页数: $pdfName", e)
            0
        }

        if (pageCount == 0) {
            val tvNoPdf = TextView(this).apply {
                text = "📄 未找到 PDF 文件: $pdfName\n\n请将 PDF 放到 app/src/main/assets/ 目录"
                textSize = 14f * spDensity / density
                setPadding(48, 48, 48, 48)
                gravity = Gravity.CENTER
                setTextColor(Color.parseColor("#999999"))
            }
            binding.llContentWrapper.addView(tvNoPdf)
            return
        }

        Log.d(TAG, "PDF 共 $pageCount 页，开始渲染...")

        for (pageIndex in 0 until pageCount) {
            val tvPageLabel = TextView(this).apply {
                text = "第 ${pageIndex + 1} / $pageCount 页"
                textSize = 12f * spDensity / density
                setPadding(16, 16, 16, 4)
                setTextColor(Color.parseColor("#AAAAAA"))
                gravity = Gravity.CENTER
            }
            binding.llContentWrapper.addView(tvPageLabel)

            val renderWidth = 1080
            val renderHeight = 1440
            val bitmap = try {
                pdfRenderer.renderPageForFile(pdfName, pageIndex, renderWidth, renderHeight)
            } catch (e: Exception) {
                Log.e(TAG, "渲染第 $pageIndex 页失败", e)
                null
            }

            if (bitmap == null) {
                val tvError = TextView(this).apply {
                    text = "❌ 第 ${pageIndex + 1} 页渲染失败"
                    textSize = 14f * spDensity / density
                    setPadding(32, 16, 32, 16)
                    setTextColor(Color.RED)
                }
                binding.llContentWrapper.addView(tvError)
                continue
            }

            val frame = FrameLayout(this).apply {
                layoutParams = LinearLayout.LayoutParams(
                    LinearLayout.LayoutParams.MATCH_PARENT,
                    LinearLayout.LayoutParams.WRAP_CONTENT
                )
            }

            val imageView = ImageView(this).apply {
                scaleType = ImageView.ScaleType.FIT_CENTER
                setImageBitmap(bitmap)
                adjustViewBounds = true
                layoutParams = FrameLayout.LayoutParams(
                    FrameLayout.LayoutParams.MATCH_PARENT,
                    FrameLayout.LayoutParams.WRAP_CONTENT
                )
            }
            frame.addView(imageView)

            val overlay = createOverlay().apply {
                layoutParams = FrameLayout.LayoutParams(
                    FrameLayout.LayoutParams.MATCH_PARENT,
                    FrameLayout.LayoutParams.MATCH_PARENT
                )
            }
            frame.addView(overlay)

            binding.llContentWrapper.addView(frame)

            pageImageViews.add(imageView)
            pageOverlays.add(overlay)

            Log.d(TAG, "第 ${pageIndex + 1} 页渲染完成")
        }
    }

    /**
     * 执行搜索，在文本/手写/PDF 各区域设置高亮
     */
    private fun performSearch(noteId: String, searchQuery: String) {
        lifecycleScope.launch {
            try {
                repository.searchInNote(searchQuery, noteId).collectLatest { results ->
                    Log.d(TAG, "搜索 '$searchQuery' → ${results.size} 个结果")

                    // ── 文本高亮 ──
                    val textResults = results.filter { it.sourceType == "TEXT" }
                    textOverlay?.let { overlay ->
                        overlay.post {
                            overlay.pageLogicalWidth = 1f
                            overlay.pageLogicalHeight = 1f
                            overlay.setContentRect(RectF(
                                0f, 0f,
                                overlay.width.toFloat(), overlay.height.toFloat()
                            ))
                            overlay.setHits(textResults.map { it.bbox })
                            Log.d(TAG, "TEXT 高亮: ${textResults.size} 个命中")
                        }
                    }

                    // ── 手写高亮 ──
                    val inkResults = results.filter { it.sourceType == "INK" }
                    inkOverlay?.let { overlay ->
                        overlay.post {
                            overlay.pageLogicalWidth = 1f
                            overlay.pageLogicalHeight = 1f
                            overlay.setContentRect(RectF(
                                0f, 0f,
                                overlay.width.toFloat(), overlay.height.toFloat()
                            ))
                            overlay.setHits(inkResults.map { it.bbox })
                            Log.d(TAG, "INK 高亮: ${inkResults.size} 个命中")
                        }
                    }

                    // ── PDF 每页高亮 ──
                    val pdfResults = results.filter { it.sourceType == "PDF" }
                    val byPage = pdfResults.groupBy { it.pageIndex }
                    for (pageIndex in pageImageViews.indices) {
                        val hits = byPage[pageIndex] ?: continue
                        val imageView = pageImageViews[pageIndex]
                        val overlay = pageOverlays[pageIndex]
                        imageView.post {
                            val contentRect = calculateBitmapContentRect(imageView)
                            overlay.setContentRect(contentRect)
                            overlay.pageLogicalWidth = 1f
                            overlay.pageLogicalHeight = 1f
                            overlay.setHits(hits.map { it.bbox })
                            Log.d(TAG, "PDF 第 ${pageIndex + 1} 页高亮: ${hits.size} 个命中")
                        }
                    }
                }
            } catch (e: Exception) {
                Log.e(TAG, "搜索失败", e)
            }
        }
    }

    private fun calculateBitmapContentRect(imageView: ImageView): RectF {
        val drawable = imageView.drawable
            ?: return RectF(0f, 0f, imageView.width.toFloat(), imageView.height.toFloat())
        val bmpWidth = drawable.intrinsicWidth.toFloat()
        val bmpHeight = drawable.intrinsicHeight.toFloat()
        val viewWidth = imageView.width.toFloat()
        val viewHeight = imageView.height.toFloat()

        if (bmpWidth <= 0 || bmpHeight <= 0 || viewWidth <= 0 || viewHeight <= 0) {
            return RectF(0f, 0f, viewWidth, viewHeight)
        }

        val scale = minOf(viewWidth / bmpWidth, viewHeight / bmpHeight)
        val displayWidth = bmpWidth * scale
        val displayHeight = bmpHeight * scale
        val offsetX = (viewWidth - displayWidth) / 2f
        val offsetY = (viewHeight - displayHeight) / 2f

        return RectF(offsetX, offsetY, offsetX + displayWidth, offsetY + displayHeight)
    }

    private fun createOverlay(): HighlightOverlayView {
        return HighlightOverlayView(this).apply {
            setBackgroundColor(Color.TRANSPARENT)
        }
    }

    private fun dpToPx(dp: Int): Int {
        val density = resources.displayMetrics.density
        return (dp * density).toInt()
    }
}
