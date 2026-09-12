package com.thunder.app.ui

import android.content.Context
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.Bolt
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Stop
import androidx.compose.material.icons.filled.Workspaces
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.thunder.app.data.ThunderApi
import com.thunder.app.data.ThunderStatus
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

private val Bg = Color(0xFF0B0B0F)
private val Card = Color(0xFF16161C)
private val Gold = Color(0xFFF5C542)
private val Mute = Color(0xFF9A9AAA)
private val Mine = Color(0xFF2A2416)
private val Theirs = Color(0xFF1C1C24)

data class Bubble(val fromMe: Boolean, val text: String)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ThunderRoot() {
    val ctx = LocalContext.current
    val prefs = remember { ctx.getSharedPreferences("thunder", Context.MODE_PRIVATE) }
    var server by remember { mutableStateOf(prefs.getString("server", "") ?: "") }
    var showSettings by remember { mutableStateOf(server.isBlank()) }
    var showJob by remember { mutableStateOf(false) }
    var draft by remember { mutableStateOf("") }
    var jobTitle by remember { mutableStateOf("overnight coding") }
    var jobPrompt by remember { mutableStateOf("") }
    var sending by remember { mutableStateOf(false) }
    val messages = remember {
        mutableStateListOf(
            Bubble(false, "Thunder phone shell. Point me at Main, then we talk. Overnight jobs go to Cache — I just press the button.")
        )
    }
    var status by remember {
        mutableStateOf(
            ThunderStatus("idle", "no_heartbeat", "idle", null, null, null, "Waiting on Main", true)
        )
    }
    val api = remember { ThunderApi() }
    val scope = rememberCoroutineScope()
    val listState = rememberLazyListState()

    LaunchedEffect(server) {
        while (true) {
            status = api.status(server)
            delay(8000)
        }
    }
    LaunchedEffect(messages.size) {
        if (messages.isNotEmpty()) listState.animateScrollToItem(messages.lastIndex)
    }

    MaterialTheme(colorScheme = darkColorScheme(primary = Gold, background = Bg, surface = Card)) {
        Surface(Modifier.fillMaxSize(), color = Bg) {
            Column(
                Modifier
                    .fillMaxSize()
                    .statusBarsPadding()
                    .imePadding()
                    .navigationBarsPadding()
            ) {
                TopBar(status) { showSettings = true }
                StatusStrip(status)
                Box(Modifier.weight(1f)) {
                    LazyColumn(
                        state = listState,
                        modifier = Modifier.fillMaxSize(),
                        contentPadding = PaddingValues(16.dp, 8.dp, 16.dp, 88.dp),
                        verticalArrangement = Arrangement.spacedBy(10.dp)
                    ) {
                        items(messages) { ChatBubble(it) }
                    }
                    FloatingActionButton(
                        onClick = { showJob = true },
                        modifier = Modifier
                            .align(Alignment.BottomEnd)
                            .padding(16.dp),
                        containerColor = Gold,
                        contentColor = Color.Black
                    ) {
                        Icon(Icons.Default.Workspaces, contentDescription = "Queue job")
                    }
                }
                Row(
                    Modifier
                        .fillMaxWidth()
                        .background(Card)
                        .padding(10.dp),
                    verticalAlignment = Alignment.Bottom
                ) {
                    OutlinedTextField(
                        value = draft,
                        onValueChange = { draft = it },
                        modifier = Modifier.weight(1f),
                        placeholder = { Text("Talk to Thunder", color = Mute) },
                        colors = fieldColors(),
                        maxLines = 5
                    )
                    Spacer(Modifier.width(8.dp))
                    IconButton(
                        enabled = draft.isNotBlank() && !sending,
                        onClick = {
                            val text = draft.trim()
                            draft = ""
                            messages.add(Bubble(true, text))
                            sending = true
                            scope.launch {
                                val reply = api.chat(server, text)
                                messages.add(Bubble(false, reply))
                                sending = false
                            }
                        }
                    ) {
                        Icon(Icons.AutoMirrored.Filled.Send, contentDescription = "Send", tint = Gold)
                    }
                }
            }
        }

        if (showSettings) {
            AlertDialog(
                onDismissRequest = { showSettings = false },
                title = { Text("Thunder-Main URL") },
                text = {
                    Column {
                        Text("Tailscale or LAN only. Example http://100.x.x.x:8080", color = Mute, fontSize = 13.sp)
                        Spacer(Modifier.height(8.dp))
                        OutlinedTextField(
                            value = server,
                            onValueChange = { server = it },
                            placeholder = { Text("http://thunder-main:8080") },
                            colors = fieldColors()
                        )
                    }
                },
                confirmButton = {
                    TextButton(onClick = {
                        prefs.edit().putString("server", server.trim()).apply()
                        showSettings = false
                    }) { Text("Save", color = Gold) }
                },
                dismissButton = {
                    TextButton(onClick = { showSettings = false }) { Text("Close") }
                }
            )
        }

        if (showJob) {
            AlertDialog(
                onDismissRequest = { showJob = false },
                title = { Text("Queue overnight job") },
                text = {
                    Column {
                        OutlinedTextField(
                            value = jobTitle,
                            onValueChange = { jobTitle = it },
                            label = { Text("Title") },
                            colors = fieldColors()
                        )
                        Spacer(Modifier.height(8.dp))
                        OutlinedTextField(
                            value = jobPrompt,
                            onValueChange = { jobPrompt = it },
                            label = { Text("What Cache should do") },
                            colors = fieldColors(),
                            minLines = 3
                        )
                        if (status.jobId != null) {
                            Spacer(Modifier.height(8.dp))
                            Text("Active: ${status.jobTitle ?: status.jobId}", color = Mute, fontSize = 13.sp)
                        }
                    }
                },
                confirmButton = {
                    Button(
                        onClick = {
                            scope.launch {
                                val msg = api.queueJob(server, jobTitle, jobPrompt)
                                messages.add(Bubble(false, msg))
                                status = api.status(server)
                            }
                            showJob = false
                        },
                        colors = ButtonDefaults.buttonColors(containerColor = Gold, contentColor = Color.Black)
                    ) { Text("Queue") }
                },
                dismissButton = {
                    TextButton(onClick = {
                        scope.launch {
                            val msg = api.cancelJob(server, status.jobId)
                            messages.add(Bubble(false, msg))
                            status = api.status(server)
                        }
                        showJob = false
                    }) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(Icons.Default.Stop, contentDescription = null, tint = Mute)
                            Spacer(Modifier.width(4.dp))
                            Text("Cancel active", color = Mute)
                        }
                    }
                }
            )
        }
    }
}

