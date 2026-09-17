package com.thunder.app.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.ArrowBack
import androidx.compose.material.icons.outlined.ExpandLess
import androidx.compose.material.icons.outlined.ExpandMore
import androidx.compose.material.icons.outlined.Refresh
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
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.thunder.app.data.FleetHealth
import com.thunder.app.data.HealthComponent
import com.thunder.app.data.NodeHealth
import com.thunder.app.data.ThunderApi
import kotlinx.coroutines.launch

/**
 * Hardware health for the whole fleet, collected by Odris.
 *
 * Three levels, because that is how you actually look for a fault: the fleet,
 * then the machine, then the part. Tap a part to see what was measured and, if
 * something is wrong, what to do about it.
 *
 * A component with no score is not a failure and not a pass - it is something
 * this hardware cannot report on, and it says so. A power supply with no
 * voltage sensors is invisible to software, and pretending otherwise would be
 * the one thing that makes a health page worse than no health page.
 */
@Composable
fun FleetHealthPanel(
    server: String,
    api: ThunderApi,
    onBack: () -> Unit = {},
    modifier: Modifier = Modifier
) {
    val scope = rememberCoroutineScope()
    var health by remember { mutableStateOf<FleetHealth?>(null) }
    var loading by remember { mutableStateOf(true) }
    var refreshing by remember { mutableStateOf(false) }
    var openNode by remember { mutableStateOf<String?>(null) }
    var openComponent by remember { mutableStateOf<String?>(null) }

    LaunchedEffect(server) {
        loading = true
        health = api.fleetHealth(server)
        loading = false
    }

    Column(modifier.fillMaxSize()) {
        Row(
            Modifier.fillMaxWidth().padding(horizontal = 18.dp, vertical = 14.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Icon(
                Icons.Outlined.ArrowBack, contentDescription = "Back",
                tint = ThunderInk.Ink,
                modifier = Modifier
                    .clip(RoundedCornerShape(6.dp))
                    .clickable(onClick = onBack)
                    .padding(4.dp)
            )
            Spacer(Modifier.width(12.dp))
            Column(Modifier.weight(1f)) {
                Text("Fleet health", color = ThunderInk.Ink, fontSize = 18.sp,
                    fontWeight = FontWeight.SemiBold)
                val h = health
                Text(
                    when {
                        loading -> "Reading sensors..."
                        h == null -> "Odris is not answering"
                        h.error != null -> "Odris is not answering"
                        else -> "${h.nodesReporting} of ${h.nodesExpected} machines reporting"
                    },
                    color = ThunderInk.Mute, fontSize = 13.sp
                )
            }
            if (refreshing) {
                CircularProgressIndicator(
                    color = ThunderInk.Gold, strokeWidth = 2.dp,
                    modifier = Modifier.width(18.dp).height(18.dp)
                )
            } else {
                Icon(
                    Icons.Outlined.Refresh, contentDescription = "Re-check now",
                    tint = ThunderInk.Mute,
                    modifier = Modifier
                        .clip(RoundedCornerShape(6.dp))
                        .clickable {
                            scope.launch {
                                refreshing = true
                                // A real re-poll: Odris walks every node over
                                // SSH, so this takes a while by nature.
                                api.fleetHealth(server, refresh = true)?.let { health = it }
                                refreshing = false
                            }
                        }
                        .padding(4.dp)
                )
            }
        }
        Hairline(dim = true)

        val h = health
        when {
            loading -> Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                CircularProgressIndicator(color = ThunderInk.Gold)
            }
            h == null || h.nodes.isEmpty() -> Box(
                Modifier.fillMaxSize(), contentAlignment = Alignment.Center
            ) {
                Text(
                    if (server.isBlank()) "Connect to Main to see fleet health."
                    else "Odris is not answering on port 9007.",
                    color = ThunderInk.Mute, fontSize = 14.sp,
                    modifier = Modifier.padding(32.dp)
                )
            }
            else -> LazyColumn(
                Modifier.fillMaxSize(),
                contentPadding = PaddingValues(bottom = 24.dp)
            ) {
                items(h.nodes) { node ->
                    NodeRow(
                        node = node,
                        expanded = openNode == node.node,
                        openComponent = openComponent,
                        onToggle = {
                            openNode = if (openNode == node.node) null else node.node
                            openComponent = null
                        },
                        onComponent = { key ->
                            openComponent = if (openComponent == key) null else key
                        }
                    )
                }
            }
        }
    }
}

