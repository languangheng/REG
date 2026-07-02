package com.example.myapplication.data

import android.graphics.Path
import android.graphics.RectF

/**
 * BBox 工具类 — 负责坐标归一化与格式转换
 *
 * 归一化规则:
 *   所有坐标统一归一化到 [0, 1] 范围，存储格式为 "x,y,w,h"
 *   坐标系原点在页面左上角，x 轴向右，y 轴向下
 */
object BBoxUtils {

    /**
     * 将像素坐标的 RectF 归一化到 [0, 1]
     *
     * @param rect           像素坐标矩形
     * @param logicalWidth   页面逻辑宽度
     * @param logicalHeight  页面逻辑高度
     * @return 归一化后的 RectF
     */
    fun normalize(rect: RectF, logicalWidth: Float, logicalHeight: Float): RectF {
        return RectF(
            rect.left / logicalWidth,
            rect.top / logicalHeight,
            (rect.left + rect.width()) / logicalWidth,
            (rect.top + rect.height()) / logicalHeight
        )
    }

    /**
     * PDF 坐标 Y 轴翻转
     *
     * PDF 原生坐标系: 原点左下角，y 轴向上
     * 我们的目标坐标系: 原点左上角，y 轴向下
     *
     * 转换公式: newTop = 1 - (oldBottom / pageHeight)
     *           newBottom = 1 - (oldTop / pageHeight)
     *
     * 注意: 调用此方法时 rect 应该已经是归一化坐标 [0,1]
     *
     * @param normalizedRect 已经归一化的 PDF 坐标 RectF (原点左下角)
     * @return 翻转后的归一化 RectF (原点左上角)
     */
    fun flipYForPdf(normalizedRect: RectF): RectF {
        val newTop = 1f - normalizedRect.bottom
        val newBottom = 1f - normalizedRect.top
        return RectF(
            normalizedRect.left,
            newTop,
            normalizedRect.right,
            newBottom
        )
    }

    /**
     * 计算手写笔迹 Path 的 Bounding Box 并归一化
     *
     * 使用 Path.computeBounds() 获取 Path 的最小外接矩形，
     * 然后归一化到 [0, 1] 范围
     *
     * @param path           手写笔迹 Path
     * @param logicalWidth   画布逻辑宽度
     * @param logicalHeight  画布逻辑高度
     * @return 归一化后的 RectF
     */
    fun fromPath(path: Path, logicalWidth: Float, logicalHeight: Float): RectF {
        val bounds = RectF()
        path.computeBounds(bounds, true)
        return normalize(bounds, logicalWidth, logicalHeight)
    }

    /**
     * 将 RectF 序列化为 "x,y,w,h" 字符串用于数据库存储
     */
    fun toDbString(rect: RectF): String {
        val w = rect.width()
        val h = rect.height()
        return "${rect.left},${rect.top},$w,$h"
    }

    /**
     * 从 "x,y,w,h" 字符串解析为 RectF
     */
    fun fromDbString(str: String): RectF {
        val parts = str.split(",")
        if (parts.size != 4) return RectF()
        val x = parts[0].toFloat()
        val y = parts[1].toFloat()
        val w = parts[2].toFloat()
        val h = parts[3].toFloat()
        return RectF(x, y, x + w, y + h)
    }
}
