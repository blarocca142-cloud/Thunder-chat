package com.thunder.app.ui

import android.content.Intent
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.net.Uri
import android.widget.Toast
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
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
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TextField
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import com.thunder.app.R
import com.thunder.app.data.Creation
import com.thunder.app.data.CreationStore
import com.thunder.app.data.ThunderApi
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import java.io.ByteArrayOutputStream

private val Styles = listOf("Cinematic", "Noir", "Gold hour", "Raw", "Documentary", "Ink")
private val Aspects = listOf("1:1", "16:9", "9:16", "4:3")
private val Durations = listOf(5, 8, 15)

private enum class StudioPane { Photo, Video, History }

@Composable
fun CreativeStudio(
    server: String,
    api: ThunderApi,
    store: CreationStore,
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var pane by remember { mutableStateOf(StudioPane.Photo) }
    var prompt by remember { mutableStateOf("") }
    var style by remember { mutableStateOf("Cinematic") }
    var aspect by remember { mutableStateOf("1:1") }
    var duration by remember { mutableStateOf(8) }
    var posting by remember { mutableStateOf(false) }
    var items by remember { mutableStateOf(store.list()) }
    var viewing by remember { mutableStateOf<Creation?>(null) }
    var preview by remember { mutableStateOf<Bitmap?>(null) }
    var workPreview by remember { mutableStateOf<Bitmap?>(null) }
    var waitingLong by remember { mutableStateOf(setOf<String>()) }
    var activeId by remember { mutableStateOf<String?>(null) }

    fun reload(remote: List<Creation> = emptyList()) {
        val local = store.list()
        val merged = (remote + local).distinctBy { it.id }
        items = merged
        viewing?.let { open ->
            merged.find { it.id == open.id }?.let { viewing = it }
        }
    }

    val pendingVideo = items.firstOrNull { it.isVideoPending() }
    val active = items.find { it.id == activeId }
    val work = pendingVideo ?: active
    val blocked = posting || pendingVideo != null

    LaunchedEffect(server) {
        reload(api.creations(server))
        if (activeId == null) {
            store.list().firstOrNull { it.isVideoPending() }?.let { activeId = it.id }
        }
    }

    LaunchedEffect(server) {
        if (server.isBlank()) return@LaunchedEffect
        val startedAt = mutableMapOf<String, Long>()
        while (isActive) {
            val pending = store.list().filter { it.isVideoPending() }
            val now = System.currentTimeMillis()
            pending.forEach { item ->
                val t0 = startedAt.getOrPut(item.id) { now }
                if (now - t0 >= 3 * 60 * 1000L) waitingLong = waitingLong + item.id
                val fresh = runCatching { api.creation(server, item.id) }.getOrNull()
                if (fresh != null) store.add(fresh)
            }
            val pendingIds = pending.map { it.id }.toSet()
            if (waitingLong.any { it !in pendingIds }) {
                waitingLong = waitingLong.filter { it in pendingIds }.toSet()
            }
            if (pending.isNotEmpty()) reload(api.creations(server))
            delay(5_000)
        }
    }

    LaunchedEffect(viewing?.id, viewing?.url, server) {
        val item = viewing
        preview = null
        if (item == null) return@LaunchedEffect
        if (item.url.isNotBlank()) {
            val bytes = api.fetchBytes(server, item.url)
            if (bytes != null) preview = BitmapFactory.decodeByteArray(bytes, 0, bytes.size)
        }
    }

    LaunchedEffect(work?.id, work?.url, server) {
        val item = work
        workPreview = null
        if (item == null || item.url.isBlank()) return@LaunchedEffect
        val bytes = api.fetchBytes(server, item.url)
        if (bytes != null) workPreview = BitmapFactory.decodeByteArray(bytes, 0, bytes.size)
    }

    fun generate() {
        val text = prompt.trim()
        if (text.isEmpty()) return
        if (blocked) {
            Toast.makeText(context, context.getString(R.string.studio_wait), Toast.LENGTH_SHORT).show()
            return
        }
        posting = true
        scope.launch {
            val made = if (pane == StudioPane.Video) {
                api.video(server, text, style, duration)
            } else {
                api.image(server, text, style, aspect)
            }
            store.add(made)
            activeId = made.id
            reload(if (server.isNotBlank()) api.creations(server) else emptyList())
            posting = false
            if (made.id == "err") {
                Toast.makeText(context, made.message, Toast.LENGTH_SHORT).show()
            }
        }
    }

    Column(modifier.fillMaxSize()) {
        Row(
            Modifier
                .padding(horizontal = 16.dp, vertical = 10.dp)
                .fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            StudioPane.entries.forEach { item ->
                val on = pane == item
                Text(
                    when (item) {
                        StudioPane.Photo -> stringResource(R.string.studio_photo)
                        StudioPane.Video -> stringResource(R.string.studio_video)
                        StudioPane.History -> stringResource(R.string.studio_history)
                    },
                    color = if (on) ThunderInk.Ink else ThunderInk.Mute,
                    fontSize = 13.sp,
                    letterSpacing = 0.3.sp,
                    modifier = Modifier
                        .clip(RoundedCornerShape(999.dp))
                        .border(1.dp, if (on) ThunderInk.Gold.copy(alpha = 0.55f) else ThunderInk.Hairline, RoundedCornerShape(999.dp))
                        .background(if (on) ThunderInk.Surface else ThunderInk.Drawer.copy(alpha = 0.3f))
                        .clickable { pane = item }
                        .padding(horizontal = 14.dp, vertical = 8.dp)
                )
            }
        }

        if (pane != StudioPane.History) {
            Column(
                Modifier
                    .weight(1f, fill = true)
                    .verticalScroll(rememberScrollState())
                    .padding(horizontal = 16.dp)
            ) {
                Text(
                    if (pane == StudioPane.Photo) stringResource(R.string.studio_still_title) else stringResource(R.string.studio_motion_title),
                    color = ThunderInk.Ink,
                    fontSize = 20.sp,
                    fontWeight = FontWeight.Medium,
                    letterSpacing = 0.4.sp
                )
                Spacer(Modifier.height(6.dp))
                Text(
                    if (pane == StudioPane.Photo) stringResource(R.string.studio_still_hint) else stringResource(R.string.studio_motion_hint),
                    color = ThunderInk.Mute,
                    fontSize = 13.sp,
                    lineHeight = 18.sp
                )
                Spacer(Modifier.height(14.dp))
                TextField(
                    value = prompt,
                    onValueChange = { prompt = it },
                    modifier = Modifier.fillMaxWidth(),
                    minLines = 4,
                    enabled = !blocked,
                    placeholder = {
                        Text(
                            if (pane == StudioPane.Photo) stringResource(R.string.studio_photo_hint)
                            else stringResource(R.string.studio_video_hint),
                            color = ThunderInk.Mute
                        )
                    },
                    colors = thunderStudioFieldColors()
                )
                Spacer(Modifier.height(14.dp))
                Text(stringResource(R.string.studio_style), color = ThunderInk.Mute, fontSize = 11.sp, letterSpacing = 0.7.sp)
                Spacer(Modifier.height(8.dp))
                ChipRow(Styles, style) { if (!blocked) style = it }
                if (pane == StudioPane.Photo) {
                    Spacer(Modifier.height(12.dp))
                    Text(stringResource(R.string.studio_frame), color = ThunderInk.Mute, fontSize = 11.sp, letterSpacing = 0.7.sp)
                    Spacer(Modifier.height(8.dp))
                    ChipRow(Aspects, aspect) { if (!blocked) aspect = it }
                } else {
                    Spacer(Modifier.height(12.dp))
                    Text(stringResource(R.string.studio_length), color = ThunderInk.Mute, fontSize = 11.sp, letterSpacing = 0.7.sp)
                    Spacer(Modifier.height(8.dp))
                    ChipRow(Durations.map { "${it}s" }, "${duration}s") { if (!blocked) duration = it.trimEnd('s').toInt() }
                }
                Spacer(Modifier.height(18.dp))
                val canStart = prompt.isNotBlank() && !blocked
                Box(
                    Modifier
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(12.dp))
                        .background(if (canStart) ThunderInk.Gold else ThunderInk.Surface)
                        .clickable {
                            when {
                                blocked -> Toast.makeText(context, context.getString(R.string.studio_wait), Toast.LENGTH_SHORT).show()
                                prompt.isNotBlank() -> generate()
                            }
                        }
                        .padding(vertical = 14.dp),
                    contentAlignment = Alignment.Center
                ) {
                    Text(
                        when {
                            blocked -> stringResource(R.string.studio_wait)
                            pane == StudioPane.Photo -> stringResource(R.string.studio_make_photo)
                            else -> stringResource(R.string.studio_make_video)
                        },
                        color = if (canStart) ThunderInk.OnGold else ThunderInk.Mute,
                        fontWeight = FontWeight.Medium,
                        letterSpacing = 0.3.sp
                    )
                }

                if (posting || work != null) {
                    Spacer(Modifier.height(18.dp))
                    StudioWorkCard(
                        item = work,
                        posting = posting,
                        waitingLong = work?.id in waitingLong,
                        poster = workPreview,
                        ratio = if (pane == StudioPane.Video || work?.kind == "video") 16f / 9f else when (work?.aspect ?: aspect) {
                            "16:9" -> 16f / 9f
                            "9:16" -> 9f / 16f
                            "4:3" -> 4f / 3f
                            else -> 1f
                        },
                        onOpen = { work?.let { viewing = it } }
                    )
                }

                Spacer(Modifier.height(18.dp))
                Text(stringResource(R.string.studio_recent), color = ThunderInk.Mute, fontSize = 11.sp, letterSpacing = 0.7.sp)
                Spacer(Modifier.height(8.dp))
                CreationGrid(
                    items = items.filter {
                        if (pane == StudioPane.Video) it.kind == "video" else it.kind == "image"
                    }.take(8),
                    server = server,
                    api = api,
                    onOpen = { viewing = it },
                    compact = true
                )
                Spacer(Modifier.height(20.dp))
            }
        } else {
            CreationGrid(
                items = items,
                server = server,
                api = api,
                onOpen = { viewing = it },
                compact = false,
                modifier = Modifier.weight(1f)
            )
        }
    }

    viewing?.let { item ->
        val phase = item.videoPhase()
        val playHref = if (phase == "done") api.mediaHref(server, item.videoUrl) else null
        val inFlight = item.isVideoPending() || (posting && item.id == activeId)
        val statusText = when {
            inFlight && item.id in waitingLong -> stringResource(R.string.studio_video_waiting)
            inFlight -> item.message.ifBlank { stringResource(R.string.studio_processing) }
            phase == "done" -> item.message.ifBlank { stringResource(R.string.studio_video_ready) }
            else -> item.message
        }
        Dialog(onDismissRequest = { viewing = null }) {
            Column(
                Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(16.dp))
                    .background(ThunderInk.Surface)
                    .border(1.dp, ThunderInk.Hairline, RoundedCornerShape(16.dp))
                    .padding(14.dp)
            ) {
                Box(
                    Modifier
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(10.dp))
                        .background(ThunderInk.SlateDeep)
                        .aspectRatio(if (item.kind == "video") 16f / 9f else 1f),
                    contentAlignment = Alignment.Center
                ) {
                    preview?.let { bmp ->
                        Image(
                            bitmap = bmp.asImageBitmap(),
                            contentDescription = item.prompt,
                            contentScale = ContentScale.Fit,
                            modifier = Modifier
                                .fillMaxSize()
                                .alpha(if (inFlight) 0.45f else 1f)
                        )
                    }
                    if (inFlight) {
                        CircularProgressIndicator(
                            modifier = Modifier.size(36.dp),
                            color = ThunderInk.Gold,
                            strokeWidth = 2.dp
                        )
                    }
                }
                Spacer(Modifier.height(12.dp))
                Text(item.prompt, color = ThunderInk.Ink, fontSize = 14.sp)
                Spacer(Modifier.height(6.dp))
                Text(statusText, color = ThunderInk.Mute, fontSize = 12.sp, lineHeight = 17.sp)
                Spacer(Modifier.height(12.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    if (playHref != null) {
                        TextButton(
                            onClick = {
                                val intent = Intent(Intent.ACTION_VIEW).apply {
                                    setDataAndType(Uri.parse(playHref), "video/mp4")
                                    addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                                }
                                runCatching {
                                    context.startActivity(Intent.createChooser(intent, context.getString(R.string.studio_play)))
                                }
                            }
                        ) { Text(stringResource(R.string.studio_play), color = ThunderInk.Gold) }
                    }
                    TextButton(
                        onClick = {
                            scope.launch {
                                val bytes = item.url.takeIf { it.isNotBlank() }?.let { api.fetchBytes(server, it) }
                                    ?: preview?.let { bmp ->
                                        ByteArrayOutputStream().use { out ->
                                            bmp.compress(Bitmap.CompressFormat.PNG, 100, out)
                                            out.toByteArray()
                                        }
                                    }
                                if (bytes != null && store.savePng(bytes, "${item.id}.png")) {
                                    Toast.makeText(context, context.getString(R.string.studio_saved), Toast.LENGTH_SHORT).show()
                                } else {
                                    Toast.makeText(context, context.getString(R.string.studio_save_fail), Toast.LENGTH_SHORT).show()
                                }
                            }
                        }
                    ) { Text(stringResource(R.string.studio_save), color = ThunderInk.Gold) }
                    TextButton(
                        onClick = {
                            scope.launch {
                                val bytes = item.url.takeIf { it.isNotBlank() }?.let { api.fetchBytes(server, it) }
                                    ?: preview?.let { bmp ->
                                        ByteArrayOutputStream().use { out ->
                                            bmp.compress(Bitmap.CompressFormat.PNG, 100, out)
                                            out.toByteArray()
                                        }
                                    }
                                if (bytes != null) store.sharePng(bytes, "${item.id}.png")
                            }
                        }
                    ) { Text(stringResource(R.string.studio_share), color = ThunderInk.Ink) }
                    Spacer(Modifier.weight(1f))
                    TextButton(onClick = { viewing = null }) {
                        Text(stringResource(R.string.studio_close), color = ThunderInk.Mute)
                    }
                }
            }
        }
    }
}

