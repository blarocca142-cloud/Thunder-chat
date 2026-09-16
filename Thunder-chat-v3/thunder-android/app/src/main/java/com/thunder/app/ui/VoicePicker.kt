package com.thunder.app.ui

import android.media.MediaPlayer
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.PlayArrow
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.thunder.app.data.ThunderApi
import com.thunder.app.data.ThunderVoice
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File

private const val PREVIEW_LINE =
    "Alright, the video model is loaded and the GPU is idle. Want me to start that first shot?"

/**
 * Grid of the voices Odris can speak in, each previewable before choosing.
 * Picking a voice also picks a personality - the server gives that voice its
 * own manner of speaking.
 */
@Composable
fun VoicePicker(
    server: String,
    api: ThunderApi,
    selected: String,
    onSelect: (String) -> Unit,
    cacheDir: File,
    modifier: Modifier = Modifier
) {
    val scope = rememberCoroutineScope()
    var voices by remember { mutableStateOf<List<ThunderVoice>>(emptyList()) }
    var previewing by remember { mutableStateOf<String?>(null) }
    var player by remember { mutableStateOf<MediaPlayer?>(null) }

    LaunchedEffect(server) { voices = api.voices(server) }

    fun preview(key: String) {
        if (previewing != null) return
        previewing = key
        scope.launch {
            val audio = api.speak(server, PREVIEW_LINE, key)
            if (audio != null) {
                withContext(Dispatchers.IO) {
                    val f = File(cacheDir, "voice_preview.wav")
                    f.writeBytes(audio)
                    player?.release()
                    player = MediaPlayer().apply {
                        setDataSource(f.absolutePath)
                        prepare()
                        start()
                    }
                }
            }
            previewing = null
        }
    }

    if (voices.isEmpty()) {
        Text(
            "No voices available — is Main reachable?",
            color = ThunderInk.Mute,
            fontSize = 12.sp,
            modifier = modifier
        )
        return
    }

    LazyVerticalGrid(
        columns = GridCells.Fixed(2),
        modifier = modifier.fillMaxWidth().height(230.dp),
        horizontalArrangement = Arrangement.spacedBy(8.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
        contentPadding = PaddingValues(vertical = 4.dp)
    ) {
        items(voices, key = { it.key }) { v ->
            val on = v.key == selected
            Column(
                Modifier
                    .clip(RoundedCornerShape(10.dp))
                    .background(if (on) ThunderInk.Surface else ThunderInk.SlateDeep)
                    .border(
                        1.dp,
                        if (on) ThunderInk.Gold else ThunderInk.Hairline,
                        RoundedCornerShape(10.dp)
                    )
                    .clickable { onSelect(v.key) }
                    .padding(10.dp)
            ) {
                Text(
                    v.label,
                    color = if (on) ThunderInk.Ink else ThunderInk.Mute,
                    fontSize = 13.sp,
                    fontWeight = if (on) FontWeight.Medium else FontWeight.Normal
                )
                Spacer(Modifier.height(6.dp))
                Row(
                    Modifier
                        .clip(RoundedCornerShape(6.dp))
                        .clickable { preview(v.key) }
                        .padding(horizontal = 2.dp, vertical = 2.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    if (previewing == v.key) {
                        CircularProgressIndicator(
                            color = ThunderInk.Gold,
                            strokeWidth = 2.dp,
                            modifier = Modifier.size(12.dp)
                        )
                    } else {
                        Icon(
                            Icons.Outlined.PlayArrow,
                            contentDescription = "preview",
                            tint = ThunderInk.Gold,
                            modifier = Modifier.size(14.dp)
                        )
                    }
                    Spacer(Modifier.width(4.dp))
                    Text("Preview", color = ThunderInk.Gold, fontSize = 11.sp)
                }
            }
        }
    }
}
