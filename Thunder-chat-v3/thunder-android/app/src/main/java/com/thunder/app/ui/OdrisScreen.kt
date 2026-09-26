package com.thunder.app.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.Send
import androidx.compose.material.icons.outlined.Check
import androidx.compose.material.icons.outlined.Refresh
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TextField
import androidx.compose.material3.TextFieldDefaults
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
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.thunder.app.data.DigestWorker
import com.thunder.app.data.FleetAlert
import com.thunder.app.data.ThunderApi
import kotlinx.coroutines.launch
import java.time.OffsetDateTime
import java.time.ZoneId
import java.time.format.DateTimeFormatter

/**
 * Odris, as its own place in the app rather than a corner of Thunder's.
 *
 * Blayne's objection was the right one: Odris mixed into Thunder is a bad idea.
 * They are genuinely separate assistants - separate machine, separate prompt,
 * live machine readings instead of chat history - and blurring them in the UI
 * would teach you to distrust both, because you would never be sure which one
 * answered.
 *
 * Three panes, all Odris's own work:
 *
 * **Dashboard** - the real ops dashboard from Odris, embedded rather than
 * reimplemented. See OdrisDashboard.kt.
 *
 * **Alerts** - the history a notification can land on. This is the screen whose
 * absence caused the original bug: the phone buzzed about serverus, and nothing
 * in the entire app had ever displayed a digest, so it looked like Thunder was
 * inventing things. It was not - the warning was real and had nowhere to go.
 *
 * **Chat** - Odris answering in its own voice, read-only from here.
 */
private enum class FleetPane { Dashboard, Alerts, Chat }

@Composable
fun OdrisScreen(
    server: String,
    api: ThunderApi,
    odrisUrl: String,
    odrisPassword: String,
    modifier: Modifier = Modifier,
    /** True when a notification brought us here, in which case the finding that
     *  buzzed matters more than the dashboard. */
    startOnAlerts: Boolean = false,
    onOpenSettings: () -> Unit = {},
    /** Fired when an alert is acknowledged, so the tab badge updates now rather
     *  than whenever its five-minute poll next comes round. */
    onAlertsChanged: () -> Unit = {}
) {
    var pane by remember {
        mutableStateOf(if (startOnAlerts) FleetPane.Alerts else FleetPane.Dashboard)
    }

    Column(modifier) {
        Row(
            Modifier
                .fillMaxWidth()
                .padding(horizontal = 14.dp, vertical = 10.dp),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            PanePill("Dashboard", pane == FleetPane.Dashboard) { pane = FleetPane.Dashboard }
            PanePill("Alerts", pane == FleetPane.Alerts) { pane = FleetPane.Alerts }
            PanePill("Chat", pane == FleetPane.Chat) { pane = FleetPane.Chat }
        }
        Hairline(dim = true)
        when (pane) {
            FleetPane.Dashboard -> OdrisDashboard(
                url = odrisUrl,
                password = odrisPassword,
                modifier = Modifier.weight(1f),
                onOpenSettings = onOpenSettings
            )
            FleetPane.Alerts -> AlertsPane(
                server, api, Modifier.weight(1f), onAlertsChanged)
            FleetPane.Chat -> OdrisPane(server, api, Modifier.weight(1f))
        }
    }
}

@Composable
private fun PanePill(label: String, selected: Boolean, onClick: () -> Unit) {
    Box(
        Modifier
            .clip(RoundedCornerShape(50))
            .background(if (selected) ThunderInk.Gold else ThunderInk.Surface)
            .clickable(onClick = onClick)
            .padding(horizontal = 16.dp, vertical = 8.dp)
    ) {
        Text(
            label,
            color = if (selected) ThunderInk.OnGold else ThunderInk.Mute,
            fontSize = 13.sp,
            fontWeight = if (selected) FontWeight.SemiBold else FontWeight.Normal
        )
    }
}

