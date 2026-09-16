package com.thunder.app.ui

import android.widget.Toast
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.ArrowBack
import androidx.compose.material.icons.outlined.ContentCopy
import androidx.compose.material.icons.outlined.Delete
import androidx.compose.material.icons.outlined.Download
import androidx.compose.material.icons.outlined.Folder
import androidx.compose.material.icons.outlined.InsertDriveFile
import androidx.compose.material.icons.outlined.Refresh
import androidx.compose.material.icons.outlined.Share
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
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
import androidx.compose.ui.platform.ClipboardManager
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.thunder.app.data.CodeFile
import com.thunder.app.data.CodeProject
import com.thunder.app.data.CodeStore
import com.thunder.app.data.ThunderApi
import kotlinx.coroutines.launch

/**
 * The code Thunder has written, and the way off the phone.
 *
 * Coding mode could produce code and then had nowhere to put it - the reply
 * scrolled away and the only route out was selecting text by hand. Files live
 * on Main in real directories; this browses them, and every screen ends in
 * either Save (into Downloads) or Share.
 */
@Composable
fun CodeVault(
    server: String,
    api: ThunderApi,
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    val clipboard = LocalClipboardManager.current
    val scope = rememberCoroutineScope()
    val store = remember { CodeStore(context.applicationContext) }

    var projects by remember { mutableStateOf<List<CodeProject>>(emptyList()) }
    var openProject by remember { mutableStateOf<String?>(null) }
    var files by remember { mutableStateOf<List<CodeFile>>(emptyList()) }
    var openFile by remember { mutableStateOf<CodeFile?>(null) }
    var content by remember { mutableStateOf<String?>(null) }
    var loading by remember { mutableStateOf(false) }
    var confirmDelete by remember { mutableStateOf<CodeFile?>(null) }

    fun toast(msg: String) =
        Toast.makeText(context, msg, Toast.LENGTH_SHORT).show()

    suspend fun loadProjects() {
        loading = true
        projects = api.codeProjects(server)
        loading = false
    }

    suspend fun loadFiles(project: String) {
        loading = true
        files = api.codeFiles(server, project)
        loading = false
    }

    LaunchedEffect(server) { loadProjects() }

    Column(modifier.fillMaxSize()) {
        // ---- header -------------------------------------------------------
        Row(
            Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp, vertical = 12.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            if (openProject != null) {
                Icon(
                    Icons.Outlined.ArrowBack, contentDescription = "Back",
                    tint = ThunderInk.Ink,
                    modifier = Modifier
                        .clip(RoundedCornerShape(6.dp))
                        .clickable {
                            if (openFile != null) {
                                openFile = null; content = null
                            } else {
                                openProject = null; files = emptyList()
                            }
                        }
                        .padding(4.dp)
                )
                Spacer(Modifier.width(10.dp))
            }
            Text(
                openFile?.name ?: openProject ?: "Code",
                color = ThunderInk.Ink, fontSize = 18.sp, fontWeight = FontWeight.SemiBold,
                modifier = Modifier.weight(1f)
            )
            if (openFile == null) {
                Icon(
                    Icons.Outlined.Refresh, contentDescription = "Refresh",
                    tint = ThunderInk.Mute,
                    modifier = Modifier
                        .clip(RoundedCornerShape(6.dp))
                        .clickable {
                            scope.launch {
                                val p = openProject
                                if (p == null) loadProjects() else loadFiles(p)
                            }
                        }
                        .padding(4.dp)
                )
            }
        }
        Hairline(dim = true)

        if (loading && projects.isEmpty() && files.isEmpty()) {
            Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                CircularProgressIndicator(color = ThunderInk.Gold)
            }
            return@Column
        }

        val file = openFile
        val project = openProject
        when {
            // ---- one file --------------------------------------------------
            file != null -> {
                LaunchedEffect(file.name, project) {
                    content = api.codeContent(server, project.orEmpty(), file.name)
                }
                val text = content
                Row(
                    Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 14.dp, vertical = 10.dp),
                    horizontalArrangement = Arrangement.spacedBy(18.dp)
                ) {
                    VaultAction(Icons.Outlined.Download, "Save") {
                        val body = text
                        if (body == null) toast("Still loading") else {
                            val ok = store.saveToDownloads(body.toByteArray(), file.name)
                            toast(if (ok) "Saved to ${store.savedLocation()}" else "Could not save")
                        }
                    }
                    VaultAction(Icons.Outlined.Share, "Send") {
                        val body = text
                        if (body == null) toast("Still loading")
                        else store.share(body.toByteArray(), file.name)
                    }
                    VaultAction(Icons.Outlined.ContentCopy, "Copy") {
                        val body = text
                        if (body == null) toast("Still loading") else {
                            clipboard.setText(AnnotatedString(body))
                            toast("Copied")
                        }
                    }
                    VaultAction(Icons.Outlined.Delete, "Delete") {
                        confirmDelete = file
                    }
                }
                Hairline(dim = true)
                if (text == null) {
                    Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                        CircularProgressIndicator(color = ThunderInk.Gold)
                    }
                } else {
                    // Code must not wrap - a wrapped line is unreadable and
                    // misleading about indentation. It scrolls sideways instead.
                    Box(
                        Modifier
                            .fillMaxSize()
                            .verticalScroll(rememberScrollState())
                            .padding(14.dp)
                    ) {
                        Text(
                            text,
                            modifier = Modifier.horizontalScroll(rememberScrollState()),
                            color = ThunderInk.Ink,
                            fontFamily = FontFamily.Monospace,
                            fontSize = 12.sp,
                            lineHeight = 17.sp
                        )
                    }
                }
            }

            // ---- files in a project ----------------------------------------
            project != null -> {
                Row(
                    Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 14.dp, vertical = 10.dp),
                    horizontalArrangement = Arrangement.spacedBy(18.dp)
                ) {
                    VaultAction(Icons.Outlined.Download, "Save all (.zip)") {
                        scope.launch {
                            val zip = api.codeArchive(server, project)
                            if (zip == null) toast("Could not build the zip") else {
                                val ok = store.saveToDownloads(
                                    zip, "$project.zip", "application/zip"
                                )
                                toast(if (ok) "Saved $project.zip to ${store.savedLocation()}"
                                      else "Could not save")
                            }
                        }
                    }
                    VaultAction(Icons.Outlined.Share, "Send (.zip)") {
                        scope.launch {
                            val zip = api.codeArchive(server, project)
                            if (zip == null) toast("Could not build the zip")
                            else store.share(zip, "$project.zip", "application/zip")
                        }
                    }
                }
                Hairline(dim = true)
                if (files.isEmpty()) {
                    EmptyVault("Nothing in $project yet.")
                } else {
                    LazyColumn(
                        Modifier.fillMaxSize(),
                        contentPadding = PaddingValues(vertical = 8.dp)
                    ) {
                        items(files) { f ->
                            VaultRow(
                                icon = Icons.Outlined.InsertDriveFile,
                                title = f.name,
                                subtitle = buildString {
                                    if (f.language.isNotBlank()) append(f.language).append("  ")
                                    append(humanBytes(f.bytes))
                                    if (f.lines > 0) append("  ${f.lines} lines")
                                }
                            ) { openFile = f }
                        }
                    }
                }
            }

            // ---- projects ---------------------------------------------------
            else -> {
                if (projects.isEmpty()) {
                    EmptyVault(
                        if (server.isBlank()) "Connect to Main to see saved code."
                        else "No code saved yet.\nAsk Thunder for code, then tap Save on the block."
                    )
                } else {
                    LazyColumn(
                        Modifier.fillMaxSize(),
                        contentPadding = PaddingValues(vertical = 8.dp)
                    ) {
                        items(projects) { p ->
                            VaultRow(
                                icon = Icons.Outlined.Folder,
                                title = p.name,
                                subtitle = "${p.files} file${if (p.files == 1) "" else "s"}  " +
                                    humanBytes(p.bytes)
                            ) {
                                openProject = p.name
                                scope.launch { loadFiles(p.name) }
                            }
                        }
                    }
                }
            }
        }
    }

    val doomed = confirmDelete
    if (doomed != null) {
        AlertDialog(
            onDismissRequest = { confirmDelete = null },
            title = { Text("Delete ${doomed.name}?") },
            text = { Text("This removes it from Main. Anything already saved to this phone stays.") },
            confirmButton = {
                TextButton(onClick = {
                    val p = openProject.orEmpty()
                    confirmDelete = null
                    scope.launch {
                        if (api.deleteCode(server, p, doomed.name)) {
                            openFile = null
                            content = null
                            loadFiles(p)
                            toast("Deleted")
                        } else toast("Could not delete")
                    }
                }) { Text("Delete", color = ThunderInk.Gold) }
            },
            dismissButton = {
                TextButton(onClick = { confirmDelete = null }) {
                    Text("Keep", color = ThunderInk.Mute)
                }
            },
            containerColor = ThunderInk.Surface
        )
    }
}