@Composable
private fun StudioWorkCard(
    item: Creation?,
    posting: Boolean,
    waitingLong: Boolean,
    poster: Bitmap?,
    ratio: Float,
    onOpen: () -> Unit
) {
    val inFlight = posting || item?.isVideoPending() == true
    val phase = item?.videoPhase().orEmpty()
    val status = when {
        posting && item == null -> stringResource(R.string.studio_starting)
        inFlight && waitingLong -> stringResource(R.string.studio_video_waiting)
        inFlight && item?.kind == "image" -> stringResource(R.string.studio_rendering_still)
        inFlight -> stringResource(R.string.studio_rendering_motion)
        phase == "error" -> item?.message.orEmpty().ifBlank { stringResource(R.string.studio_save_fail) }
        phase == "done" || (item != null && !inFlight) -> stringResource(R.string.studio_ready)
        else -> item?.message.orEmpty()
    }
    Column(
        Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(14.dp))
            .background(ThunderInk.Surface)
            .border(1.dp, ThunderInk.Gold.copy(alpha = 0.35f), RoundedCornerShape(14.dp))
            .clickable(enabled = item != null && !inFlight) { onOpen() }
            .padding(12.dp)
    ) {
        Text(
            stringResource(R.string.studio_stage),
            color = ThunderInk.Mute,
            fontSize = 11.sp,
            letterSpacing = 0.7.sp
        )
        Spacer(Modifier.height(10.dp))
        Box(
            Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(10.dp))
                .background(ThunderInk.SlateDeep)
                .aspectRatio(ratio.coerceIn(0.5f, 2.2f)),
            contentAlignment = Alignment.Center
        ) {
            val showPoster = poster != null && (item?.isVideoPending() == true || !inFlight)
            if (showPoster) {
                Image(
                    bitmap = poster!!.asImageBitmap(),
                    contentDescription = item?.prompt,
                    contentScale = ContentScale.Crop,
                    modifier = Modifier
                        .fillMaxSize()
                        .alpha(if (inFlight) 0.4f else 1f)
                )
            }
            if (inFlight) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(32.dp),
                        color = ThunderInk.Gold,
                        strokeWidth = 2.dp
                    )
                    Spacer(Modifier.height(10.dp))
                    Text(
                        status,
                        color = ThunderInk.Gold,
                        fontSize = 12.sp,
                        textAlign = TextAlign.Center,
                        modifier = Modifier.padding(horizontal = 16.dp)
                    )
                }
            }
        }
        Spacer(Modifier.height(10.dp))
        Text(
            item?.prompt?.ifBlank { status } ?: status,
            color = ThunderInk.Ink,
            fontSize = 13.sp,
            maxLines = 2,
            overflow = TextOverflow.Ellipsis
        )
        if (!inFlight && item != null) {
            Spacer(Modifier.height(4.dp))
            Text(status, color = ThunderInk.Mute, fontSize = 12.sp)
        }
    }
}