@Composable
private fun AlertsPane(
    server: String,
    api: ThunderApi,
    modifier: Modifier = Modifier,
    onAlertsChanged: () -> Unit = {}
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var alerts by remember { mutableStateOf<List<FleetAlert>>(emptyList()) }
    var loading by remember { mutableStateOf(true) }
    var showResolved by remember { mutableStateOf(false) }
    var expanded by remember { mutableStateOf<String?>(null) }
    var loadedOnce by remember { mutableStateOf(false) }

    suspend fun load() {
        loading = true
        alerts = api.alerts(server, includeResolved = true)
        loading = false
        loadedOnce = true
    }

    LaunchedEffect(server) {
        // Looking at the list is reading it, so take the notification out of the
        // shade. Leaving it there while the app shows the same finding marked as
        // read is the phone contradicting itself.
        DigestWorker.clear(context)
        load()
    }

    val active = alerts.filter { it.active }
    val resolved = alerts.filter { !it.active }
    val shown = if (showResolved) active + resolved else active

    Column(modifier) {
        Row(
            Modifier
                .fillMaxWidth()
                .padding(start = 16.dp, end = 6.dp, top = 10.dp, bottom = 4.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                when {
                    loading && !loadedOnce -> "Checking the fleet…"
                    active.isEmpty() -> "Nothing needs you."
                    active.size == 1 -> "1 thing to look at"
                    else -> "${active.size} things to look at"
                },
                color = ThunderInk.Ink,
                fontSize = 15.sp,
                fontWeight = FontWeight.SemiBold,
                modifier = Modifier.weight(1f)
            )
            if (loading && loadedOnce) {
                CircularProgressIndicator(
                    Modifier.size(16.dp), color = ThunderInk.Gold, strokeWidth = 2.dp
                )
                Spacer(Modifier.width(8.dp))
            }
            IconButton(onClick = { scope.launch { load() } }) {
                Icon(Icons.Outlined.Refresh, contentDescription = "Refresh",
                     tint = ThunderInk.Mute)
            }
        }

        if (!loading && active.isEmpty() && resolved.isEmpty() && loadedOnce) {
            Box(Modifier.fillMaxWidth().padding(24.dp)) {
                Text(
                    if (server.isBlank())
                        "Point Settings at Main and this fills in."
                    else
                        "No findings recorded yet. This fills in the first time " +
                        "Thunder checks the fleet, or right now if you hit refresh.",
                    color = ThunderInk.Mute, fontSize = 13.sp
                )
            }
        }

        LazyColumn(
            modifier = Modifier.weight(1f).fillMaxWidth(),
            contentPadding = PaddingValues(horizontal = 14.dp, vertical = 8.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            items(shown, key = { it.id }) { alert ->
                AlertCard(
                    alert = alert,
                    expanded = expanded == alert.id,
                    onToggle = { expanded = if (expanded == alert.id) null else alert.id },
                    onAck = {
                        scope.launch {
                            if (api.ackAlert(server, alert.id)) {
                                load()
                                // Both of these, immediately. The badge otherwise
                                // sat on its old number for up to five minutes,
                                // which reads as the app ignoring the tap.
                                DigestWorker.clear(context)
                                onAlertsChanged()
                            }
                        }
                    }
                )
            }
            if (resolved.isNotEmpty()) {
                item {
                    TextButton(onClick = { showResolved = !showResolved }) {
                        Text(
                            if (showResolved) "Hide cleared (${resolved.size})"
                            else "Show cleared (${resolved.size})",
                            color = ThunderInk.Gold, fontSize = 13.sp
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun AlertCard(
    alert: FleetAlert,
    expanded: Boolean,
    onToggle: () -> Unit,
    onAck: () -> Unit
) {
    val accent = severityColor(alert)
    Column(
        Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(14.dp))
            .background(ThunderInk.Surface)
            .clickable(onClick = onToggle)
            .padding(14.dp)
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Box(Modifier.size(9.dp).clip(CircleShape).background(accent))
            Spacer(Modifier.width(10.dp))
            Text(
                alert.headline,
                color = if (alert.active) ThunderInk.Ink else ThunderInk.Mute,
                fontSize = 14.sp,
                fontWeight = if (alert.active && !alert.acknowledged)
                    FontWeight.SemiBold else FontWeight.Normal,
                modifier = Modifier.weight(1f)
            )
        }
        Spacer(Modifier.height(6.dp))
        // The line that was missing entirely: when it started, and whether it is
        // still true. That is the whole answer to "what was that buzz?".
        Text(
            buildString {
                append("since ").append(localTime(alert.firstSeen))
                append(if (alert.active) " · still happening" else " · cleared " + localTime(alert.resolvedAt))
                if (alert.acknowledged) append(" · read")
            },
            color = ThunderInk.Mute, fontSize = 11.sp
        )

        if (expanded) {
            Spacer(Modifier.height(10.dp))
            Text(alert.detail, color = ThunderInk.Ink, fontSize = 13.sp)
            if (alert.action.isNotBlank()) {
                Spacer(Modifier.height(8.dp))
                Text("What to do", color = ThunderInk.Gold, fontSize = 11.sp,
                     fontWeight = FontWeight.SemiBold)
                Text(alert.action, color = ThunderInk.Ink, fontSize = 13.sp)
            }
            Spacer(Modifier.height(4.dp))
            Text("last seen ${localTime(alert.lastSeen)} · ${alert.kind}",
                 color = ThunderInk.Mute, fontSize = 11.sp)
            if (alert.active && !alert.acknowledged) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    TextButton(onClick = onAck) {
                        Icon(Icons.Outlined.Check, contentDescription = null,
                             tint = ThunderInk.Gold, modifier = Modifier.size(16.dp))
                        Spacer(Modifier.width(6.dp))
                        Text("Mark as read", color = ThunderInk.Gold, fontSize = 13.sp)
                    }
                }
            }
        }
    }
}

@Composable
private fun OdrisPane(server: String, api: ThunderApi, modifier: Modifier = Modifier) {
    val scope = rememberCoroutineScope()
    val listState = rememberLazyListState()
    val turns = remember { mutableStateOf<List<Pair<String, String>>>(emptyList()) }
    var draft by remember { mutableStateOf("") }
    var waiting by remember { mutableStateOf(false) }

    LaunchedEffect(server) {
        turns.value = api.odrisHistory(server).map { it.role to it.content }
    }

    fun send() {
        val text = draft.trim()
        if (text.isEmpty() || waiting) return
        draft = ""
        turns.value = turns.value + ("user" to text)
        waiting = true
        scope.launch {
            val reply = api.odrisChat(server, text)
            turns.value = turns.value + ("assistant" to reply)
            waiting = false
        }
    }

    LaunchedEffect(turns.value.size) {
        if (turns.value.isNotEmpty()) listState.animateScrollToItem(turns.value.size - 1)
    }

    Column(modifier) {
        if (turns.value.isEmpty()) {
            Column(Modifier.fillMaxWidth().padding(18.dp)) {
                Text("Odris watches the machines.", color = ThunderInk.Ink,
                     fontSize = 15.sp, fontWeight = FontWeight.SemiBold)
                Spacer(Modifier.height(6.dp))
                Text(
                    "A different assistant from Thunder - it sees node health, " +
                    "hardware findings, jobs and errors instead of your chat " +
                    "history. Ask it what a notification meant, or whether " +
                    "something actually needs you today.",
                    color = ThunderInk.Mute, fontSize = 13.sp
                )
                Spacer(Modifier.height(10.dp))
                Text(
                    "Read-only from here. Approving, applying and maintenance " +
                    "stay on the Odris dashboard on port 9005.",
                    color = ThunderInk.Mute, fontSize = 11.sp
                )
            }
        }
        LazyColumn(
            state = listState,
            modifier = Modifier.weight(1f).fillMaxWidth(),
            contentPadding = PaddingValues(horizontal = 16.dp, vertical = 12.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            items(turns.value) { (role, text) ->
                val mine = role == "user"
                Column(Modifier.fillMaxWidth()) {
                    Text(
                        if (mine) "You" else "Odris",
                        color = if (mine) ThunderInk.Mute else ThunderInk.Gold,
                        fontSize = 11.sp, fontWeight = FontWeight.SemiBold
                    )
                    Spacer(Modifier.height(3.dp))
                    Box(
                        Modifier
                            .clip(RoundedCornerShape(12.dp))
                            .background(if (mine) ThunderInk.YouBubble else ThunderInk.Surface)
                            .padding(12.dp)
                    ) {
                        Text(text, color = ThunderInk.Ink, fontSize = 14.sp)
                    }
                }
            }
            if (waiting) {
                item {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        CircularProgressIndicator(
                            Modifier.size(14.dp), color = ThunderInk.Gold, strokeWidth = 2.dp
                        )
                        Spacer(Modifier.width(8.dp))
                        Text("Odris is checking the fleet…",
                             color = ThunderInk.Mute, fontSize = 12.sp)
                    }
                }
            }
        }
        Hairline(dim = true)
        Row(
            Modifier
                .fillMaxWidth()
                .padding(horizontal = 10.dp, vertical = 8.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            TextField(
                value = draft,
                onValueChange = { draft = it },
                modifier = Modifier.weight(1f),
                placeholder = { Text("Ask Odris about the fleet…",
                                     color = ThunderInk.Mute, fontSize = 14.sp) },
                colors = TextFieldDefaults.colors(
                    focusedContainerColor = ThunderInk.Surface,
                    unfocusedContainerColor = ThunderInk.Surface,
                    focusedTextColor = ThunderInk.Ink,
                    unfocusedTextColor = ThunderInk.Ink,
                    cursorColor = ThunderInk.Gold,
                    focusedIndicatorColor = Color.Transparent,
                    unfocusedIndicatorColor = Color.Transparent
                ),
                shape = RoundedCornerShape(22.dp),
                maxLines = 4
            )
            IconButton(onClick = { send() }, enabled = draft.isNotBlank() && !waiting) {
                Icon(Icons.AutoMirrored.Outlined.Send, contentDescription = "Send",
                     tint = if (draft.isNotBlank() && !waiting) ThunderInk.Gold else ThunderInk.Mute)
            }
        }
    }
}

@Composable
private fun severityColor(alert: FleetAlert): Color {
    if (!alert.active) return ThunderInk.Mute
    return when (alert.severity) {
        "critical" -> Color(0xFFD9534F)
        "warning" -> ThunderInk.Gold
        else -> ThunderInk.Live
    }
}

/**
 * Stored UTC, shown local - deliberately, and in that order.
 *
 * A canary alert logged at 07:12 UTC was 03:12 in the kitchen, and showing the
 * raw value once turned "me, last night" into "a stranger, this morning". The
 * server stores UTC because that is the only sane thing to store; every surface
 * a person reads converts first.
 */
private fun localTime(iso: String?): String {
    if (iso.isNullOrBlank()) return "unknown"
    return try {
        OffsetDateTime.parse(iso)
            .atZoneSameInstant(ZoneId.systemDefault())
            .format(DateTimeFormatter.ofPattern("EEE d MMM, h:mm a"))
    } catch (_: Exception) {
        iso
    }
}
