package com.thunder.app.ui

import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import com.thunder.app.R
import kotlinx.coroutines.delay

@Composable
fun ThunderSplash(onFinished: () -> Unit) {
    val reveal = remember { Animatable(0f) }
    val hold = remember { Animatable(1f) }

    LaunchedEffect(Unit) {
        reveal.snapTo(0f)
        reveal.animateTo(1f, tween(720, easing = FastOutSlowInEasing))
        delay(780)
        hold.animateTo(0f, tween(520, easing = FastOutSlowInEasing))
        onFinished()
    }

    val r = reveal.value
    val h = hold.value
    ThunderAtmosphere(bloomY = 0.42f) {
        Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            Image(
                painter = painterResource(R.drawable.thunder_splash),
                contentDescription = stringResource(R.string.splash_cd),
                contentScale = ContentScale.Fit,
                modifier = Modifier
                    .fillMaxWidth()
                    .graphicsLayer {
                        val grow = 1.16f + (1f - r) * 0.20f
                        scaleX = grow
                        scaleY = grow
                        alpha = (0.12f + 0.88f * r) * h
                    }
            )
        }
    }
}
