package com.thunder.app.ui

import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
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
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.outlined.Settings
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
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.thunder.app.R
import com.thunder.app.data.ThunderApi
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

data class Line(val who: String, val text: String)

private val Bg = Color(0xFF141416)
private val BgLift = Color(0xFF1A1A1E)
private val Surface = Color(0xFF1C1C21)
private val YouBubble = Color(0xFF26262C)
private val Hairline = Color(0xFF2C2C32)
private val Ink = Color(0xFFE8E8EA)
private val Mute = Color(0xFF8E8E94)
private val Gold = Color(0xFFC4A35A)

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
            .background(
                Brush.verticalGradient(
                    0f to BgLift,
                    0.22f to Bg,
                    1f to Bg
                )
            )
            .statusBarsPadding()
            .imePadding()
    ) {
        Row(
            Modifier
                .fillMaxWidth()
                .padding(start = 16.dp, end = 4.dp, top = 10.dp, bottom = 10.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            ThunderWordmark(Modifier.weight(1f))
            Text(
                if (server.isBlank()) "shell" else "main",
                color = if (server.isBlank()) Mute else Color(0xFF8FCB9B),
                fontSize = 11.sp,
                letterSpacing = 0.6.sp,
                modifier = Modifier.padding(end = 2.dp)
            )
            IconButton(onClick = { showSettings = true }) {
                Icon(Icons.Outlined.Settings, contentDescription = "settings", tint = Mute)
            }
        }
        Box(
            Modifier
                .fillMaxWidth()
                .height(1.dp)
                .background(Hairline)
        )

        if (lines.isEmpty() && !waiting) {
            Box(Modifier.weight(1f).fillMaxWidth(), contentAlignment = Alignment.Center) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Image(
                        painter = painterResource(R.drawable.thunder_face),
                        contentDescription = null,
                        contentScale = ContentScale.Fit,
                        modifier = Modifier.size(88.dp)
                    )
                    Spacer(Modifier.height(22.dp))
                    Text(
                        stringResource(R.string.brand_name),
                        color = Ink,
                        fontSize = 22.sp,
                        fontWeight = FontWeight.Medium,
                        letterSpacing = 1.6.sp
                    )
                    Spacer(Modifier.height(8.dp))
                    Text(
                        stringResource(R.string.empty_state_line),
                        color = Mute,
                        fontSize = 15.sp,
                        letterSpacing = 0.2.sp
                    )
                }
            }
        } else {
            LazyColumn(
                state = listState,
                modifier = Modifier.weight(1f).fillMaxWidth(),
                contentPadding = PaddingValues(horizontal = 18.dp, vertical = 16.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                items(lines) { line -> Bubble(line) }
                if (waiting) item { ThunderThinking() }
            }
        }

        Box(
            Modifier
                .fillMaxWidth()
                .height(1.dp)
                .background(Hairline.copy(alpha = 0.7f))
        )
        Row(
            Modifier
                .fillMaxWidth()
                .navigationBarsPadding()
                .padding(horizontal = 14.dp, vertical = 12.dp),
            verticalAlignment = Alignment.Bottom
        ) {
            Row(
                Modifier
                    .weight(1f)
                    .clip(RoundedCornerShape(12.dp))
                    .background(Surface)
                    .border(1.dp, Hairline, RoundedCornerShape(12.dp))
                    .padding(horizontal = 16.dp, vertical = 12.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                BasicTextField(
                    value = draft,
                    onValueChange = { draft = it },
                    modifier = Modifier.fillMaxWidth(),
                    textStyle = TextStyle(color = Ink, fontSize = 15.sp, lineHeight = 21.sp),
                    cursorBrush = SolidColor(Gold),
                    maxLines = 6,
                    decorationBox = { inner ->
                        if (draft.isEmpty()) {
                            Text(
                                stringResource(R.string.composer_hint),
                                color = Mute,
                                fontSize = 15.sp,
                                letterSpacing = 0.15.sp
                            )
                        }
                        inner()
                    }
                )
            }
            Spacer(Modifier.size(10.dp))
            IconButton(
                onClick = { send() },
                enabled = draft.isNotBlank() && !waiting,
                modifier = Modifier
                    .size(44.dp)
                    .clip(RoundedCornerShape(12.dp))
                    .background(if (draft.isNotBlank() && !waiting) Ink else Color(0xFF242428))
            ) {
                Icon(
                    Icons.AutoMirrored.Filled.Send,
                    contentDescription = "send",
                    tint = if (draft.isNotBlank() && !waiting) Color(0xFF141416) else Mute,
                    modifier = Modifier.size(18.dp)
                )
            }
        }
    }

    if (showSettings) {
        AlertDialog(
            onDismissRequest = { showSettings = false },
            containerColor = Surface,
            shape = RoundedCornerShape(12.dp),
            title = {
                Text(
                    "Server",
                    color = Ink,
                    fontWeight = FontWeight.Medium,
                    letterSpacing = 0.4.sp
                )
            },
            text = {
                Column {
                    Text(
                        "Leave empty for shell mode. Paste the Thunder Main URL when that box is running.",
                        color = Mute,
                        fontSize = 13.sp,
                        lineHeight = 18.sp
                    )
                    Spacer(Modifier.height(14.dp))
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
                            focusedIndicatorColor = Gold.copy(alpha = 0.7f),
                            unfocusedIndicatorColor = Hairline
                        )
                    )
                }
            },
            confirmButton = {
                TextButton(onClick = { showSettings = false }) {
                    Text("Done", color = Gold, letterSpacing = 0.4.sp)
                }
            }
        )
    }
}

