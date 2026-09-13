package com.thunder.app.data

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.util.concurrent.TimeUnit

data class ThunderStatus(
    val mode: String,
    val odriss: String,
    val cache: String,
    val jobId: String?,
    val jobTitle: String?,
    val progress: String?,
    val message: String,
    val demo: Boolean = false
)

class ThunderApi(
    private val client: OkHttpClient = OkHttpClient.Builder()
        .connectTimeout(8, TimeUnit.SECONDS)
        .readTimeout(120, TimeUnit.SECONDS)
        .build()
) {
    private val jsonType = "application/json; charset=utf-8".toMediaType()
    private fun base(url: String) = url.trim().trimEnd('/')

    suspend fun status(server: String): ThunderStatus = withContext(Dispatchers.IO) {
        if (server.isBlank()) return@withContext demoStatus("No server yet — shell mode")
        try {
            val req = Request.Builder().url("${base(server)}/status").get().build()
            client.newCall(req).execute().use { res ->
                val body = res.body?.string().orEmpty()
                if (!res.isSuccessful) return@use demoStatus("Main said ${res.code}")
                val o = JSONObject(body)
                ThunderStatus(
                    mode = o.optString("mode", "idle"),
                    odriss = o.optString("odriss", "no_heartbeat"),
                    cache = o.optString("cache", "idle"),
                    jobId = o.optString("job_id").ifBlank { null },
                    jobTitle = o.optString("job_title").ifBlank { null },
                    progress = o.optString("progress").ifBlank { null },
                    message = o.optString("message", ""),
                    demo = false
                )
            }
        } catch (e: Exception) {
            demoStatus("Can't reach Main. ${e.message ?: ""}")
        }
    }

    suspend fun chat(server: String, message: String): String = withContext(Dispatchers.IO) {
        if (server.isBlank()) {
            return@withContext shellReply(message)
        }
        try {
            val payload = JSONObject().put("message", message).toString()
            val req = Request.Builder()
                .url("${base(server)}/chat")
                .post(payload.toRequestBody(jsonType))
                .build()
            client.newCall(req).execute().use { res ->
                val body = res.body?.string().orEmpty()
                if (!res.isSuccessful) return@use "Main ${res.code}: $body"
                JSONObject(body).optString("reply", body)
            }
        } catch (e: Exception) {
            "Main offline. Demo: heard \"$message\"."
        }
    }

    // No-network placeholder so chat is testable before Main is wired up.
    private fun shellReply(message: String): String {
        val m = message.trim().lowercase()
        return when {
            m.isEmpty() -> "Say something and I'll answer — shell mode, no model wired up yet."
            listOf("hello", "hi", "hey").any { m.contains(it) } ->
                "Hey, I'm Thunder. Running in shell mode right now — no model connected."
            m.contains("test") ->
                "Test received. Bubbles, typing dots, and send all work. Point Settings at Main for real replies."
            m.contains("help") ->
                "Shell mode just echoes for now. Set the server URL in Settings once Main + Ollama are running."
            m.contains("who are you") || m.contains("what are you") ->
                "I'm Thunder, your local AI. Right now I'm the offline placeholder until Main's model is wired in."
            else -> "Heard: \"$message\". Still shell mode — set Main's URL in Settings for real replies."
        }
    }

    private fun demoStatus(message: String) = ThunderStatus(
        mode = "idle",
        odriss = "no_heartbeat",
        cache = "idle",
        jobId = null,
        jobTitle = null,
        progress = null,
        message = message,
        demo = true
    )
}
