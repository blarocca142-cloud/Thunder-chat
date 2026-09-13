package com.thunder.app.ui

import androidx.activity.compose.BackHandler
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
import androidx.compose.material.icons.outlined.Close
import androidx.compose.material.icons.outlined.Delete
import androidx.compose.material.icons.outlined.Edit
import androidx.compose.material.icons.outlined.Menu
import androidx.compose.material.icons.outlined.Settings
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.DrawerValue
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.ModalNavigationDrawer
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TextField
import androidx.compose.material3.TextFieldDefaults
import androidx.compose.material3.rememberDrawerState
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
import androidx.compose.ui.platform.LocalContext
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
import com.thunder.app.data.ThunderApi
import com.thunder.app.data.ThunderPrefs
import com.thunder.app.data.titleFromMessage
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

data class Line(val who: String, val text: String)

private enum class ThunderTab { Chat, Studio }

@Composable
fun ThunderRoot() {
    val context = LocalContext.current
    val api = remember { ThunderApi() }
    val store = remember { ChatStore(context) }
    val creations = remember { CreationStore(context) }
    val prefs = remember { ThunderPrefs(context) }
    val scope = rememberCoroutineScope()
    val drawerState = rememberDrawerState(DrawerValue.Closed)
    val listState = rememberLazyListState()

    var server by remember { mutableStateOf(prefs.serverUrl) }
    var draft by remember { mutableStateOf("") }
    var showSettings by remember { mutableStateOf(false) }
    var waiting by remember { mutableStateOf(false) }
    var activeId by remember { mutableStateOf<String?>(null) }
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

    fun leaveChat() {
        persistActive()
        activeId = null
        lines.clear()
        draft = ""
        waiting = false
    }

    fun send() {
        val msg = draft.trim()
        if (msg.isEmpty() || waiting || activeId == null) return
        draft = ""
        lines.add(Line("you", msg))
        persistActive()
        waiting = true
        scope.launch {
            val reply = api.chat(server, msg)
            lines.add(Line("thunder", reply))
            waiting = false
            persistActive()
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

    LaunchedEffect(maintenanceActive) {
        while (maintenanceActive) {
            nowEpoch = System.currentTimeMillis() / 1000
            delay(1_000)
        }
    }

    BackHandler(enabled = drawerState.isOpen || tab == ThunderTab.Studio || activeId != null) {
        when {
            drawerState.isOpen -> scope.launch { drawerState.close() }
            tab == ThunderTab.Studio -> tab = ThunderTab.Chat
            activeId != null -> leaveChat()
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
                    onMenu = { scope.launch { drawerState.open() } },
                    onSettings = { showSettings = true }
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
                            .background(Color(0xFF3A2F1B))
                            .padding(horizontal = 14.dp, vertical = 10.dp)
                    ) {
                        Text(maintenanceMessage + countdown, color = Color(0xFFE3B341), fontSize = 13.sp)
                    }
                }

                if (tab == ThunderTab.Studio) {
                    CreativeStudio(
                        server = server,
                        api = api,
                        store = creations,
                        modifier = Modifier.weight(1f)
                    )
                } else if (activeId == null) {
                    ThunderHome(
                        modifier = Modifier.weight(1f),
                        hasChats = chats.isNotEmpty(),
                        onStart = { startNewChat() },
                        onOpenChats = { scope.launch { drawerState.open() } }
                    )
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
            onDismiss = { showSettings = false }
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

@Composable
private fun ThunderTopBar(
    inChat: Boolean,
    chatTitle: String?,
    serverBlank: Boolean,
    onMenu: () -> Unit,
    onSettings: () -> Unit
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
        IconButton(onClick = onSettings) {
            Icon(Icons.Outlined.Settings, contentDescription = "settings", tint = ThunderInk.Mute)
        }
    }
}

@Composable
private fun ThunderHome(
    modifier: Modifier = Modifier,
    hasChats: Boolean,
    onStart: () -> Unit,
    onOpenChats: () -> Unit
) {
    Box(modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 28.dp)
        ) {
            Image(
                painter = painterResource(R.drawable.thunder_face),
                contentDescription = null,
                contentScale = ContentScale.Fit,
                modifier = Modifier.size(118.dp)
            )
            Spacer(Modifier.height(20.dp))
            Text(
                stringResource(R.string.brand_name),
                color = ThunderInk.Ink,
                fontSize = 24.sp,
                fontWeight = FontWeight.Medium,
                letterSpacing = 1.8.sp
            )
            Spacer(Modifier.height(8.dp))
            Text(
                stringResource(R.string.empty_state_line),
                color = ThunderInk.Mute,
                fontSize = 15.sp,
                letterSpacing = 0.2.sp
            )
            Spacer(Modifier.height(36.dp))
            Row(
                Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(14.dp))
                    .background(ThunderInk.Surface.copy(alpha = 0.92f))
                    .border(1.dp, ThunderInk.Gold.copy(alpha = 0.72f), RoundedCornerShape(14.dp))
                    .clickable(onClick = onStart)
                    .padding(horizontal = 20.dp, vertical = 16.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.Center
            ) {
                Icon(
                    Icons.Outlined.Add,
                    contentDescription = null,
                    tint = ThunderInk.Gold,
                    modifier = Modifier.size(18.dp)
                )
                Spacer(Modifier.width(10.dp))
                Text(
                    stringResource(R.string.start_new_chat),
                    color = ThunderInk.Ink,
                    fontSize = 16.sp,
                    fontWeight = FontWeight.Medium,
                    letterSpacing = 0.35.sp
                )
            }
            if (hasChats) {
                Spacer(Modifier.height(16.dp))
                Text(
                    stringResource(R.string.open_chats),
                    color = ThunderInk.Gold.copy(alpha = 0.9f),
                    fontSize = 14.sp,
                    letterSpacing = 0.4.sp,
                    modifier = Modifier
                        .clip(RoundedCornerShape(8.dp))
                        .clickable(onClick = onOpenChats)
                        .padding(horizontal = 12.dp, vertical = 8.dp)
                )
            }
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
        Spacer(Modifier.size(10.dp))
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
                tint = if (ready) ThunderInk.SlateDeep else ThunderInk.Mute,
                modifier = Modifier.size(18.dp)
            )
        }
    }
}

@Composable
private fun ServerDialog(
    server: String,
    onServer: (String) -> Unit,
    onDismiss: () -> Unit
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        containerColor = ThunderInk.Surface,
        shape = RoundedCornerShape(12.dp),
        title = {
            Text(
                "Server",
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
private fun Hairline(dim: Boolean = false) {
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
                .background(if (mine) ThunderInk.YouBubble else Color.Transparent)
                .padding(horizontal = if (mine) 14.dp else 2.dp, vertical = 9.dp)
        ) {
            Text(line.text, color = ThunderInk.Ink, fontSize = 15.sp, lineHeight = 22.sp)
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
