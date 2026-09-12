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
        if (server.isBlank()) return@withContext demoStatus("Set a server URL")
        try {
            val req = Request.Builder().url("${base(server)}/status").get().build()
            client.newCall(req).execute().use { res ->
                val body = res.body?.string().orEmpty()
                if (!res.isSuccessful) return@use demoStatus("Main said ${res.code}")
                val o = JSONObject(body)
                ThunderStatus(
                    mode = o.optString("mode", "idle"),
                    odriss = o.optString("odriss", "no_heartbeat"),
                    cache = o.optString("cache", "down"),
                    jobId = o.optString("job_id").ifBlank { null },
                    jobTitle = o.optString("job_title").ifBlank { null },
                    progress = o.optString("progress").ifBlank { null },
                    message = o.optString("message", ""),
                    demo = false
                )
            }
        } catch (e: Exception) {
            demoStatus("Can't reach Main — demo mode. ${e.message ?: ""}")
        }
    }

    suspend fun chat(server: String, message: String): String = withContext(Dispatchers.IO) {
        if (server.isBlank()) {
            return@withContext "Point me at Main (Settings → Server URL). Until then I'm just the shell."
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
            "Main is offline ($e). Demo reply: I heard \"$message\". Wire /chat on Thunder-Main at 12:45."
        }
    }

    suspend fun queueJob(server: String, title: String, prompt: String): String =
        withContext(Dispatchers.IO) {
            if (server.isBlank()) return@withContext "No server — job not queued."
            try {
                val payload = JSONObject()
                    .put("title", title)
                    .put("prompt", prompt)
                    .toString()
                val req = Request.Builder()
                    .url("${base(server)}/job")
                    .post(payload.toRequestBody(jsonType))
                    .build()
                client.newCall(req).execute().use { res ->
                    val body = res.body?.string().orEmpty()
                    if (!res.isSuccessful) return@use "Queue failed ${res.code}"
                    val o = JSONObject(body)
                    "Queued ${o.optString("job_id")} (${o.optString("status")})"
                }
            } catch (e: Exception) {
                "Queue failed — Main unreachable. $e"
            }
        }

    suspend fun cancelJob(server: String, jobId: String?): String = withContext(Dispatchers.IO) {
        if (server.isBlank()) return@withContext "No server."
        try {
            val payload = JSONObject().put("job_id", jobId ?: "").toString()
            val req = Request.Builder()
                .url("${base(server)}/job/cancel")
                .post(payload.toRequestBody(jsonType))
                .build()
            client.newCall(req).execute().use { res ->
                if (!res.isSuccessful) "Cancel failed ${res.code}" else "Cancelled"
            }
        } catch (e: Exception) {
            "Cancel failed — Main unreachable."
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