@Composable
private fun ChipRow(values: List<String>, selected: String, onPick: (String) -> Unit) {
    Row(
        Modifier.horizontalScroll(rememberScrollState()),
        horizontalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        values.forEach { value ->
            val on = value == selected
            Text(
                value,
                color = if (on) ThunderInk.Ink else ThunderInk.Mute,
                fontSize = 13.sp,
                modifier = Modifier
                    .clip(RoundedCornerShape(999.dp))
                    .border(1.dp, if (on) ThunderInk.Gold else ThunderInk.Hairline, RoundedCornerShape(999.dp))
                    .clickable { onPick(value) }
                    .padding(horizontal = 12.dp, vertical = 6.dp)
            )
        }
    }
}

@Composable
private fun CreationGrid(
    items: List<Creation>,
    server: String,
    api: ThunderApi,
    onOpen: (Creation) -> Unit,
    compact: Boolean,
    modifier: Modifier = Modifier
) {
    if (items.isEmpty()) {
        Text(
            stringResource(R.string.studio_empty),
            color = ThunderInk.Mute,
            fontSize = 13.sp,
            modifier = modifier.padding(vertical = 20.dp)
        )
        return
    }
    LazyVerticalGrid(
        columns = GridCells.Fixed(2),
        modifier = modifier.fillMaxWidth().then(if (compact) Modifier.height(280.dp) else Modifier),
        horizontalArrangement = Arrangement.spacedBy(10.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp),
        contentPadding = PaddingValues(bottom = 16.dp),
        userScrollEnabled = !compact
    ) {
        items(items, key = { it.id }) { item ->
            CreationThumb(item, server, api, onOpen)
        }
    }
}