@Composable
private fun ThunderWordmark(modifier: Modifier = Modifier) {
    val progress = remember { Animatable(0f) }
    val scope = rememberCoroutineScope()

    suspend fun play() {
        progress.snapTo(0f)
        delay(280)
        progress.animateTo(
            1f,
            tween(durationMillis = 1100, easing = FastOutSlowInEasing)
        )
    }

    LaunchedEffect(Unit) { play() }

    val p = progress.value
    Row(
        modifier
            .clickable(
                interactionSource = remember { MutableInteractionSource() },
                indication = null
            ) { scope.launch { play() } },
        verticalAlignment = Alignment.CenterVertically
    ) {
        Image(
            painter = painterResource(R.drawable.thunder_face),
            contentDescription = stringResource(R.string.brand_name),
            contentScale = ContentScale.Fit,
            modifier = Modifier
                .size((34f - 4f * p).dp)
                .graphicsLayer {
                    translationX = -4f * p
                    alpha = 0.96f
                }
        )
        Row(
            Modifier.graphicsLayer {
                alpha = p
                translationX = (1f - p) * 14f
            },
            verticalAlignment = Alignment.Bottom
        ) {
            Spacer(Modifier.width(8.dp))
            Text(
                "Thunder",
                color = Ink,
                fontSize = 18.sp,
                fontWeight = FontWeight.Medium,
                letterSpacing = 1.5.sp,
                maxLines = 1,
                overflow = TextOverflow.Clip
            )
            Text(
                " AI",
                color = Gold.copy(alpha = 0.88f),
                fontSize = 18.sp,
                fontWeight = FontWeight.Light,
                letterSpacing = 1.2.sp,
                maxLines = 1
            )
        }
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
                .clip(RoundedCornerShape(10.dp))
                .background(if (mine) YouBubble else Color.Transparent)
                .padding(horizontal = if (mine) 14.dp else 2.dp, vertical = 9.dp)
        ) {
            Text(line.text, color = Ink, fontSize = 15.sp, lineHeight = 22.sp)
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

    LaunchedEffect(Unit) {
        while (true) {
            delay(420)
            frame = (frame + 1) % frames.size
        }
    }

    Image(
        painter = painterResource(frames[frame]),
        contentDescription = stringResource(R.string.thinking_cd),
        contentScale = ContentScale.Fit,
        modifier = Modifier
            .padding(start = 2.dp, top = 2.dp, bottom = 2.dp)
            .height(26.dp)
            .aspectRatio(1f)
    )
}
