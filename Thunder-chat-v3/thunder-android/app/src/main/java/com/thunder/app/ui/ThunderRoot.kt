package com.thunder.app.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextFieldDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.thunder.app.data.ThunderApi
import kotlinx.coroutines.launch

data class Line(val who: String, val text: String)

@Composable
fun ThunderRoot() {
    val api = remember { ThunderApi() }
    var server by remember { mutableStateOf("") }
    var draft by remember { mutableStateOf("") }
    val lines = remember { mutableStateListOf(Line("thunder", "Shell is up. Server can stay empty.")) }
    val scope = rememberCoroutineScope()
    val bg = Color(0xFF0B0B0F)
    val ink = Color(0xFFE8EDF2)

    Column(
        Modifier
            .fillMaxSize()
            .background(bg)
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        Text("THUNDER", color = Color(0xFFF5C542), fontSize = 22.sp)
        OutlinedTextField(
            value = server,
            onValueChange = { server = it },
            modifier = Modifier.fillMaxWidth(),
            label = { Text("Server URL (optional)") },
            colors = fieldColors(ink)
        )
        LazyColumn(Modifier.weight(1f).fillMaxWidth()) {
            items(lines) { line ->
                Text(
                    "${line.who}: ${line.text}",
                    color = if (line.who == "you") Color(0xFF8EC8FF) else Color(0xFFC8F0C0),
                    modifier = Modifier.padding(vertical = 4.dp)
                )
            }
        }
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            OutlinedTextField(
                value = draft,
                onValueChange = { draft = it },
                modifier = Modifier.weight(1f),
                label = { Text("message") },
                colors = fieldColors(ink)
            )
            Button(onClick = {
                val msg = draft.trim()
                if (msg.isEmpty()) return@Button
                draft = ""
                lines.add(Line("you", msg))
                scope.launch {
                    val reply = api.chat(server, msg)
                    lines.add(Line("thunder", reply))
                }
            }) { Text("send") }
        }
    }
}

@Composable
private fun fieldColors(ink: Color) = TextFieldDefaults.colors(
    focusedTextColor = ink,
    unfocusedTextColor = ink,
    focusedContainerColor = Color(0xFF15181D),
    unfocusedContainerColor = Color(0xFF15181D),
    focusedIndicatorColor = Color(0xFFF5C542),
    unfocusedIndicatorColor = Color(0xFF333333),
    focusedLabelColor = ink,
    unfocusedLabelColor = Color(0xFF888888)
)