@Composable
private fun NodeRow(
    node: NodeHealth,
    expanded: Boolean,
    openComponent: String?,
    onToggle: () -> Unit,
    onComponent: (String) -> Unit
) {
    Column(Modifier.fillMaxWidth()) {
        Row(
            Modifier
                .fillMaxWidth()
                .clickable(onClick = onToggle)
                .padding(horizontal = 18.dp, vertical = 14.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            StatusDot(node.status)
            Spacer(Modifier.width(12.dp))
            Column(Modifier.weight(1f)) {
                Text(node.host, color = ThunderInk.Ink, fontSize = 15.sp,
                    fontWeight = FontWeight.Medium)
                Text(node.summary, color = ThunderInk.Mute, fontSize = 12.5.sp)
            }
            Text(
                node.score?.let { "$it%" } ?: "--",
                color = statusColor(node.status),
                fontSize = 15.sp,
                fontFamily = FontFamily.Monospace
            )
            Spacer(Modifier.width(8.dp))
            Icon(
                if (expanded) Icons.Outlined.ExpandLess else Icons.Outlined.ExpandMore,
                contentDescription = null, tint = ThunderInk.Mute
            )
        }
        if (expanded) {
            node.components.forEach { c ->
                val key = "${node.node}/${c.component}"
                ComponentRow(
                    component = c,
                    expanded = openComponent == key,
                    onClick = { onComponent(key) }
                )
            }
            Spacer(Modifier.height(6.dp))
        }
        Hairline(dim = true)
    }
}

@Composable
private fun ComponentRow(
    component: HealthComponent,
    expanded: Boolean,
    onClick: () -> Unit
) {
    Column(
        Modifier
            .fillMaxWidth()
            .background(ThunderInk.SlateDeep)
    ) {
        Row(
            Modifier
                .fillMaxWidth()
                .clickable(onClick = onClick)
                .padding(start = 34.dp, end = 18.dp, top = 11.dp, bottom = 11.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            StatusDot(component.status, small = true)
            Spacer(Modifier.width(12.dp))
            Column(Modifier.weight(1f)) {
                Text(component.component, color = ThunderInk.Ink, fontSize = 14.sp)
                Text(component.detail, color = ThunderInk.Mute, fontSize = 12.sp)
            }
            Text(
                // "--" rather than a number, because a component with no
                // sensors has no score and inventing one is the whole trap.
                component.score?.let { "$it%" } ?: "--",
                color = statusColor(component.status),
                fontSize = 13.sp,
                fontFamily = FontFamily.Monospace
            )
        }
        if (expanded) {
            Column(
                Modifier.padding(start = 34.dp, end = 18.dp, bottom = 14.dp),
                verticalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                if (component.readings.isNotEmpty()) {
                    Column(verticalArrangement = Arrangement.spacedBy(3.dp)) {
                        component.readings.forEach { r ->
                            Row(Modifier.fillMaxWidth()) {
                                Text(r.label, color = ThunderInk.Mute, fontSize = 12.sp,
                                    modifier = Modifier.weight(1f))
                                Text(
                                    r.value + (r.limit?.let { "  (limit $it)" } ?: ""),
                                    color = ThunderInk.Ink, fontSize = 12.sp,
                                    fontFamily = FontFamily.Monospace
                                )
                            }
                        }
                    }
                }
                component.findings.forEach { f ->
                    Column(
                        Modifier
                            .fillMaxWidth()
                            .clip(RoundedCornerShape(6.dp))
                            .background(ThunderInk.Surface)
                            .padding(12.dp),
                        verticalArrangement = Arrangement.spacedBy(6.dp)
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            StatusDot(
                                when (f.severity) {
                                    "attention" -> "attention"
                                    "info" -> "unknown"
                                    else -> "watch"
                                },
                                small = true
                            )
                            Spacer(Modifier.width(8.dp))
                            Text(f.finding, color = ThunderInk.Ink, fontSize = 13.sp,
                                fontWeight = FontWeight.Medium)
                        }
                        Text(f.why, color = ThunderInk.Mute, fontSize = 12.5.sp, lineHeight = 17.sp)
                        Text("Fix: ${f.fix}", color = ThunderInk.Gold, fontSize = 12.5.sp,
                            lineHeight = 17.sp)
                    }
                }
                if (component.findings.isEmpty() && component.readings.isEmpty()) {
                    Text("Nothing to report.", color = ThunderInk.Mute, fontSize = 12.5.sp)
                }
            }
        }
    }
}

@Composable
private fun StatusDot(status: String, small: Boolean = false) {
    val size = if (small) 7.dp else 9.dp
    Box(
        Modifier
            .width(size)
            .height(size)
            .clip(RoundedCornerShape(size))
            .background(statusColor(status))
    )
}

@Composable
private fun statusColor(status: String): Color = when (status) {
    "ok" -> ThunderInk.Live
    "watch" -> ThunderInk.Gold
    "attention" -> Color(0xFFD1554E)
    else -> ThunderInk.Mute      // unknown: not a pass and not a failure
}