@Composable
private fun VaultAction(
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    label: String,
    onClick: () -> Unit
) {
    Row(
        Modifier
            .clip(RoundedCornerShape(6.dp))
            .clickable(onClick = onClick)
            .padding(horizontal = 4.dp, vertical = 4.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Icon(icon, contentDescription = null, tint = ThunderInk.Mute)
        Spacer(Modifier.width(6.dp))
        Text(label, color = ThunderInk.Mute, fontSize = 13.sp)
    }
}

@Composable
private fun VaultRow(
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    title: String,
    subtitle: String,
    onClick: () -> Unit
) {
    Row(
        Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .padding(horizontal = 18.dp, vertical = 14.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Icon(icon, contentDescription = null, tint = ThunderInk.Gold)
        Spacer(Modifier.width(14.dp))
        Column(Modifier.weight(1f)) {
            Text(title, color = ThunderInk.Ink, fontSize = 15.sp, fontFamily = FontFamily.Monospace)
            Text(subtitle, color = ThunderInk.Mute, fontSize = 12.sp)
        }
    }
}

@Composable
private fun EmptyVault(message: String) {
    Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
        Text(
            message,
            color = ThunderInk.Mute,
            fontSize = 14.sp,
            modifier = Modifier.padding(32.dp)
        )
    }
}

private fun humanBytes(b: Long): String = when {
    b < 1024 -> "$b B"
    b < 1024 * 1024 -> "${b / 1024} KB"
    else -> String.format("%.1f MB", b / 1024.0 / 1024.0)
}
