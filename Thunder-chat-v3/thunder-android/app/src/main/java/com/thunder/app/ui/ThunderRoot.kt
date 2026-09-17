package com.thunder.app.ui

import android.widget.Toast
import android.speech.RecognizerIntent
import android.speech.tts.TextToSpeech
import android.content.Intent
import androidx.activity.compose.BackHandler
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.text.selection.SelectionContainer
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
import androidx.compose.foundation.layout.fillMaxHeight
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
import androidx.compose.material.icons.outlined.Add
import androidx.compose.material.icons.outlined.AutoAwesome
import androidx.compose.material.icons.outlined.ChatBubbleOutline
import androidx.compose.material.icons.outlined.Code
import androidx.compose.material.icons.outlined.ContentCopy
import androidx.compose.material.icons.outlined.FileDownload
import androidx.compose.material.icons.outlined.Close
import androidx.compose.material.icons.outlined.Delete
import androidx.compose.material.icons.outlined.Edit
import androidx.compose.material.icons.outlined.Menu
import androidx.compose.material.icons.outlined.Mic
import androidx.compose.material.icons.outlined.Save
import androidx.compose.material.icons.outlined.Settings
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.DrawerValue
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.ModalNavigationDrawer
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TextField
import androidx.compose.material3.TextFieldDefaults
import androidx.compose.material3.rememberDrawerState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.Lifecycle
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
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.thunder.app.R
import com.thunder.app.data.Chat
import com.thunder.app.data.ChatMessage
import com.thunder.app.data.ChatStore
import com.thunder.app.data.CreationStore
import com.thunder.app.data.AppRelease
import com.thunder.app.data.AppUpdater
import com.thunder.app.data.ThunderApi
import com.thunder.app.data.ThunderPrefs
import com.thunder.app.data.titleFromMessage
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

data class Line(val who: String, val text: String)

private enum class ThunderTab { Chat, Studio, Code }

