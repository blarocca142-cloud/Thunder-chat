package com.thunder.app.ui

import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TextField
import androidx.compose.material3.TextFieldDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.thunder.app.R
import com.thunder.app.data.ThunderApi
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

data class Line(val who: String, val text: String)

private val Bg = Color(0xFF0A0A0A)
private val Surface = Color(0xFF161616)
private val YouBubble = Color(0xFF2A2A2E)
private val Ink = Color(0xFFF4F4F5)
private val Mute = Color(0xFF8B8B8B)
private val Gold = Color(0xFFE8C547)

@Composable
fun ThunderRoot() {
    val api = remember { ThunderApi() }
    var server by remember { mutableStateOf("") }
    var draft by remember { mutableStateOf("") }
    var showSettings by remember { mutableStateOf(false) }
    var waiting by remember { mutableStateOf(false) }
    val lines = remember { mutableStateListOf<Line>() }
    val scope = rememberCoroutineScope()
    val listState = rememberLazyListState()

    LaunchedEffect(lines.size, waiting) {
        val last = lines.lastIndex + if (waiting) 1 else 0
        if (last >= 0) listState.animateScrollToItem(last.coerceAtLeast(0))
    }

    fun send() {
        val msg = draft.trim()
        if (msg.isEmpty() || waiting) return
        draft = ""
        lines.add(Line("you", msg))
        waiting = true
        scope.launch {
            val reply = api.chat(server, msg)
            lines.add(Line("thunder", reply))
            waiting = false
        }
    }

    Column(
        Modifier
            .fillMaxSize()
            .background(Bg)
            .statusBarsPadding()
            .imePadding()
    ) {
        Row(
            Modifier
                .fillMaxWidth()
                .padding(horizontal = 8.dp, vertical = 6.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                "Thunder",
                color = Gold,
                fontSize = 22.sp,
                fontWeight = FontWeight.SemiBold,
                modifier = Modifier.padding(start = 12.dp)
            )
            Spacer(Modifier.weight(1f))
            Box(
                Modifier
                    .clip(RoundedCornerShape(20.dp))
                    .background(Color(0xFF1C1C1C))
                    .padding(horizontal = 10.dp, vertical = 5.dp)
            ) {
                Text(
                    if (server.isBlank()) "shell" else "main",
                    color = if (server.isBlank()) Mute else Color(0xFF7DDA88),
                    fontSize = 11.sp
                )
            }
            IconButton(onClick = { showSettings = true }) {
                Icon(Icons.Filled.Settings, contentDescription = "settings", tint = Mute)
            }
        }

        if (lines.isEmpty() && !waiting) {
            Box(Modifier.weight(1f).fillMaxWidth(), contentAlignment = Alignment.Center) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Text("Thunder", color = Ink, fontSize = 34.sp, fontWeight = FontWeight.Medium)
                    Spacer(Modifier.height(8.dp))
                    Text(stringResource(R.string.empty_state_line), color = Mute, fontSize = 16.sp)
                }
            }
        } else {
            LazyColumn(
                state = listState,
                modifier = Modifier.weight(1f).fillMaxWidth(),
                contentPadding = PaddingValues(horizontal = 14.dp, vertical = 12.dp),
                verticalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                items(lines) { line -> Bubble(line) }
                if (waiting) item { ThunderThinking() }
            }
        }

        Row(
            Modifier
                .fillMaxWidth()
                .navigationBarsPadding()
                .padding(horizontal = 12.dp, vertical = 10.dp),
            verticalAlignment = Alignment.Bottom
        ) {
            Row(
                Modifier
                    .weight(1f)
                    .clip(RoundedCornerShape(28.dp))
                    .background(Surface)
                    .padding(horizontal = 18.dp, vertical = 14.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                BasicTextField(
                    value = draft,
                    onValueChange = { draft = it },
                    modifier = Modifier.fillMaxWidth(),
                    textStyle = TextStyle(color = Ink, fontSize = 16.sp),
                    cursorBrush = SolidColor(Gold),
                    maxLines = 6,
                    decorationBox = { inner ->
                        if (draft.isEmpty()) Text(stringResource(R.string.composer_hint), color = Mute, fontSize = 16.sp)
                        inner()
                    }
                )
            }
            Spacer(Modifier.size(8.dp))
            IconButton(
                onClick = { send() },
                enabled = draft.isNotBlank() && !waiting,
                modifier = Modifier
                    .size(48.dp)
                    .clip(CircleShape)
                    .background(if (draft.isNotBlank() && !waiting) Ink else Color(0xFF2A2A2A))
            ) {
                Icon(
                    Icons.AutoMirrored.Filled.Send,
                    contentDescription = "send",
                    tint = if (draft.isNotBlank() && !waiting) Color.Black else Mute,
                    modifier = Modifier.size(20.dp)
                )
            }
        }
    }

    if (showSettings) {
        AlertDialog(
            onDismissRequest = { showSettings = false },
            containerColor = Surface,
            title = { Text("Main server", color = Ink) },
            text = {
                Column {
                    Text(
                        "Leave empty to stay in shell mode. Paste the Thunder Main URL when that box is running.",
                        color = Mute,
                        fontSize = 13.sp
                    )
                    Spacer(Modifier.height(12.dp))
                    TextField(
                        value = server,
                        onValueChange = { server = it },
                        placeholder = { Text("http://192.168.x.x:8080") },
                        singleLine = true,
                        colors = TextFieldDefaults.colors(
                            focusedTextColor = Ink,
                            unfocusedTextColor = Ink,
                            focusedContainerColor = Bg,
                            unfocusedContainerColor = Bg,
                            cursorColor = Gold,
                            focusedIndicatorColor = Gold,
                            unfocusedIndicatorColor = Color(0xFF333333)
                        )
                    )
                }
            },
            confirmButton = {
                TextButton(onClick = { showSettings = false }) {
                    Text("Done", color = Gold)
                }
            }
        )
    }
}

