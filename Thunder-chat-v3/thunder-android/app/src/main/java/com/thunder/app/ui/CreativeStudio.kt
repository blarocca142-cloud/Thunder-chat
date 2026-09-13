package com.thunder.app.ui

import android.graphics.Bitmap
import android.graphics.BitmapFactory
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
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
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
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.thunder.app.R
import com.thunder.app.data.Creation
import com.thunder.app.data.CreationStore
import com.thunder.app.data.ThunderApi
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
    var busy by remember { mutableStateOf(false) }
    var items by remember { mutableStateOf(store.list()) }
    var viewing by remember { mutableStateOf<Creation?>(null) }
    var preview by remember { mutableStateOf<Bitmap?>(null) }

    fun reload(remote: List<Creation> = emptyList()) {
        val local = store.list()
        val merged = (remote + local).distinctBy { it.id }
        items = merged
    }

    LaunchedEffect(server) {
        reload(api.creations(server))
    }

    LaunchedEffect(viewing?.id, viewing?.url, server) {
        val item = viewing
        preview = null
        if (item == null) return@LaunchedEffect
        if (item.url.isNotBlank()) {
            val bytes = api.fetchBytes(server, item.url)
            if (bytes != null) preview = BitmapFactory.decodeByteArray(bytes, 0, bytes.size)
        }
        if (preview == null) {
            preview = CreationStore.stubBitmap(item.prompt, item.style, item.aspect)
        }
    }

    fun generate() {
        val text = prompt.trim()
        if (text.isEmpty() || busy) return
        busy = true
        scope.launch {
            val made = if (pane == StudioPane.Video) {
                api.video(server, text, style, duration)
            } else {
                api.image(server, text, style, aspect)
            }
            store.add(made)
            reload(if (server.isNotBlank()) api.creations(server) else emptyList())
            viewing = made
            busy = false
            Toast.makeText(context, made.message.ifBlank { context.getString(R.string.studio_done) }, Toast.LENGTH_SHORT).show()
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
                ChipRow(Styles, style) { style = it }
                if (pane == StudioPane.Photo) {
                    Spacer(Modifier.height(12.dp))
                    Text(stringResource(R.string.studio_frame), color = ThunderInk.Mute, fontSize = 11.sp, letterSpacing = 0.7.sp)
                    Spacer(Modifier.height(8.dp))
                    ChipRow(Aspects, aspect) { aspect = it }
                } else {
                    Spacer(Modifier.height(12.dp))
                    Text(stringResource(R.string.studio_length), color = ThunderInk.Mute, fontSize = 11.sp, letterSpacing = 0.7.sp)
                    Spacer(Modifier.height(8.dp))
                    ChipRow(Durations.map { "${it}s" }, "${duration}s") { duration = it.trimEnd('s').toInt() }
                }
                Spacer(Modifier.height(18.dp))
                Box(
                    Modifier
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(12.dp))
                        .background(if (prompt.isNotBlank() && !busy) ThunderInk.Gold else ThunderInk.Surface)
                        .clickable(enabled = prompt.isNotBlank() && !busy) { generate() }
                        .padding(vertical = 14.dp),
                    contentAlignment = Alignment.Center
                ) {
                    Text(
                        if (busy) stringResource(R.string.studio_working)
                        else if (pane == StudioPane.Photo) stringResource(R.string.studio_make_photo)
                        else stringResource(R.string.studio_make_video),
                        color = if (prompt.isNotBlank() && !busy) ThunderInk.SlateDeep else ThunderInk.Mute,
                        fontWeight = FontWeight.Medium,
                        letterSpacing = 0.3.sp
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
        AlertDialog(
            onDismissRequest = { viewing = null },
            containerColor = ThunderInk.Surface,
            shape = RoundedCornerShape(14.dp),
            title = {
                Text(
                    item.kind.replaceFirstChar { it.uppercase() },
                    color = ThunderInk.Ink,
                    fontWeight = FontWeight.Medium
                )
            },
            text = {
                Column {
                    preview?.let { bmp ->
                        Image(
                            bitmap = bmp.asImageBitmap(),
                            contentDescription = item.prompt,
                            contentScale = ContentScale.Fit,
                            modifier = Modifier
                                .fillMaxWidth()
                                .clip(RoundedCornerShape(10.dp))
                                .background(ThunderInk.SlateDeep)
                        )
                        Spacer(Modifier.height(10.dp))
                    }
                    Text(item.prompt, color = ThunderInk.Ink, fontSize = 14.sp)
                    Spacer(Modifier.height(6.dp))
                    Text(item.message, color = ThunderInk.Mute, fontSize = 12.sp, lineHeight = 17.sp)
                }
            },
            confirmButton = {
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
            },
            dismissButton = {
                Row {
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
                    TextButton(onClick = { viewing = null }) {
                        Text(stringResource(R.string.studio_close), color = ThunderInk.Mute)
                    }
                }
            }
        )
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
        columns = GridCells.Fixed(if (compact) 2 else 2),
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
        if (bmp == null) bmp = CreationStore.stubBitmap(item.prompt, item.style, item.aspect)
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
                .background(ThunderInk.SlateDeep)
        ) {
            bmp?.let {
                Image(
                    bitmap = it.asImageBitmap(),
                    contentDescription = item.prompt,
                    contentScale = ContentScale.Crop,
                    modifier = Modifier.fillMaxSize()
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
    focusedContainerColor = ThunderInk.SlateDeep,
    unfocusedContainerColor = ThunderInk.SlateDeep,
    cursorColor = ThunderInk.Gold,
    focusedIndicatorColor = ThunderInk.Gold.copy(alpha = 0.7f),
    unfocusedIndicatorColor = ThunderInk.Hairline
)