@Composable
fun ThunderRoot() {
    val context = LocalContext.current
    val prefs = remember { ThunderPrefs(context) }
    val api = remember { ThunderApi(token = prefs.apiToken) }
    val store = remember { ChatStore(context) }
    val creations = remember { CreationStore(context) }
    val scope = rememberCoroutineScope()
    val drawerState = rememberDrawerState(DrawerValue.Closed)
    val listState = rememberLazyListState()

    var server by remember { mutableStateOf(prefs.serverUrl) }
    var dark by remember { mutableStateOf(prefs.darkMode) }
    var draft by remember { mutableStateOf("") }
    var showSettings by remember { mutableStateOf(false) }
    var waiting by remember { mutableStateOf(false) }
    var activeId by remember { mutableStateOf<String?>(store.newId()) }
    var chats by remember { mutableStateOf(store.list()) }
    var renameChat by remember { mutableStateOf<Chat?>(null) }
    var renameDraft by remember { mutableStateOf("") }
    var deleteChat by remember { mutableStateOf<Chat?>(null) }
    var tab by remember { mutableStateOf(ThunderTab.Chat) }
    val lines = remember { mutableStateListOf<Line>() }
    var maintenanceActive by remember { mutableStateOf(false) }
    var maintenanceMessage by remember { mutableStateOf("") }
    var maintenanceUntil by remember { mutableStateOf<Long?>(null) }
    var nowEpoch by remember { mutableStateOf(System.currentTimeMillis() / 1000) }
    var update by remember { mutableStateOf<AppRelease?>(null) }
    var showUpdate by remember { mutableStateOf(false) }
    var updating by remember { mutableStateOf(false) }
    var studioPrefill by remember { mutableStateOf<String?>(null) }
    // Code saved from a conversation lands in a project named after it, so a
    // week of chats does not become one undifferentiated heap of snippets.
    val codeProject = remember(activeId, chats) {
        chats.firstOrNull { it.id == activeId }?.title?.takeIf { it.isNotBlank() } ?: "scratch"
    }
    var apiToken by remember { mutableStateOf(prefs.apiToken) }
    var speakReplies by remember { mutableStateOf(prefs.speakReplies) }
    var voice by remember { mutableStateOf(prefs.voice) }
    // Android's on-device engine - no server, no model to ship.
    val tts = remember { TextToSpeech(context) { } }
    var replyPlayer by remember { mutableStateOf<android.media.MediaPlayer?>(null) }
    DisposableEffect(Unit) {
        onDispose { tts.stop(); tts.shutdown(); replyPlayer?.release() }
    }
    val installedVersion = remember {
        runCatching {
            context.packageManager.getPackageInfo(context.packageName, 0).versionName
        }.getOrNull().orEmpty()
    }

    fun refreshChats() {
        chats = store.list()
    }

    fun persistActive() {
        val id = activeId ?: return
        if (lines.isEmpty()) return
        val existing = store.get(id)
        val firstYou = lines.firstOrNull { it.who == "you" }?.text.orEmpty()
        val title = existing?.title?.takeIf { it.isNotBlank() && it != "New chat" }
            ?: titleFromMessage(firstYou)
        store.upsert(
            Chat(
                id = id,
                title = title,
                createdAt = existing?.createdAt ?: System.currentTimeMillis(),
                updatedAt = System.currentTimeMillis(),
                messages = lines.map { ChatMessage(it.who, it.text) }
            )
        )
        refreshChats()
    }

    fun openChat(id: String) {
        persistActive()
        activeId = id
        lines.clear()
        store.get(id)?.messages?.forEach { lines.add(Line(it.who, it.text)) }
        draft = ""
        waiting = false
        tab = ThunderTab.Chat
    }

    fun startNewChat() {
        persistActive()
        activeId = store.newId()
        lines.clear()
        draft = ""
        waiting = false
        tab = ThunderTab.Chat
    }

    fun send() {
        val msg = draft.trim()
        if (msg.isEmpty() || waiting || activeId == null) return
        draft = ""
        lines.add(Line("you", msg))
        persistActive()
        waiting = true
        scope.launch {
            // Add the bubble up front and grow it as text arrives, so the
            // reply appears immediately instead of after the whole generation.
            val slot = lines.size
            lines.add(Line("thunder", ""))
            var first = true
            val full = api.chatStream(server, msg, voice) { delta ->
                if (first) {
                    waiting = false
                    first = false
                }
                lines[slot] = Line("thunder", lines[slot].text + delta)
            }
            lines[slot] = Line("thunder", full)
            waiting = false
            persistActive()
            if (speakReplies && full.isNotBlank()) {
                // Prose only - reading a generation prompt aloud is noise.
                val spoken = parseSegments(full)
                    .filterIsInstance<Segment.Prose>()
                    .joinToString(" ") { it.text }
                    .ifBlank { full }
                val audio = api.speak(server, spoken, voice)
                if (audio != null) {
                    // Odris's neural voice.
                    runCatching {
                        val f = java.io.File(context.cacheDir, "reply.wav")
                        f.writeBytes(audio)
                        replyPlayer?.release()
                        replyPlayer = android.media.MediaPlayer().apply {
                            setDataSource(f.absolutePath); prepare(); start()
                        }
                    }
                } else {
                    // Voice node unreachable - the phone's own engine rather
                    // than silence.
                    tts.speak(spoken, TextToSpeech.QUEUE_FLUSH, null, "thunder-reply")
                }
            }
        }
    }

    LaunchedEffect(lines.size, waiting) {
        val last = lines.lastIndex + if (waiting) 1 else 0
        if (last >= 0) listState.animateScrollToItem(last.coerceAtLeast(0))
    }

    LaunchedEffect(server) {
        while (true) {
            if (server.isNotBlank()) {
                val st = api.status(server)
                if (!st.demo) {
                    maintenanceActive = st.maintenanceActive
                    maintenanceMessage = st.maintenanceMessage ?: "Thunder's down for maintenance."
                    maintenanceUntil = st.maintenanceUntilEpochSec
                }
            }
            delay(15_000)
        }
    }

    // The app is sideloaded, not on Play, so it asks Main whether a newer APK
    // has been published and surfaces a badge rather than silently going stale.
    suspend fun checkForUpdate() {
        // Main can pin a specific build; otherwise ask GitHub directly, which
        // needs no server at all and so works in shell mode too.
        val declared = if (server.isNotBlank()) api.appRelease(server) else null
        val rel = declared?.takeIf { !it.apkVersion.isNullOrBlank() }
            ?: AppUpdater.latestRelease()
        update = rel?.takeIf { AppUpdater.isNewer(it.apkVersion, installedVersion) }
    }

    LaunchedEffect(server) {
        while (true) {
            checkForUpdate()
            delay(60 * 60 * 1000L)
        }
    }

    // Also check whenever the app comes back to the foreground. A periodic
    // timer alone means a resumed app - which Android does not recompose -
    // could sit for an hour showing no badge when one is already available.
    val lifecycleOwner = LocalLifecycleOwner.current
    DisposableEffect(lifecycleOwner, server) {
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_RESUME) {
                scope.launch { checkForUpdate() }
            }
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose { lifecycleOwner.lifecycle.removeObserver(observer) }
    }

    LaunchedEffect(maintenanceActive) {
        while (maintenanceActive) {
            nowEpoch = System.currentTimeMillis() / 1000
            delay(1_000)
        }
    }

    ThunderTheme(dark = dark) {
    BackHandler(enabled = drawerState.isOpen || tab != ThunderTab.Chat) {
        when {
            drawerState.isOpen -> scope.launch { drawerState.close() }
            tab != ThunderTab.Chat -> tab = ThunderTab.Chat
        }
    }

    ModalNavigationDrawer(
        drawerState = drawerState,
        gesturesEnabled = true,
        drawerContent = {
            ThunderChatsDrawer(
                chats = chats,
                activeId = activeId,
                onNewChat = {
                    startNewChat()
                    scope.launch { drawerState.close() }
                },
                onOpen = { id ->
                    openChat(id)
                    scope.launch { drawerState.close() }
                },
                onRename = { chat ->
                    renameChat = chat
                    renameDraft = chat.title
                },
                onDelete = { deleteChat = it },
                onClose = { scope.launch { drawerState.close() } }
            )
        }
    ) {
        ThunderAtmosphere(bloomY = if (tab == ThunderTab.Studio) 0.16f else if (activeId == null) 0.30f else 0.10f) {
            Column(
                Modifier
                    .fillMaxSize()
                    .statusBarsPadding()
                    .imePadding()
            ) {
                ThunderTopBar(
                    inChat = tab == ThunderTab.Chat && activeId != null,
                    chatTitle = activeId?.let { id -> chats.find { it.id == id }?.title },
                    serverBlank = server.isBlank(),
                    updateReady = update != null,
                    onMenu = { scope.launch { drawerState.open() } },
                    onSettings = { showSettings = true },
                    onUpdate = { showUpdate = true }
                )
                Hairline()

                if (maintenanceActive) {
                    val countdown = maintenanceUntil?.let { until ->
                        val remaining = (until - nowEpoch).coerceAtLeast(0)
                        " (back in ${remaining / 60}:${(remaining % 60).toString().padStart(2, '0')})"
                    } ?: ""
                    Box(
                        Modifier
                            .fillMaxWidth()
                            .background(ThunderInk.MaintBg)
                            .padding(horizontal = 14.dp, vertical = 10.dp)
                    ) {
                        Text(maintenanceMessage + countdown, color = ThunderInk.MaintInk, fontSize = 13.sp)
                    }
                }

                if (tab == ThunderTab.Code) {
                    CodeVault(
                        server = server,
                        api = api,
                        modifier = Modifier.weight(1f)
                    )
                } else if (tab == ThunderTab.Studio) {
                    CreativeStudio(
                        server = server,
                        api = api,
                        store = creations,
                        prefill = studioPrefill,
                        onPrefillUsed = { studioPrefill = null },
                        modifier = Modifier.weight(1f)
                    )
                } else {
                    LazyColumn(
                        state = listState,
                        modifier = Modifier.weight(1f).fillMaxWidth(),
                        contentPadding = PaddingValues(horizontal = 18.dp, vertical = 16.dp),
                        verticalArrangement = Arrangement.spacedBy(12.dp)
                    ) {
                        items(lines) { line ->
                            Bubble(
                                line = line,
                                onSendToStudio = { prompt ->
                                    studioPrefill = prompt
                                    tab = ThunderTab.Studio
                                },
                                onSaveCode = { body, language ->
                                    scope.launch {
                                        val saved = api.saveCode(
                                            server, body, codeProject, null, language
                                        )
                                        Toast.makeText(
                                            context,
                                            // saved.project, not the chat title: the
                                            // server sanitises the name, and the toast
                                            // should say where the file actually went.
                                            if (saved != null) "Saved ${saved.name} to ${saved.project}"
                                            else "Could not save - is Main reachable?",
                                            Toast.LENGTH_SHORT
                                        ).show()
                                    }
                                }
                            )
                        }
                        if (waiting) item { ThunderThinking() }
                    }
                    Hairline(dim = true)
                    ThunderComposer(
                        draft = draft,
                        waiting = waiting,
                        onDraft = { draft = it },
                        onSend = { send() }
                    )
                }

                NavigationBar(
                    containerColor = ThunderInk.Drawer,
                    contentColor = ThunderInk.Ink,
                    modifier = Modifier.navigationBarsPadding()
                ) {
                    val colors = NavigationBarItemDefaults.colors(
                        selectedIconColor = ThunderInk.Gold,
                        selectedTextColor = ThunderInk.Gold,
                        indicatorColor = ThunderInk.Surface,
                        unselectedIconColor = ThunderInk.Mute,
                        unselectedTextColor = ThunderInk.Mute
                    )
                    NavigationBarItem(
                        selected = tab == ThunderTab.Chat,
                        onClick = { tab = ThunderTab.Chat },
                        icon = { Icon(Icons.Outlined.ChatBubbleOutline, contentDescription = null) },
                        label = { Text(stringResource(R.string.tab_chat)) },
                        colors = colors
                    )
                    NavigationBarItem(
                        selected = tab == ThunderTab.Studio,
                        onClick = { tab = ThunderTab.Studio },
                        icon = { Icon(Icons.Outlined.AutoAwesome, contentDescription = null) },
                        label = { Text(stringResource(R.string.tab_studio)) },
                        colors = colors
                    )
                    NavigationBarItem(
                        selected = tab == ThunderTab.Code,
                        onClick = { tab = ThunderTab.Code },
                        icon = { Icon(Icons.Outlined.Code, contentDescription = null) },
                        label = { Text(stringResource(R.string.tab_code)) },
                        colors = colors
                    )
                }
            }
        }
    }

    if (showSettings) {
        ServerDialog(
            server = server,
            onServer = {
                server = it
                prefs.serverUrl = it
            },
            token = apiToken,
            onToken = {
                apiToken = it
                prefs.apiToken = it
                api.token = it
            },
            voice = voice,
            onVoice = {
                voice = it
                prefs.voice = it
            },
            api = api,
            speak = speakReplies,
            onSpeak = {
                speakReplies = it
                prefs.speakReplies = it
                if (!it) tts.stop()
            },
            dark = dark,
            onDark = {
                dark = it
                prefs.darkMode = it
            },
            onDismiss = { showSettings = false }
        )
    }

    if (showUpdate) {
        val rel = update
        AlertDialog(
            onDismissRequest = { if (!updating) showUpdate = false },
            containerColor = ThunderInk.Surface,
            shape = RoundedCornerShape(14.dp),
            title = {
                Text(
                    stringResource(R.string.update_available),
                    color = ThunderInk.Ink,
                    fontWeight = FontWeight.Medium
                )
            },
            text = {
                Column {
                    Text(
                        "${installedVersion.ifBlank { "?" }} \u2192 ${rel?.apkVersion ?: "?"}",
                        color = ThunderInk.Ink,
                        fontSize = 14.sp
                    )
                    val notes = rel?.notes.orEmpty()
                    if (notes.isNotBlank()) {
                        Spacer(Modifier.height(8.dp))
                        Text(notes, color = ThunderInk.Mute, fontSize = 12.sp, lineHeight = 17.sp)
                    }
                    if (updating) {
                        Spacer(Modifier.height(12.dp))
                        LinearProgressIndicator(
                            color = ThunderInk.Gold,
                            trackColor = ThunderInk.Hairline,
                            modifier = Modifier.fillMaxWidth()
                        )
                    }
                }
            },
            confirmButton = {
                TextButton(
                    enabled = !updating && !rel?.apkUrl.isNullOrBlank(),
                    onClick = {
                        val url = rel?.apkUrl ?: return@TextButton
                        updating = true
                        scope.launch {
                            val apk = AppUpdater.download(context, url)
                            updating = false
                            when {
                                apk == null ->
                                    AppUpdater.openInBrowser(context, url)
                                !AppUpdater.signatureMatchesInstalled(context, apk) -> {
                                    // Better to say why than to let the system
                                    // installer fail with "App not installed".
                                    Toast.makeText(
                                        context,
                                        context.getString(R.string.update_signature_mismatch),
                                        Toast.LENGTH_LONG
                                    ).show()
                                }
                                !AppUpdater.installApk(context, apk) ->
                                    AppUpdater.openInBrowser(context, url)
                            }
                            showUpdate = false
                        }
                    }
                ) { Text(stringResource(R.string.update_install), color = ThunderInk.Gold) }
            },
            dismissButton = {
                TextButton(enabled = !updating, onClick = { showUpdate = false }) {
                    Text(stringResource(R.string.update_later), color = ThunderInk.Mute)
                }
            }
        )
    }

    renameChat?.let { chat ->
        AlertDialog(
            onDismissRequest = { renameChat = null },
            containerColor = ThunderInk.Surface,
            shape = RoundedCornerShape(12.dp),
            title = {
                Text(
                    stringResource(R.string.rename_chat),
                    color = ThunderInk.Ink,
                    fontWeight = FontWeight.Medium
                )
            },
            text = {
                TextField(
                    value = renameDraft,
                    onValueChange = { renameDraft = it },
                    singleLine = true,
                    colors = thunderFieldColors()
                )
            },
            confirmButton = {
                TextButton(
                    onClick = {
                        store.rename(chat.id, renameDraft)
                        refreshChats()
                        renameChat = null
                    }
                ) { Text("Save", color = ThunderInk.Gold) }
            },
            dismissButton = {
                TextButton(onClick = { renameChat = null }) {
                    Text("Cancel", color = ThunderInk.Mute)
                }
            }
        )
    }

    deleteChat?.let { chat ->
        AlertDialog(
            onDismissRequest = { deleteChat = null },
            containerColor = ThunderInk.Surface,
            shape = RoundedCornerShape(12.dp),
            title = {
                Text(
                    stringResource(R.string.delete_chat),
                    color = ThunderInk.Ink,
                    fontWeight = FontWeight.Medium
                )
            },
            text = {
                Text(
                    "Remove “${chat.title}” from this phone?",
                    color = ThunderInk.Mute,
                    fontSize = 14.sp
                )
            },
            confirmButton = {
                TextButton(
                    onClick = {
                        store.delete(chat.id)
                        if (activeId == chat.id) {
                            activeId = null
                            lines.clear()
                        }
                        refreshChats()
                        deleteChat = null
                    }
                ) { Text("Delete", color = ThunderInk.Gold) }
            },
            dismissButton = {
                TextButton(onClick = { deleteChat = null }) {
                    Text("Keep", color = ThunderInk.Mute)
                }
            }
        )
    }
    }
}

