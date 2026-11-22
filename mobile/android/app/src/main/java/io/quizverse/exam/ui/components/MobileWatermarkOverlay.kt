package io.quizverse.exam.ui.components

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.rotate
import androidx.compose.ui.graphics.nativeCanvas
import android.graphics.Paint
import android.graphics.Typeface

/**
 * Jetpack Compose Dynamic Candidate Watermark Canvas Overlay.
 *
 * Renders an unobtrusive, tamper-resistant diagonal watermark pattern across
 * the native mobile viewport containing the authenticated candidate identity.
 */
@Composable
fun MobileWatermarkOverlay(
    watermarkText: String,
    modifier: Modifier = Modifier,
    opacity: Float = 0.08f,
    fontSizeSp: Float = 12f,
    rotationDeg: Float = -25f,
    spacingPx: Float = 160f
) {
    Canvas(
        modifier = modifier.fillMaxSize()
    ) {
        val width = size.width
        val height = size.height

        val paint = Paint().apply {
            color = android.graphics.Color.WHITE
            alpha = (opacity * 255).toInt().coerceIn(10, 80)
            textSize = fontSizeSp * density
            typeface = Typeface.create(Typeface.MONOSPACE, Typeface.BOLD)
            textAlign = Paint.Align.CENTER
            isAntiAlias = true
        }

        val stepX = spacingPx * 2f
        val stepY = spacingPx * 1.2f

        var curY = -stepY
        while (curY < height + stepY * 2) {
            var curX = -stepX
            while (curX < width + stepX * 2) {
                drawContext.canvas.nativeCanvas.save()
                drawContext.canvas.nativeCanvas.rotate(rotationDeg, curX, curY)
                drawContext.canvas.nativeCanvas.drawText(watermarkText, curX, curY, paint)
                drawContext.canvas.nativeCanvas.restore()
                curX += stepX
            }
            curY += stepY
        }
    }
}
