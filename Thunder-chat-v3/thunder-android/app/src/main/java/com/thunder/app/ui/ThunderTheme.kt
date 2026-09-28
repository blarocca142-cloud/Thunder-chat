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
        // 1.9 redesign: crisp neutrals like the frontier apps, gold kept as
        // Thunder's one accent. The parchment tint is gone.
        val Light = ThunderPalette(
            isDark = false,
            slateTop = Color(0xFFFFFFFF),
            slateMid = Color(0xFFFCFCFB),
            slateDeep = Color(0xFFF7F7F5),
            surface = Color(0xFFFFFFFF),
            drawer = Color(0xFFF7F7F5),
            youBubble = Color(0xFFF1F0EC),
            hairline = Color(0xFFE7E5E0),
            ink = Color(0xFF1B1B1A),
            mute = Color(0xFF6E6C67),
            gold = Color(0xFFB07A1E),
            goldSoft = Color(0xFFF6EEDD),
            live = Color(0xFF1F8A4C),
            onGold = Color(0xFFFFFFFF),
            maintBg = Color(0xFFFBF1DC),
            maintInk = Color(0xFF6B4E12)
        )
        val Dark = ThunderPalette(
            isDark = true,
            slateTop = Color(0xFF0F1012),
            slateMid = Color(0xFF0F1012),
            slateDeep = Color(0xFF15171A),
            surface = Color(0xFF1A1C20),
            drawer = Color(0xFF131417),
            youBubble = Color(0xFF24272C),
            hairline = Color(0xFF2B2E34),
            ink = Color(0xFFECECEA),
            mute = Color(0xFF8F939B),
            gold = Color(0xFFE2B04E),
            goldSoft = Color(0xFF2A2417),
            live = Color(0xFF6FCF97),
            onGold = Color(0xFF15171A),
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
        // Flat, like the apps it is measured against. The gold bloom read as
        // decoration and competed with the conversation.
        Canvas(Modifier.fillMaxSize()) { drawRect(pal.slateMid) }
        content()
    }
}
