# 项目记忆

## 项目: 高性能笔记搜索模块 Demo

### 技术栈
- Android (Kotlin), Gradle Groovy DSL, AGP 9.2.1, Gradle 9.4.1, JDK 21
- SQLite FTS5 (原生 SQLiteOpenHelper，非 Room)
- jieba-kmp-android:1.0.0 (中文分词)
- Kotlin Coroutines (所有 DB/PDF 操作在 Dispatchers.IO)
- Android 原生 PdfRenderer

### 项目路径
`C:\Users\languangheng\.qclaw\workspace-tfxjjhfnjialcuju\notes\notedemo`

### 核心架构
- `search_meta` 普通表: note_id, page_index, source_type(TEXT/PDF/INK), bbox("x,y,w,h" 归一化), original_text
- `search_index` FTS5 虚拟表: token(jieba 分词空格拼接), meta_rowid(外键→search_meta.rowid), tokenize='ascii'
- 所有 bbox 归一化到 [0,1]，原点左上角，y 轴向下
- PDF 需 Y 轴翻转: newTop = 1 - oldBottom
- 手写笔迹用 Path.computeBounds() 计算 BBox
- HighlightOverlayView 透明叠加层，不修改原始 Bitmap
- 入库先删后插，包裹在 transaction 中

### AGP 9.x 编译要点（重要！）
- AGP 9.x 内置 Kotlin 插件，**不要**单独 apply `org.jetbrains.kotlin.android`，否则冲突报错
- Kotlin 配置用 `kotlin { compilerOptions { jvmTarget.set(...) } }` 而非 `kotlinOptions { jvmTarget = ... }`
- androidx 库最新版要求 compileSdk 35+
