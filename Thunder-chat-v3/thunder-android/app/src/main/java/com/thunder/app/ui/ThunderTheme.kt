package com.thunder.app.ui

import android.app.Activity
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxScope
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.SideEffect
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalView
import androidx.core.view.WindowCompat

data class ThunderPalette(
    val isDark: Boolean,
    val slateTop: Color,
    val slateMid: Color,
    val slateDeep: Color,
    val surface: Color,
    val drawer: Color,
    val youBubble: Color,
    val hairline: Color,
    val ink: Color,
    val mute: Color,
    val gold: Color,
    val goldSoft: Color,
    val live: Color,
    val onGold: Color,
    val maintBg: Color,
    val maintInk: Color
) {
    companion object {
        val Light = ThunderPalette(
            isDark = false,
            slateTop = Color(0xFFF7F2EA),
            slateMid = Color(0xFFF1EBE2),
            slateDeep = Color(0xFFE7E0D4),
            surface = Color(0xFFFAF6EF),
            drawer = Color(0xFFF3EEE6),
            youBubble = Color(0xFFE8DFD0),
            hairline = Color(0xFFD4CBBB),
            ink = Color(0xFF2A261F),
            mute = Color(0xFF6F685C),
            gold = Color(0xFFB8923A),
            goldSoft = Color(0xFFC4A35A),
            live = Color(0xFF2F7A4A),
            onGold = Color(0xFF2A261F),
            maintBg = Color(0xFFF3E6C8),
            maintInk = Color(0xFF6B4E12)
        )
        val Dark = ThunderPalette(
            isDark = true,
            slateTop = Color(0xFF2C3340),
            slateMid = Color(0xFF1E232B),
            slateDeep = Color(0xFF16191F),
            surface = Color(0xFF252A33),
            drawer = Color(0xFF1A1E26),
            youBubble = Color(0xFF2E3440),
            hairline = Color(0xFF3A414D),
            ink = Color(0xFFEDE8DF),
            mute = Color(0xFF9A948A),
            gold = Color(0xFFC4A35A),
            goldSoft = Color(0xFFB8924A),
            live = Color(0xFF8FCB9B),
            onGold = Color(0xFF16191F),
            maintBg = Color(0xFF3A2F1B),
            maintInk = Color(0xFFE3B341)
        )
    }
}

val LocalThunderPalette = staticCompositionLocalOf { ThunderPalette.Light }

object ThunderInk {
    val SlateTop: Color @Composable get() = LocalThunderPalette.current.slateTop
    val SlateMid: Color @Composable get() = LocalThunderPalette.current.slateMid
    val SlateDeep: Color @Composable get() = LocalThunderPalette.current.slateDeep
    val Surface: Color @Composable get() = LocalThunderPalette.current.surface
    val Drawer: Color @Composable get() = LocalThunderPalette.current.drawer
    val YouBubble: Color @Composable get() = LocalThunderPalette.current.youBubble
    val Hairline: Color @Composable get() = LocalThunderPalette.current.hairline
    val Ink: Color @Composable get() = LocalThunderPalette.current.ink
    val Mute: Color @Composable get() = LocalThunderPalette.current.mute
    val Gold: Color @Composable get() = LocalThunderPalette.current.gold
    val GoldSoft: Color @Composable get() = LocalThunderPalette.current.goldSoft
    val Live: Color @Composable get() = LocalThunderPalette.current.live
    val OnGold: Color @Composable get() = LocalThunderPalette.current.onGold
    val MaintBg: Color @Composable get() = LocalThunderPalette.current.maintBg
    val MaintInk: Color @Composable get() = LocalThunderPalette.current.maintInk
}

@Composable
fun ThunderTheme(
    dark: Boolean,
    content: @Composable () -> Unit
) {
    val palette = if (dark) ThunderPalette.Dark else ThunderPalette.Light
    val view = LocalView.current
    SideEffect {
        val window = (view.context as? Activity)?.window ?: return@SideEffect
        window.statusBarColor = palette.slateTop.toArgb()
        window.navigationBarColor = palette.drawer.toArgb()
        val controller = WindowCompat.getInsetsController(window, view)
        controller.isAppearanceLightStatusBars = !dark
        controller.isAppearanceLightNavigationBars = !dark
    }
    CompositionLocalProvider(LocalThunderPalette provides palette, content = content)
}

@Composable
fun ThunderAtmosphere(
    modifier: Modifier = Modifier,
    bloomY: Float = 0.22f,
    content: @Composable BoxScope.() -> Unit
) {
    val pal = LocalThunderPalette.current
    Box(modifier.fillMaxSize()) {
        Canvas(Modifier.fillMaxSize()) {
            drawRect(
                Brush.verticalGradient(
                    0f to pal.slateTop,
                    0.38f to pal.slateMid,
                    1f to pal.slateDeep
                )
            )
            val bloom = size.minDimension * 0.72f
            val goldAlpha = if (pal.isDark) 0.16f else 0.22f
            val goldSoft = if (pal.isDark) 0.05f else 0.08f
            drawCircle(
                brush = Brush.radialGradient(
                    colors = listOf(
                        pal.gold.copy(alpha = goldAlpha),
                        pal.gold.copy(alpha = goldSoft),
                        Color.Transparent
                    ),
                    center = Offset(size.width * 0.5f, size.height * bloomY),
                    radius = bloom
                ),
                radius = bloom,
                center = Offset(size.width * 0.5f, size.height * bloomY)
            )
            val haze = if (pal.isDark) Color(0xFF3A4554).copy(alpha = 0.28f) else Color(0xFFFFF8EE).copy(alpha = 0.55f)
            drawCircle(
                brush = Brush.radialGradient(
                    colors = listOf(haze, Color.Transparent),
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