@Composable
private fun Bubble(line: Line) {
    val mine = line.who == "you"
    Row(
        Modifier.fillMaxWidth(),
        horizontalArrangement = if (mine) Arrangement.End else Arrangement.Start
    ) {
        Box(
            Modifier
                .widthIn(max = 320.dp)
                .clip(
                    RoundedCornerShape(
                        topStart = 18.dp,
                        topEnd = 18.dp,
                        bottomStart = if (mine) 18.dp else 4.dp,
                        bottomEnd = if (mine) 4.dp else 18.dp
                    )
                )
                .background(if (mine) YouBubble else Color.Transparent)
                .padding(horizontal = if (mine) 14.dp else 4.dp, vertical = 10.dp)
        ) {
            Text(line.text, color = Ink, fontSize = 16.sp, lineHeight = 22.sp)
        }
    }
}

@Composable
private fun ThunderThinking() {
    val frames = remember {
        listOf(
            R.drawable.thunder_think_1,
            R.drawable.thunder_think_2,
            R.drawable.thunder_think_3
        )
    }
    var frame by remember { mutableIntStateOf(0) }
    val bob = rememberInfiniteTransition(label = "thunder-toy")
    val lift by bob.animateFloat(
        initialValue = 0f,
        targetValue = -2.5f,
        animationSpec = infiniteRepeatable(tween(380), RepeatMode.Reverse),
        label = "lift"
    )

    LaunchedEffect(Unit) {
        while (true) {
            delay(320)
            frame = (frame + 1) % frames.size
        }
    }

    Image(
        painter = painterResource(frames[frame]),
        contentDescription = stringResource(R.string.thinking_cd),
        contentScale = ContentScale.Fit,
        modifier = Modifier
            .padding(start = 6.dp, top = 2.dp, bottom = 2.dp)
            .height(28.dp)
            .aspectRatio(1f)
            .graphicsLayer { translationY = lift }
    )
}
