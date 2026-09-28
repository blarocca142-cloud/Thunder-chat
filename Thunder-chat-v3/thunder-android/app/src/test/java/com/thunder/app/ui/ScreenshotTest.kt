package com.thunder.app.ui

import androidx.activity.compose.LocalActivityResultRegistryOwner
import androidx.activity.result.ActivityResultRegistry
import androidx.activity.result.ActivityResultRegistryOwner
import androidx.activity.result.contract.ActivityResultContract
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.core.app.ActivityOptionsCompat
import app.cash.paparazzi.DeviceConfig
import app.cash.paparazzi.Paparazzi
import org.junit.Rule
import org.junit.Test

/**
 * Renders the real app screens to PNG without a phone, so the look can be
 * checked before it ships. `gradle recordPaparazziDebug` writes the images to
 * app/src/test/snapshots/images.
 */
class ScreenshotTest {
    @get:Rule
    val paparazzi = Paparazzi(deviceConfig = DeviceConfig.PIXEL_6, maxPercentDifference = 0.1)

    private val noResults = object : ActivityResultRegistryOwner {
        override val activityResultRegistry = object : ActivityResultRegistry() {
            override fun <I, O> onLaunch(
                requestCode: Int, contract: ActivityResultContract<I, O>, input: I,
                options: ActivityOptionsCompat?
            ) = Unit
        }
    }

    @Composable
    private fun Host(content: @Composable () -> Unit) {
        CompositionLocalProvider(LocalActivityResultRegistryOwner provides noResults) { content() }
    }

    private val sample = listOf(
        Line("you", "write a python function that checks if a string is a palindrome and test it"),
        Line("thunder", "[running code - forge: tests, candidates, repair]\n" +
            "Here's a version that ignores case and punctuation. I ran it against 6 tests and they all passed.\n\n" +
            "```python\ndef is_palindrome(s: str) -> bool:\n    cleaned = [c.lower() for c in s if c.isalnum()]\n" +
            "    return cleaned == cleaned[::-1]\n```\n\n" +
            "**Why it works:** it keeps only letters and digits, lowercases them, and compares the list to its reverse."),
        Line("you", "what does ICD-10 code Z9Q.47 mean?"),
        Line("thunder", "[checking the official code list: Z9Q.47]\n" +
            "Z9Q.47 is not in the official 2026 ICD-10-CM list, so it is not a valid code. " +
            "If you tell me what the diagnosis is, I can look up the right one.")
    )

    @Test
    fun home_light() {
        paparazzi.snapshot { Host { ThunderRoot(previewDark = false) } }
    }

    @Test
    fun home_dark() {
        paparazzi.snapshot { Host { ThunderRoot(previewDark = true) } }
    }

    @Test
    fun chat_light() {
        paparazzi.snapshot { Host { ThunderRoot(previewLines = sample, previewDark = false) } }
    }

    @Test
    fun chat_dark() {
        paparazzi.snapshot { Host { ThunderRoot(previewLines = sample, previewDark = true) } }
    }
}