@Composable
private fun TopBar(status: ThunderStatus, onSettings: () -> Unit) {
    Row(
        Modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Icon(Icons.Default.Bolt, contentDescription = null, tint = Gold, modifier = Modifier.size(28.dp))
        Spacer(Modifier.width(8.dp))
        Column(Modifier.weight(1f)) {
            Text("THUNDER", fontWeight = FontWeight.Bold, letterSpacing = 2.sp, color = Color.White)
            Text(
                if (status.demo) "demo · not on Main yet" else "mode ${status.mode}",
                color = Mute,
                fontSize = 12.sp
            )
        }
        IconButton(onClick = onSettings) {
            Icon(Icons.Default.Settings, contentDescription = "Settings", tint = Mute)
        }
    }
}

@Composable
private fun StatusStrip(status: ThunderStatus) {
    val color = when (status.odriss) {
        "ok" -> Color(0xFF3DDC84)
        "stuck" -> Color(0xFFFF8A4C)
        else -> Color(0xFF666676)
    }
    Row(
        Modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp)
            .clip(RoundedCornerShape(12.dp))
            .background(Card)
            .padding(12.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Box(
            Modifier
                .size(10.dp)
                .clip(CircleShape)
                .background(color)
        )
        Spacer(Modifier.width(10.dp))
        Column(Modifier.weight(1f)) {
            Text("Odris ${status.odriss.replace('_', ' ')}  ·  cache ${status.cache}", color = Color.White, fontSize = 13.sp)
            Text(
                status.jobTitle?.let { "$it${status.progress?.let { p -> " · $p" } ?: ""}" }
                    ?: status.message,
                color = Mute,
                fontSize = 12.sp
            )
        }
    }
}

@Composable
private fun ChatBubble(b: Bubble) {
    Row(
        Modifier.fillMaxWidth(),
        horizontalArrangement = if (b.fromMe) Arrangement.End else Arrangement.Start
    ) {
        Text(
            b.text,
            color = Color.White,
            fontSize = 15.sp,
            modifier = Modifier
                .clip(RoundedCornerShape(16.dp))
                .background(if (b.fromMe) Mine else Theirs)
                .padding(12.dp, 10.dp)
        )
    }
}

@Composable
private fun fieldColors() = OutlinedTextFieldDefaults.colors(
    focusedBorderColor = Gold,
    unfocusedBorderColor = Color(0xFF2A2A33),
    focusedTextColor = Color.White,
    unfocusedTextColor = Color.White,
    cursorColor = Gold
)