@Composable
private fun ThunderTopBar(
    inChat: Boolean,
    chatTitle: String?,
    serverBlank: Boolean,
    updateReady: Boolean,
    onMenu: () -> Unit,
    onSettings: () -> Unit,
    onUpdate: () -> Unit
) {
    Row(
        Modifier
            .fillMaxWidth()
            .padding(start = 4.dp, end = 4.dp, top = 8.dp, bottom = 8.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        IconButton(onClick = onMenu) {
            Icon(
                Icons.Outlined.Menu,
                contentDescription = stringResource(R.string.menu_cd),
                tint = ThunderInk.Ink
            )
        }
        if (inChat && !chatTitle.isNullOrBlank() && chatTitle != "New chat") {
            Text(
                chatTitle,
                color = ThunderInk.Ink,
                fontSize = 16.sp,
                fontWeight = FontWeight.Medium,
                letterSpacing = 0.3.sp,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
                modifier = Modifier.weight(1f)
            )
        } else {
            ThunderWordmark(Modifier.weight(1f))
        }
        Text(
            if (serverBlank) "shell" else "main",
            color = if (serverBlank) ThunderInk.Mute else ThunderInk.Live,
            fontSize = 11.sp,
            letterSpacing = 0.6.sp,
            modifier = Modifier.padding(end = 2.dp)
        )
        if (updateReady) {
            IconButton(onClick = onUpdate) {
                Icon(
                    Icons.Outlined.FileDownload,
                    contentDescription = stringResource(R.string.update_available),
                    tint = ThunderInk.Gold
                )
            }
        }
        IconButton(onClick = onSettings) {
            Icon(Icons.Outlined.Settings, contentDescription = "settings", tint = ThunderInk.Mute)
        }
    }
}

@Composable
private fun ThunderChatsDrawer(
    chats: List<Chat>,
    activeId: String?,
    onNewChat: () -> Unit,
    onOpen: (String) -> Unit,
    onRename: (Chat) -> Unit,
    onDelete: (Chat) -> Unit,
    onClose: () -> Unit
) {
    Column(
        Modifier
            .fillMaxHeight()
            .width(320.dp)
            .background(ThunderInk.Drawer)
            .statusBarsPadding()
            .navigationBarsPadding()
    ) {
        Row(
            Modifier
                .fillMaxWidth()
                .padding(start = 18.dp, end = 4.dp, top = 12.dp, bottom = 8.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                stringResource(R.string.chats_title),
                color = ThunderInk.Ink,
                fontSize = 18.sp,
                fontWeight = FontWeight.Medium,
                letterSpacing = 0.8.sp,
                modifier = Modifier.weight(1f)
            )
            IconButton(onClick = onClose) {
                Icon(
                    Icons.Outlined.Close,
                    contentDescription = stringResource(R.string.close_menu_cd),
                    tint = ThunderInk.Mute
                )
            }
        }
        Row(
            Modifier
                .padding(horizontal = 14.dp)
                .fillMaxWidth()
                .clip(RoundedCornerShape(12.dp))
                .background(ThunderInk.Surface)
                .border(1.dp, ThunderInk.Gold.copy(alpha = 0.45f), RoundedCornerShape(12.dp))
                .clickable(onClick = onNewChat)
                .padding(horizontal = 14.dp, vertical = 12.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Icon(Icons.Outlined.Add, contentDescription = null, tint = ThunderInk.Gold, modifier = Modifier.size(18.dp))
            Spacer(Modifier.width(10.dp))
            Text(
                stringResource(R.string.start_new_chat),
                color = ThunderInk.Ink,
                fontSize = 14.sp,
                fontWeight = FontWeight.Medium
            )
        }
        Spacer(Modifier.height(10.dp))
        Hairline()
        if (chats.isEmpty()) {
            Text(
                stringResource(R.string.no_chats_yet),
                color = ThunderInk.Mute,
                fontSize = 13.sp,
                modifier = Modifier.padding(horizontal = 20.dp, vertical = 22.dp)
            )
        } else {
            LazyColumn(modifier = Modifier.weight(1f), contentPadding = PaddingValues(vertical = 8.dp)) {
                items(chats, key = { it.id }) { chat ->
                    val selected = chat.id == activeId
                    Row(
                        Modifier
                            .fillMaxWidth()
                            .padding(horizontal = 8.dp, vertical = 2.dp)
                            .clip(RoundedCornerShape(10.dp))
                            .background(if (selected) ThunderInk.Surface else ThunderInk.Drawer)
                            .clickable { onOpen(chat.id) }
                            .padding(start = 12.dp, end = 2.dp, top = 8.dp, bottom = 8.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column(Modifier.weight(1f)) {
                            Text(
                                chat.title,
                                color = ThunderInk.Ink,
                                fontSize = 14.sp,
                                maxLines = 1,
                                overflow = TextOverflow.Ellipsis
                            )
                            Text(
                                "${chat.messages.size} lines",
                                color = ThunderInk.Mute,
                                fontSize = 11.sp
                            )
                        }
                        IconButton(onClick = { onRename(chat) }, modifier = Modifier.size(34.dp)) {
                            Icon(
                                Icons.Outlined.Edit,
                                contentDescription = stringResource(R.string.rename_chat),
                                tint = ThunderInk.Mute,
                                modifier = Modifier.size(16.dp)
                            )
                        }
                        IconButton(onClick = { onDelete(chat) }, modifier = Modifier.size(34.dp)) {
                            Icon(
                                Icons.Outlined.Delete,
                                contentDescription = stringResource(R.string.delete_chat),
                                tint = ThunderInk.Mute,
                                modifier = Modifier.size(16.dp)
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun ThunderComposer(
    draft: String,
    waiting: Boolean,
    onDraft: (String) -> Unit,
    onSend: () -> Unit
) {
    val context = LocalContext.current
    // Android's own recogniser, launched as an intent: the system handles the
    // microphone permission and the listening UI, so this needs neither a
    // permission request nor a speech model of our own.
    val speech = rememberLauncherForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) { result ->
        val said = result.data
            ?.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS)
            ?.firstOrNull()
            .orEmpty()
        if (said.isNotBlank()) onDraft(if (draft.isBlank()) said else "$draft $said")
    }
    Row(
        Modifier
            .fillMaxWidth()
            .padding(horizontal = 14.dp, vertical = 12.dp),
        verticalAlignment = Alignment.Bottom
    ) {
        Row(
            Modifier
                .weight(1f)
                .clip(RoundedCornerShape(12.dp))
                .background(ThunderInk.Surface.copy(alpha = 0.94f))
                .border(1.dp, ThunderInk.Hairline, RoundedCornerShape(12.dp))
                .padding(horizontal = 16.dp, vertical = 12.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            BasicTextField(
                value = draft,
                onValueChange = onDraft,
                modifier = Modifier.fillMaxWidth(),
                textStyle = TextStyle(color = ThunderInk.Ink, fontSize = 15.sp, lineHeight = 21.sp),
                cursorBrush = SolidColor(ThunderInk.Gold),
                maxLines = 6,
                decorationBox = { inner ->
                    if (draft.isEmpty()) {
                        Text(
                            stringResource(R.string.composer_hint),
                            color = ThunderInk.Mute,
                            fontSize = 15.sp,
                            letterSpacing = 0.15.sp
                        )
                    }
                    inner()
                }
            )
        }
        Spacer(Modifier.size(6.dp))
        IconButton(
            onClick = {
                val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
                    putExtra(
                        RecognizerIntent.EXTRA_LANGUAGE_MODEL,
                        RecognizerIntent.LANGUAGE_MODEL_FREE_FORM
                    )
                    putExtra(RecognizerIntent.EXTRA_PROMPT, context.getString(R.string.voice_prompt))
                }
                runCatching { speech.launch(intent) }.onFailure {
                    Toast.makeText(context, context.getString(R.string.voice_unavailable), Toast.LENGTH_SHORT).show()
                }
            },
            modifier = Modifier.size(44.dp)
        ) {
            Icon(Icons.Outlined.Mic, contentDescription = stringResource(R.string.voice_cd), tint = ThunderInk.Mute)
        }
        Spacer(Modifier.size(4.dp))
        val ready = draft.isNotBlank() && !waiting
        IconButton(
            onClick = onSend,
            enabled = ready,
            modifier = Modifier
                .size(44.dp)
                .clip(RoundedCornerShape(12.dp))
                .background(if (ready) ThunderInk.Gold else ThunderInk.Surface)
        ) {
            Icon(
                Icons.AutoMirrored.Filled.Send,
                contentDescription = "send",
                tint = if (ready) ThunderInk.OnGold else ThunderInk.Mute,
                modifier = Modifier.size(18.dp)
            )
        }
    }
}

private fun installedName(context: android.content.Context): String =
    runCatching {
        context.packageManager.getPackageInfo(context.packageName, 0).versionName
    }.getOrNull() ?: "?"


@Composable
private fun ServerDialog(
    server: String,
    onServer: (String) -> Unit,
    dark: Boolean,
    onDark: (Boolean) -> Unit,
    token: String,
    onToken: (String) -> Unit,
    voice: String,
    onVoice: (String) -> Unit,
    api: ThunderApi,
    speak: Boolean,
    onSpeak: (Boolean) -> Unit,
    onDismiss: () -> Unit
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        containerColor = ThunderInk.Surface,
        shape = RoundedCornerShape(12.dp),
        title = {
            Text(
                "Settings",
                color = ThunderInk.Ink,
                fontWeight = FontWeight.Medium,
                letterSpacing = 0.4.sp
            )
        },
        text = {
            Column {
                Text(
                    "Leave empty for shell mode. Paste the Thunder Main URL when that box is running. This stays on the phone.",
                    color = ThunderInk.Mute,
                    fontSize = 13.sp,
                    lineHeight = 18.sp
                )
                Spacer(Modifier.height(14.dp))
                TextField(
                    value = server,
                    onValueChange = onServer,
                    placeholder = { Text("http://192.168.x.x:8080") },
                    singleLine = true,
                    colors = thunderFieldColors()
                )
                Spacer(Modifier.height(18.dp))
                Row(
                    Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column(Modifier.weight(1f)) {
                        Text(
                            stringResource(R.string.settings_dark),
                            color = ThunderInk.Ink,
                            fontSize = 15.sp,
                            fontWeight = FontWeight.Medium
                        )
                        Text(
                            stringResource(R.string.settings_dark_hint),
                            color = ThunderInk.Mute,
                            fontSize = 12.sp,
                            lineHeight = 16.sp
                        )
                    }
                    Switch(
                        checked = dark,
                        onCheckedChange = onDark,
                        colors = SwitchDefaults.colors(
                            checkedThumbColor = ThunderInk.OnGold,
                            checkedTrackColor = ThunderInk.Gold,
                            uncheckedThumbColor = ThunderInk.Surface,
                            uncheckedTrackColor = ThunderInk.Hairline
                        )
                    )
                }
                Spacer(Modifier.height(14.dp))
                Text(
                    stringResource(R.string.settings_token),
                    color = ThunderInk.Ink,
                    fontSize = 15.sp,
                    fontWeight = FontWeight.Medium
                )
                Text(
                    stringResource(R.string.settings_token_hint),
                    color = ThunderInk.Mute,
                    fontSize = 12.sp,
                    lineHeight = 16.sp
                )
                Spacer(Modifier.height(6.dp))
                TextField(
                    value = token,
                    onValueChange = onToken,
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    placeholder = { Text("not set", color = ThunderInk.Mute) },
                    colors = TextFieldDefaults.colors(
                        focusedTextColor = ThunderInk.Ink,
                        unfocusedTextColor = ThunderInk.Ink,
                        focusedContainerColor = ThunderInk.SlateDeep,
                        unfocusedContainerColor = ThunderInk.SlateDeep,
                        cursorColor = ThunderInk.Gold,
                        focusedIndicatorColor = ThunderInk.Gold.copy(alpha = 0.7f),
                        unfocusedIndicatorColor = ThunderInk.Hairline
                    )
                )
                Spacer(Modifier.height(14.dp))
                Text(
                    stringResource(R.string.settings_voice),
                    color = ThunderInk.Ink,
                    fontSize = 15.sp,
                    fontWeight = FontWeight.Medium
                )
                Text(
                    stringResource(R.string.settings_voice_hint),
                    color = ThunderInk.Mute,
                    fontSize = 12.sp,
                    lineHeight = 16.sp
                )
                VoicePicker(
                    server = server,
                    api = api,
                    selected = voice,
                    onSelect = onVoice,
                    cacheDir = LocalContext.current.cacheDir
                )
                Spacer(Modifier.height(14.dp))
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Column(Modifier.weight(1f)) {
                        Text(
                            stringResource(R.string.speak_replies),
                            color = ThunderInk.Ink,
                            fontSize = 15.sp,
                            fontWeight = FontWeight.Medium
                        )
                        Text(
                            stringResource(R.string.speak_replies_hint),
                            color = ThunderInk.Mute,
                            fontSize = 12.sp,
                            lineHeight = 16.sp
                        )
                    }
                    Switch(
                        checked = speak,
                        onCheckedChange = onSpeak,
                        colors = SwitchDefaults.colors(
                            checkedThumbColor = ThunderInk.OnGold,
                            checkedTrackColor = ThunderInk.Gold,
                            uncheckedThumbColor = ThunderInk.Surface,
                            uncheckedTrackColor = ThunderInk.Hairline
                        )
                    )
                }
                Spacer(Modifier.height(16.dp))
                // Shown so "which build am I on" never means digging through
                // Android's own settings.
                Text(
                    stringResource(R.string.settings_version, installedName(LocalContext.current)),
                    color = ThunderInk.Mute,
                    fontSize = 11.sp
                )
            }
        },
        confirmButton = {
            TextButton(onClick = onDismiss) {
                Text("Done", color = ThunderInk.Gold, letterSpacing = 0.4.sp)
            }
        }
    )
}

@Composable
private fun thunderFieldColors() = TextFieldDefaults.colors(
    focusedTextColor = ThunderInk.Ink,
    unfocusedTextColor = ThunderInk.Ink,
    focusedContainerColor = ThunderInk.SlateDeep,
    unfocusedContainerColor = ThunderInk.SlateDeep,
    cursorColor = ThunderInk.Gold,
    focusedIndicatorColor = ThunderInk.Gold.copy(alpha = 0.7f),
    unfocusedIndicatorColor = ThunderInk.Hairline
)

@Composable
internal fun Hairline(dim: Boolean = false) {
    Box(
        Modifier
            .fillMaxWidth()
            .height(1.dp)
            .background(ThunderInk.Hairline.copy(alpha = if (dim) 0.65f else 0.9f))
    )
}

@Composable
private fun ThunderWordmark(modifier: Modifier = Modifier) {
    val progress = remember { Animatable(0f) }
    val scope = rememberCoroutineScope()

    suspend fun play() {
        progress.snapTo(0f)
        delay(180)
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
                color = ThunderInk.Ink,
                fontSize = 18.sp,
                fontWeight = FontWeight.Medium,
                letterSpacing = 1.5.sp,
                maxLines = 1,
                overflow = TextOverflow.Clip
            )
            Text(
                " AI",
                color = ThunderInk.Gold.copy(alpha = 0.88f),
                fontSize = 18.sp,
                fontWeight = FontWeight.Light,
                letterSpacing = 1.2.sp,
                maxLines = 1
            )
        }
    }
}

@Composable
private fun Bubble(
    line: Line,
    onSendToStudio: (String) -> Unit = {},
    onSaveCode: (String, String) -> Unit = { _, _ -> }
) {
    val mine = line.who == "you"
    val clipboard = LocalClipboardManager.current
    val context = LocalContext.current
    Row(
        Modifier.fillMaxWidth(),
        horizontalArrangement = if (mine) Arrangement.End else Arrangement.Start
    ) {
        Column(
            Modifier
                .widthIn(max = 320.dp)
                .clip(RoundedCornerShape(10.dp))
                .background(if (mine) ThunderInk.YouBubble else Color.Transparent)
                .padding(horizontal = if (mine) 14.dp else 2.dp, vertical = 9.dp)
        ) {
            // Selection handles partial copies; the button covers the common
            // case of wanting the whole thing, which is miserable to drag-select
            // inside a scrolling list.
            if (mine) {
                SelectionContainer {
                    Text(line.text, color = ThunderInk.Ink, fontSize = 15.sp, lineHeight = 22.sp)
                }
            } else {
                parseSegments(line.text).forEach { seg ->
                    when (seg) {
                        is Segment.Prose -> SelectionContainer {
                            Text(seg.text, color = ThunderInk.Ink, fontSize = 15.sp, lineHeight = 22.sp)
                        }
                        is Segment.Block -> ActionBlock(
                            text = seg.text,
                            isPrompt = seg.isPrompt,
                            onSave = { onSaveCode(seg.text, seg.language) },
                            onCopy = {
                                clipboard.setText(AnnotatedString(seg.text))
                                Toast.makeText(context, context.getString(R.string.copied), Toast.LENGTH_SHORT).show()
                            },
                            onSendToStudio = { onSendToStudio(seg.text) }
                        )
                    }
                    Spacer(Modifier.height(6.dp))
                }
            }
            if (!mine) {
                Row(
                    Modifier
                        .clip(RoundedCornerShape(6.dp))
                        .clickable {
                            clipboard.setText(AnnotatedString(line.text))
                            Toast.makeText(
                                context,
                                context.getString(R.string.copied),
                                Toast.LENGTH_SHORT
                            ).show()
                        }
                        .padding(horizontal = 4.dp, vertical = 4.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Icon(
                        Icons.Outlined.ContentCopy,
                        contentDescription = stringResource(R.string.copy_cd),
                        tint = ThunderInk.Mute,
                        modifier = Modifier.size(14.dp)
                    )
                    Spacer(Modifier.width(5.dp))
                    Text(
                        stringResource(R.string.copy_label),
                        color = ThunderInk.Mute,
                        fontSize = 11.sp
                    )
                }
            }
        }
    }
}

/** A block lifted out of a reply: copy it, or hand it straight to the Studio. */
@Composable
private fun ActionBlock(
    text: String,
    isPrompt: Boolean,
    onCopy: () -> Unit,
    onSendToStudio: () -> Unit,
    onSave: () -> Unit = {}
) {
    Column(
        Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(8.dp))
            .background(ThunderInk.SlateDeep)
            .border(1.dp, ThunderInk.Hairline, RoundedCornerShape(8.dp))
            .padding(10.dp)
    ) {
        SelectionContainer {
            Text(text, color = ThunderInk.Ink, fontSize = 13.sp, lineHeight = 19.sp)
        }
        Spacer(Modifier.height(8.dp))
        Row(verticalAlignment = Alignment.CenterVertically) {
            BlockAction(Icons.Outlined.ContentCopy, stringResource(R.string.copy_label), onCopy)
            if (isPrompt) {
                Spacer(Modifier.width(14.dp))
                BlockAction(Icons.Outlined.AutoAwesome, stringResource(R.string.send_to_studio), onSendToStudio)
            } else {
                Spacer(Modifier.width(14.dp))
                BlockAction(Icons.Outlined.Save, stringResource(R.string.save_code), onSave)
            }
        }
    }
}

@Composable
private fun BlockAction(icon: androidx.compose.ui.graphics.vector.ImageVector, label: String, onClick: () -> Unit) {
    Row(
        Modifier
            .clip(RoundedCornerShape(6.dp))
            .clickable { onClick() }
            .padding(horizontal = 4.dp, vertical = 3.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Icon(icon, contentDescription = label, tint = ThunderInk.Gold, modifier = Modifier.size(14.dp))
        Spacer(Modifier.width(5.dp))
        Text(label, color = ThunderInk.Gold, fontSize = 11.sp)
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
