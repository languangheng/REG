package com.example.myapplication.ui

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Path
import android.graphics.RectF
import android.util.AttributeSet
import android.util.Log
import android.view.MotionEvent
import android.view.View

/**
 * InkCanvasView — 手写笔迹画板 View
 *
 * 功能:
 *   - 手指/触控笔在画板上绘制
 *   - 实时显示笔迹
 *   - 获取 Path 对象用于 bbox 计算
 *   - 清除画布
 *   - 序列化/反序列化 Path 数据（用于存储）
 */
class InkCanvasView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
    defStyleAttr: Int = 0
) : View(context, attrs, defStyleAttr) {

    private val paths = mutableListOf<Pair<Path, Paint>>()
    private var currentPath: Path? = null
    private var currentPaint: Paint = createPaint()

    // 画笔逻辑尺寸（用于归一化）
    var canvasLogicalWidth: Float = 1080f
    var canvasLogicalHeight: Float = 1920f

    private var lastX = 0f
    private var lastY = 0f

    companion object {
        private const val TAG = "InkCanvasView"
    }

    private fun createPaint(): Paint {
        return Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = Color.parseColor("#1565C0")  // 深蓝色
            style = Paint.Style.STROKE
            strokeWidth = 6f
            strokeCap = Paint.Cap.ROUND
            strokeJoin = Paint.Join.ROUND
        }
    }

    /**
     * 获取所有笔迹合并后的 Path（用于 bbox 计算）
     */
    fun getInkPath(): Path {
        val combined = Path()
        for ((p, _) in paths) {
            combined.addPath(p)
        }
        currentPath?.let { combined.addPath(it) }
        return combined
    }

    /**
     * 清除所有笔迹
     */
    fun clear() {
        paths.clear()
        currentPath = null
        invalidate()
    }

    /**
     * 判断是否有笔迹
     */
    fun hasInk(): Boolean = paths.isNotEmpty() || currentPath != null

    /**
     * 序列化 Path 数据为字符串
     * 格式: "M:x,y;L:x,y;L:x,y|M:x,y;L:x,y;..."
     * 坐标归一化到 [0,1]
     */
    fun serializePaths(): String {
        if (paths.isEmpty() && currentPath == null) return ""

        val w = width.toFloat()
        val h = height.toFloat()
        if (w <= 0f || h <= 0f) return ""

        val sb = StringBuilder()
        val allPaths = mutableListOf<Path>()
        allPaths.addAll(paths.map { it.first })
        currentPath?.let { allPaths.add(it) }

        for (path in allPaths) {
            val pathData = pathToNormalizedString(path, w, h)
            if (pathData.isNotEmpty()) {
                if (sb.isNotEmpty()) sb.append("|")
                sb.append(pathData)
            }
        }
        return sb.toString()
    }

    /**
     * 将 Path 转为归一化坐标字符串
     */
    private fun pathToNormalizedString(path: Path, w: Float, h: Float): String {
        val sb = StringBuilder()
        val pathMeasure = android.graphics.PathMeasure(path, false)
        val coords = FloatArray(2)
        var first = true

        while (pathMeasure.nextContour()) {
            // 简化: 采样关键点
            val length = pathMeasure.length
            val step = length / maxOf(1, (length / 20f).toInt())
            var dist = 0f
            while (dist <= length) {
                if (pathMeasure.getPosTan(dist, coords, null)) {
                    val nx = coords[0] / w
                    val ny = coords[1] / h
                    if (first) {
                        sb.append("M:$nx,$ny")
                        first = false
                    } else {
                        sb.append(";L:$nx,$ny")
                    }
                }
                dist += step
            }
        }
        return sb.toString()
    }

    /**
     * 从序列化数据恢复笔迹
     * 格式: "M:x,y;L:x,y;L:x,y|M:x,y;L:x,y;..."
     * 坐标是归一化的 [0,1]，需要乘以 View 尺寸还原
     */
    fun restoreFromSerializedData(data: String) {
        paths.clear()
        currentPath = null
        if (data.isEmpty()) return

        val w = width.toFloat().takeIf { it > 0 } ?: canvasLogicalWidth
        val h = height.toFloat().takeIf { it > 0 } ?: canvasLogicalHeight

        val pathStrings = data.split("|")
        for (pathStr in pathStrings) {
            if (pathStr.isEmpty()) continue
            val path = Path()
            val points = pathStr.split(";")
            for ((index, point) in points.withIndex()) {
                val parts = point.split(":")
                if (parts.size != 2) continue
                val cmd = parts[0]
                val coords = parts[1].split(",")
                if (coords.size != 2) continue
                val nx = coords[0].toFloat() * w
                val ny = coords[1].toFloat() * h
                when (cmd) {
                    "M" -> path.moveTo(nx, ny)
                    "L" -> path.lineTo(nx, ny)
                }
            }
            if (!path.isEmpty) {
                paths.add(path to createPaint())
            }
        }
        Log.d(TAG, "恢复笔迹: ${paths.size} 条路径")
        invalidate()
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        // 白色背景
        canvas.drawColor(Color.WHITE)
        // 网格线
        val gridPaint = Paint().apply {
            color = Color.argb(20, 0, 0, 0)
            strokeWidth = 1f
        }
        val step = width / 10f
        var i = step
        while (i < width) {
            canvas.drawLine(i, 0f, i, height.toFloat(), gridPaint)
            i += step
        }
        i = step
        while (i < height) {
            canvas.drawLine(0f, i, width.toFloat(), i, gridPaint)
            i += step
        }

        // 绘制所有路径
        for ((path, paint) in paths) {
            canvas.drawPath(path, paint)
        }
        currentPath?.let { canvas.drawPath(it, currentPaint) }
    }

    override fun onTouchEvent(event: MotionEvent): Boolean {
        val x = event.x
        val y = event.y

        when (event.action) {
            MotionEvent.ACTION_DOWN -> {
                currentPath = Path()
                currentPath?.moveTo(x, y)
                lastX = x
                lastY = y
            }
            MotionEvent.ACTION_MOVE -> {
                // 平滑曲线: 用二阶贝塞尔
                currentPath?.quadTo(lastX, lastY, (x + lastX) / 2, (y + lastY) / 2)
                lastX = x
                lastY = y
            }
            MotionEvent.ACTION_UP -> {
                currentPath?.lineTo(x, y)
                currentPath?.let { paths.add(it to currentPaint) }
                currentPath = null
                Log.d(TAG, "笔迹完成，总路径数: ${paths.size}")
            }
        }
        invalidate()
        return true
    }
}
