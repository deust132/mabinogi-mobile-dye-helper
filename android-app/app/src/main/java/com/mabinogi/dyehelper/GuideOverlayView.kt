package com.mabinogi.dyehelper

import android.content.Context
import android.graphics.*
import android.view.View

class GuideOverlayView(context: Context) : View(context) {

    private val guidePaint = Paint().apply {
        color = Color.YELLOW
        strokeWidth = 4f
        style = Paint.Style.STROKE
        pathEffect = DashPathEffect(floatArrayOf(20f, 10f), 0f)
    }

    private val circlePaint = Paint().apply {
        color = Color.argb(150, 255, 255, 0)
        style = Paint.Style.FILL
    }

    private val detectedPaint = Paint().apply {
        color = Color.argb(150, 0, 255, 0)
        style = Paint.Style.FILL
    }

    private val textPaint = Paint().apply {
        color = Color.BLACK
        textSize = 40f
        textAlign = Paint.Align.CENTER
    }

    private var guide1X = 0.3f
    private var guide2X = 0.5f
    private var guide3X = 0.7f

    private var detectedPositions = listOf<Pair<Int, Int>>()
    private var blinkVisible = true

    init {
        // 점멸 효과
        postDelayed(object : Runnable {
            override fun run() {
                blinkVisible = !blinkVisible
                invalidate()
                postDelayed(this, 500)
            }
        }, 500)
    }

    fun setGuidePositions(x1: Float, x2: Float, x3: Float) {
        guide1X = x1
        guide2X = x2
        guide3X = x3
        invalidate()
    }

    fun setDetectedPositions(positions: List<Pair<Int, Int>>) {
        detectedPositions = positions
        invalidate()
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)

        val w = width.toFloat()
        val h = height.toFloat()

        // 가이드라인 3개 그리기
        val positions = listOf(
            Pair(guide1X * w, "4"),
            Pair(guide2X * w, "5"),
            Pair(guide3X * w, "6")
        )

        for ((x, label) in positions) {
            // 세로선
            canvas.drawLine(x, 0f, x, h, guidePaint)

            // 기준점 원
            canvas.drawCircle(x, 100f, 20f, circlePaint)

            // 번호
            canvas.drawText(label, x, 110f, textPaint)
        }

        // 검출된 위치 표시 (점멸)
        if (blinkVisible) {
            for ((x, y) in detectedPositions) {
                canvas.drawCircle(x.toFloat(), y.toFloat(), 15f, detectedPaint)
            }
        }
    }
}
