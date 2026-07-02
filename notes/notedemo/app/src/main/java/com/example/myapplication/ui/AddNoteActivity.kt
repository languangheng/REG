package com.example.myapplication.ui

import android.graphics.Color
import android.graphics.Path
import android.os.Bundle
import android.util.Log
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.widget.FrameLayout
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.example.myapplication.data.Note
import com.example.myapplication.data.SearchDatabase
import com.example.myapplication.databinding.ActivityAddNoteBinding
import com.example.myapplication.repository.SearchRepository
import com.example.myapplication.util.PdfPageRenderer
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class AddNoteActivity : AppCompatActivity() {

    companion object {
        private const val TAG = "AddNoteActivity"
    }

    private lateinit var binding: ActivityAddNoteBinding
    private lateinit var repository: SearchRepository
    private lateinit var pdfRenderer: PdfPageRenderer
    private var selectedPdfName: String = ""

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityAddNoteBinding.inflate(layoutInflater)
        setContentView(binding.root)

        repository = SearchRepository(SearchDatabase(this))
        pdfRenderer = PdfPageRenderer(this)

        // 清除笔迹按钮
        binding.btnClearInk.setOnClickListener {
            binding.inkCanvas.clear()
        }

        // 插入 PDF 按钮
        binding.btnInsertPdf.setOnClickListener {
            showPdfSelector()
        }

        // 保存按钮
        binding.btnSave.setOnClickListener {
            saveNote()
        }
    }

    private fun showPdfSelector() {
        try {
            val pdfFiles = assets.list("")?.filter { it.endsWith(".pdf", ignoreCase = true) } ?: emptyList()

            if (pdfFiles.isEmpty()) {
                Toast.makeText(this,
                    "assets 目录下没有 PDF 文件。\n请将 PDF 放到 app/src/main/assets/ 后重新编译。",
                    Toast.LENGTH_LONG).show()
                selectedPdfName = "sample.pdf"
                binding.tvPdfName.text = "PDF: $selectedPdfName (可能不存在)"
                binding.tvPdfName.setTextColor(Color.parseColor("#FF8800"))
                loadPdfPreview(selectedPdfName)
                return
            }

            val labels = pdfFiles.map { "📄 $it" }.toTypedArray()
            androidx.appcompat.app.AlertDialog.Builder(this)
                .setTitle("选择 PDF 文件")
                .setItems(labels) { _, which ->
                    selectedPdfName = pdfFiles[which]
                    binding.tvPdfName.text = "PDF: $selectedPdfName"
                    binding.tvPdfName.setTextColor(Color.parseColor("#1565C0"))
                    Log.i(TAG, "已选择 PDF: $selectedPdfName")
                    loadPdfPreview(selectedPdfName)
                }
                .setNegativeButton("取消", null)
                .show()
        } catch (e: Exception) {
            Log.e(TAG, "读取 assets 失败", e)
            Toast.makeText(this, "读取 PDF 列表失败: ${e.message}", Toast.LENGTH_SHORT).show()
        }
    }

    /**
     * 加载 PDF 所有页面预览
     */
    private fun loadPdfPreview(pdfName: String) {
        // 用 ScrollView + LinearLayout 展示所有页
        val scrollView = ScrollView(this).apply {
            layoutParams = FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT,
                FrameLayout.LayoutParams.MATCH_PARENT
            )
        }
        val linearLayout = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            layoutParams = FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT,
                FrameLayout.LayoutParams.WRAP_CONTENT
            )
        }
        scrollView.addView(linearLayout)

        // 替换原来的预览容器
        binding.ivPdfPreview.visibility = View.GONE
        binding.tvPdfLoading.visibility = View.VISIBLE
        binding.tvPdfLoading.text = "正在加载 PDF 预览..."

        // 找到 ivPdfPreview 的父容器，在其位置插入 ScrollView
        val parent = binding.ivPdfPreview.parent as ViewGroup
        val index = parent.indexOfChild(binding.ivPdfPreview)
        parent.removeView(binding.ivPdfPreview)
        parent.addView(scrollView, index)

        lifecycleScope.launch {
            try {
                val pageCount = pdfRenderer.getPageCountForFile(pdfName)
                if (pageCount == 0) {
                    binding.tvPdfLoading.text = "PDF 预览加载失败（文件不存在？）"
                    return@launch
                }

                binding.tvPdfLoading.text = "PDF 共 $pageCount 页"

                // 渲染每一页
                for (pageIndex in 0 until pageCount) {
                    val tvPageLabel = TextView(this@AddNoteActivity).apply {
                        text = "第 ${pageIndex + 1} / $pageCount 页"
                        textSize = 12f
                        setPadding(16, 16, 16, 4)
                        gravity = Gravity.CENTER
                        setTextColor(Color.parseColor("#AAAAAA"))
                    }
                    linearLayout.addView(tvPageLabel)

                    val bitmap = withContext(Dispatchers.IO) {
                        pdfRenderer.renderPageForFile(pdfName, pageIndex, 600, 800)
                    }
                    if (bitmap != null) {
                        val imageView = ImageView(this@AddNoteActivity).apply {
                            scaleType = ImageView.ScaleType.FIT_CENTER
                            setImageBitmap(bitmap)
                            adjustViewBounds = true
                            layoutParams = LinearLayout.LayoutParams(
                                LinearLayout.LayoutParams.MATCH_PARENT,
                                LinearLayout.LayoutParams.WRAP_CONTENT
                            )
                            setPadding(8, 4, 8, 8)
                        }
                        linearLayout.addView(imageView)
                    } else {
                        val tvError = TextView(this@AddNoteActivity).apply {
                            text = "❌ 第 ${pageIndex + 1} 页加载失败"
                            textSize = 14f
                            setPadding(16, 16, 16, 16)
                            setTextColor(Color.RED)
                        }
                        linearLayout.addView(tvError)
                    }
                }

                Log.i(TAG, "PDF 预览加载完成: $pageCount 页")
            } catch (e: Exception) {
                Log.e(TAG, "PDF 预览加载失败", e)
                binding.tvPdfLoading.text = "PDF 加载失败: ${e.message}"
            }
        }
    }

    private fun saveNote() {
        val title = binding.etTitle.text.toString().trim()
        val content = binding.etContent.text.toString().trim()
        val hasInk = binding.inkCanvas.hasInk()

        if (title.isEmpty() && content.isEmpty() && !hasInk && selectedPdfName.isEmpty()) {
            Toast.makeText(this, "请至少填写标题、内容、手写笔迹或插入PDF", Toast.LENGTH_SHORT).show()
            return
        }

        val noteId = "note_${System.currentTimeMillis()}"
        val now = System.currentTimeMillis()
        val inkPathData = if (hasInk) binding.inkCanvas.serializePaths() else ""

        val note = Note(
            noteId = noteId,
            title = title,
            content = content,
            inkPathData = inkPathData,
            pdfName = selectedPdfName,
            createdAt = now,
            updatedAt = now
        )

        val inkPath: Path? = if (hasInk) binding.inkCanvas.getInkPath() else null

        // 禁用按钮防止重复点击
        binding.btnSave.isEnabled = false
        binding.btnSave.text = "保存中..."

        lifecycleScope.launch {
            try {
                repository.saveNote(note, inkPath,
                    canvasWidth = binding.inkCanvas.width.toFloat().takeIf { it > 0 } ?: 1080f,
                    canvasHeight = binding.inkCanvas.height.toFloat().takeIf { it > 0 } ?: 400f
                )
                Log.i(TAG, "笔记保存成功: $noteId, title=$title, hasInk=$hasInk, pdf=$selectedPdfName")
                Toast.makeText(this@AddNoteActivity, "笔记已保存", Toast.LENGTH_SHORT).show()
                finish()
            } catch (e: Exception) {
                Log.e(TAG, "笔记保存失败", e)
                Toast.makeText(this@AddNoteActivity, "保存失败: ${e.message}", Toast.LENGTH_LONG).show()
                binding.btnSave.isEnabled = true
                binding.btnSave.text = "保存笔记"
            }
        }
    }
}
