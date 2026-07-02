package com.example.myapplication.ui

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.RectF
import android.util.AttributeSet
import android.util.Log
import android.view.View

/**
 * HighlightOverlayView — 高亮覆盖层 View
 *
 * 核心设计:
 *   - 完全透明的 View，叠加在内容（PDF Bitmap / TextView）之上
 *   - 绝不修改原始 Bitmap，所有高亮绘制在此透明 View 上
 *   - 接收归一化的 bbox 列表 [0, 1]
 *   - 支持 contentRect: 当 ImageView 使用 fitCenter 时，Bitmap 实际显示区域
 *     可能小于 View 尺寸（有黑边），高亮需要限制在 contentRect 内
 *
 * 坐标映射逻辑:
 *
 *   归一化 bbox [0,1]  →  contentRect 内的像素坐标
 *
 *   如果没有设置 contentRect（默认 null），则使用整个 View 尺寸
 *
 *   highlightX = contentRect.left + normalizedX * contentRect.width()
 *   highlightY = contentRect.top  + normalizedY * contentRect.height()
 *
 * 缩略图适配:
 *   复用同一个 View，传入缩略图的 contentRect 即可自动适配
 */
class HighlightOverlayView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
    defStyleAttr: Int = 0
) : View(context, attrs, defStyleAttr) {

    private val TAG = "HighlightOverlayView"

    // ── 页面逻辑尺寸 ──
    // 默认 1f: 归一化坐标直接乘以 contentRect 宽高
    var pageLogicalWidth: Float = 1f
        set(value) {
            field = value
            invalidate()
        }

    var pageLogicalHeight: Float = 1f
        set(value) {
            field = value
            invalidate()
        }

    // ── Bitmap 在 ImageView 中的实际显示区域 ──
    // fitCenter 模式下 Bitmap 可能不充满整个 View
    // 高亮需要限制在此区域内
    private var contentRect: RectF? = null

    // ── 高亮数据 ──
    private val hits = mutableListOf<RectF>()

    // ── 画笔配置 ──
    private val highlightPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.argb(80, 255, 200, 0)  // 半透明黄色填充
        style = Paint.Style.FILL
    }

    private val strokePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.argb(200, 255, 150, 0) // 橙色描边
        style = Paint.Style.STROKE
        strokeWidth = 3f
    }

    /**
     * 设置 Bitmap 在 ImageView 中的实际显示区域
     * 用于 fitCenter 等缩放模式下纠正高亮位置
     *
     * 传 null 表示使用整个 View 尺寸（适合 contentRect == View 尺寸的场景）
     */
    fun setContentRect(rect: RectF?) {
        contentRect = rect
        invalidate()
    }

    /**
     * 设置高亮命中区域
     *
     * @param list 归一化的 bbox 列表 (RectF)，取值范围 [0, 1]
     *             坐标系: 原点左上角，x 向右，y 向下
     */
    fun setHits(list: List<RectF>) {
        hits.clear()
        hits.addAll(list)
        invalidate()
    }

    fun clearHits() {
        hits.clear()
        invalidate()
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)

        if (hits.isEmpty()) return

        // 获取有效绘制区域
        // 如果设置了 contentRect，使用 contentRect（fitCenter 模式下 Bitmap 的实际显示区域）
        // 否则使用整个 View 尺寸
        val rect = contentRect ?: RectF(0f, 0f, width.toFloat(), height.toFloat())

        if (rect.width() <= 0f || rect.height() <= 0f) return

        // scale: 归一化坐标 [0,1] → contentRect 像素坐标
        val scaleX = rect.width() / pageLogicalWidth
        val scaleY = rect.height() / pageLogicalHeight

        for (normalizedRect in hits) {
            // 坐标映射:
            //   drawX = contentRect.left + normalizedX * scaleX
            //   drawY = contentRect.top  + normalizedY * scaleY
            //
            // 这样高亮会精确映射到 Bitmap 的实际显示区域，
            // 不受 ImageView fitCenter 黑边影响
            val drawRect = RectF(
                rect.left + normalizedRect.left * scaleX,
                rect.top + normalizedRect.top * scaleY,
                rect.left + normalizedRect.right * scaleX,
                rect.top + normalizedRect.bottom * scaleY
            )

            Log.d(TAG, "Draw: normalized=$normalizedRect → pixel=$drawRect, contentRect=$rect")

            canvas.drawRoundRect(drawRect, 4f, 4f, highlightPaint)
            canvas.drawRoundRect(drawRect, 4f, 4f, strokePaint)
        }
    }
}