@Composable
private fun CreationThumb(
    item: Creation,
    server: String,
    api: ThunderApi,
    onOpen: (Creation) -> Unit
) {
    var bmp by remember(item.id, item.url) { mutableStateOf<Bitmap?>(null) }
    LaunchedEffect(item.id, item.url, server) {
        if (item.url.isNotBlank()) {
            val bytes = api.fetchBytes(server, item.url)
            if (bytes != null) bmp = BitmapFactory.decodeByteArray(bytes, 0, bytes.size)
        }
    }
    Column(
        Modifier
            .clip(RoundedCornerShape(12.dp))
            .background(ThunderInk.Surface)
            .border(1.dp, ThunderInk.Hairline, RoundedCornerShape(12.dp))
            .clickable { onOpen(item) }
    ) {
        Box(
            Modifier
                .fillMaxWidth()
                .aspectRatio(1f)
                .background(ThunderInk.SlateDeep),
            contentAlignment = Alignment.Center
        ) {
            bmp?.let {
                Image(
                    bitmap = it.asImageBitmap(),
                    contentDescription = item.prompt,
                    contentScale = ContentScale.Crop,
                    modifier = Modifier
                        .fillMaxSize()
                        .alpha(if (item.isVideoPending()) 0.45f else 1f)
                )
            }
            if (item.isVideoPending()) {
                CircularProgressIndicator(
                    modifier = Modifier.size(22.dp),
                    color = ThunderInk.Gold,
                    strokeWidth = 2.dp
                )
            }
        }
        Text(
            item.prompt,
            color = ThunderInk.Ink,
            fontSize = 12.sp,
            maxLines = 2,
            overflow = TextOverflow.Ellipsis,
            modifier = Modifier.padding(horizontal = 10.dp, vertical = 8.dp)
        )
    }
}

@Composable
private fun thunderStudioFieldColors() = androidx.compose.material3.TextFieldDefaults.colors(
    focusedTextColor = ThunderInk.Ink,
    unfocusedTextColor = ThunderInk.Ink,
    disabledTextColor = ThunderInk.Mute,
    focusedContainerColor = ThunderInk.SlateDeep,
    unfocusedContainerColor = ThunderInk.SlateDeep,
    disabledContainerColor = ThunderInk.SlateDeep,
    cursorColor = ThunderInk.Gold,
    focusedIndicatorColor = ThunderInk.Gold.copy(alpha = 0.7f),
    unfocusedIndicatorColor = ThunderInk.Hairline,
    disabledIndicatorColor = ThunderInk.Hairline
)
