package com.example.myapplication.ui

import android.content.Intent
import android.graphics.Path
import android.os.Bundle
import android.util.Log
import android.view.LayoutInflater
import android.view.ViewGroup
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.example.myapplication.data.Note
import com.example.myapplication.data.SearchDatabase
import com.example.myapplication.data.SearchResult
import com.example.myapplication.databinding.ActivityMainBinding
import com.example.myapplication.repository.SearchRepository
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private lateinit var repository: SearchRepository
    private lateinit var adapter: SearchResultAdapter
    private var searchJob: Job? = null

    // 笔记列表数据
    private var allNotes: List<Note> = emptyList()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        val database = SearchDatabase(this)
        repository = SearchRepository(database)

        adapter = SearchResultAdapter { result ->
            val intent = Intent(this, NoteDetailActivity::class.java).apply {
                putExtra(NoteDetailActivity.EXTRA_NOTE_ID, result.noteId)
                putExtra(NoteDetailActivity.EXTRA_SEARCH_QUERY, binding.etSearch.text.toString())
                putExtra(NoteDetailActivity.EXTRA_SOURCE_TYPE, result.sourceType)
                putExtra(NoteDetailActivity.EXTRA_PAGE_INDEX, result.pageIndex)
            }
            startActivity(intent)
        }
        binding.rvResults.layoutManager = LinearLayoutManager(this)
        binding.rvResults.adapter = adapter

        // FAB 按钮 → 跳转到添加笔记页
        binding.fabAddNote.setOnClickListener {
            startActivity(Intent(this, AddNoteActivity::class.java))
        }

        // 搜索框防抖
        binding.etSearch.addTextChangedListener(object : android.text.TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}
            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {}
            override fun afterTextChanged(s: android.text.Editable?) {
                val query = s?.toString()?.trim() ?: ""
                searchJob?.cancel()
                searchJob = lifecycleScope.launch {
                    delay(300)
                    if (query.isNotEmpty()) {
                        try {
                            repository.searchGlobal(query).collectLatest { results ->
                                adapter.submitList(results)
                            }
                        } catch (e: Exception) {
                            Log.e("MainActivity", "搜索失败", e)
                        }
                    } else {
                        // 无搜索词时展示笔记列表
                        showNoteList()
                    }
                }
            }
        })
    }

    override fun onResume() {
        super.onResume()
        // 每次返回时刷新笔记列表
        loadNotes()
    }

    /**
     * 加载所有笔记
     */
    private fun loadNotes() {
        lifecycleScope.launch {
            try {
                allNotes = repository.getAllNotes()
                if (binding.etSearch.text.isNullOrBlank()) {
                    showNoteList()
                }
            } catch (e: Exception) {
                Log.e("MainActivity", "加载笔记失败", e)
            }
        }
    }

    /**
     * 将笔记列表转为 SearchResult 格式展示
     */
    private fun showNoteList() {
        val results = allNotes.map { note ->
            SearchResult(
                noteId = note.noteId,
                pageIndex = 0,
                sourceType = note.primarySourceType(),
                bbox = android.graphics.RectF(0f, 0f, 1f, 1f),
                originalText = note.content,
                snippet = note.summary()
            )
        }
        adapter.submitList(results)
    }
}

// ════════════════════════════════════════════════════════════════
//  RecyclerView Adapter
// ════════════════════════════════════════════════════════════════

class SearchResultAdapter(
    private val onItemClick: (SearchResult) -> Unit
) : RecyclerView.Adapter<SearchResultAdapter.ViewHolder>() {

    private val items = mutableListOf<SearchResult>()

    fun submitList(newItems: List<SearchResult>) {
        items.clear()
        items.addAll(newItems)
        notifyDataSetChanged()
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val tv = TextView(parent.context).apply {
            layoutParams = ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
            )
            setPadding(48, 32, 48, 32)
            textSize = 14f
        }
        return ViewHolder(tv)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        holder.bind(items[position])
    }

    override fun getItemCount(): Int = items.size

    inner class ViewHolder(private val textView: TextView) : RecyclerView.ViewHolder(textView) {
        init {
            textView.setOnClickListener {
                val pos = bindingAdapterPosition
                if (pos != RecyclerView.NO_POSITION) {
                    onItemClick(items[pos])
                }
            }
        }

        fun bind(result: SearchResult) {
            val snippet = android.text.Html.fromHtml(
                "<b>[${result.sourceTypeLabel()}] ${result.noteId}</b><br/>${result.snippet}",
                android.text.Html.FROM_HTML_MODE_COMPACT
            )
            textView.text = snippet
        }
    }
}
