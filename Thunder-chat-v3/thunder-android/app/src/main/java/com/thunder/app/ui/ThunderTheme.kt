package com.thunder.app.ui

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxScope
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color

object ThunderInk {
    val SlateTop = Color(0xFF2C3340)
    val SlateMid = Color(0xFF1E232B)
    val SlateDeep = Color(0xFF16191F)
    val Surface = Color(0xFF252A33)
    val Drawer = Color(0xFF1A1E26)
    val YouBubble = Color(0xFF2E3440)
    val Hairline = Color(0xFF3A414D)
    val Ink = Color(0xFFEDE8DF)
    val Mute = Color(0xFF9A948A)
    val Gold = Color(0xFFC4A35A)
    val GoldSoft = Color(0xFFB8924A)
    val Live = Color(0xFF8FCB9B)
}

@Composable
fun ThunderAtmosphere(
    modifier: Modifier = Modifier,
    bloomY: Float = 0.22f,
    content: @Composable BoxScope.() -> Unit
) {
    Box(modifier.fillMaxSize()) {
        Canvas(Modifier.fillMaxSize()) {
            drawRect(
                Brush.verticalGradient(
                    0f to ThunderInk.SlateTop,
                    0.38f to ThunderInk.SlateMid,
                    1f to ThunderInk.SlateDeep
                )
            )
            val bloom = size.minDimension * 0.72f
            drawCircle(
                brush = Brush.radialGradient(
                    colors = listOf(
                        ThunderInk.Gold.copy(alpha = 0.16f),
                        ThunderInk.Gold.copy(alpha = 0.05f),
                        Color.Transparent
                    ),
                    center = Offset(size.width * 0.5f, size.height * bloomY),
                    radius = bloom
                ),
                radius = bloom,
                center = Offset(size.width * 0.5f, size.height * bloomY)
            )
            drawCircle(
                brush = Brush.radialGradient(
                    colors = listOf(
                        Color(0xFF3A4554).copy(alpha = 0.28f),
                        Color.Transparent
                    ),
                    center = Offset(size.width * 0.18f, size.height * 0.08f),
                    radius = size.minDimension * 0.55f
                ),
                radius = size.minDimension * 0.55f,
                center = Offset(size.width * 0.18f, size.height * 0.08f)
            )
        }
        content()
    }
}
