package com.thunder.app.data

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.util.concurrent.TimeUnit

data class Creation(
    val id: String,
    val kind: String,
    val prompt: String,
    val style: String,
    val aspect: String,
    val duration: Int?,
    val url: String,
    val videoUrl: String? = null,
    val videoStatus: String? = null,
    val stub: Boolean,
    val message: String
) {
    /** processing | done | error | stub | "" for stills */
    fun videoPhase(): String {
        val reported = videoStatus?.lowercase()?.trim().orEmpty()
        if (reported.isNotEmpty()) return reported
        if (kind != "video") return ""
        if (!videoUrl.isNullOrBlank() && !stub) return "done"
        if (stub) return "stub"
        return "processing"
    }

    fun isVideoPending(): Boolean = kind == "video" && videoPhase() == "processing"
}

data class ThunderStatus(
    val mode: String,
    val odriss: String,
    val cache: String,
    val jobId: String?,
    val jobTitle: String?,
    val progress: String?,
    val message: String,
    val demo: Boolean = false,
    val maintenanceActive: Boolean = false,
    val maintenanceMessage: String? = null,
    val maintenanceUntilEpochSec: Long? = null
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
                val maint = o.optJSONObject("maintenance")
                ThunderStatus(
                    mode = o.optString("mode", "idle"),
                    odriss = o.optString("odriss", "no_heartbeat"),
                    cache = o.optString("cache", "idle"),
                    jobId = o.optString("job_id").ifBlank { null },
                    jobTitle = o.optString("job_title").ifBlank { null },
                    progress = o.optString("progress").ifBlank { null },
                    message = o.optString("message", ""),
                    demo = false,
                    maintenanceActive = maint?.optBoolean("active", false) ?: false,
                    maintenanceMessage = maint?.optString("message")?.ifBlank { null },
                    maintenanceUntilEpochSec = maint?.let { if (it.isNull("until")) null else it.optLong("until") }
                )
            }
        } catch (e: Exception) {
            demoStatus("Can't reach Main. ${e.message ?: ""}")
        }
    }

    suspend fun chat(server: String, message: String): String = withContext(Dispatchers.IO) {
        if (server.isBlank()) {
            return@withContext "I'm here in shell mode — heard \"$message\". Point Settings at Main when that box is up and I'll really talk."
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

    suspend fun image(server: String, prompt: String, style: String, aspect: String): Creation =
        withContext(Dispatchers.IO) {
            studioPost(server, "/image", JSONObject()
                .put("prompt", prompt)
                .put("style", style)
                .put("aspect", aspect))
        }

    suspend fun video(server: String, prompt: String, style: String, duration: Int): Creation =
        withContext(Dispatchers.IO) {
            studioPost(server, "/video", JSONObject()
                .put("prompt", prompt)
                .put("style", style)
                .put("duration", duration))
        }

    suspend fun creations(server: String): List<Creation> = withContext(Dispatchers.IO) {
        if (server.isBlank()) return@withContext emptyList()
        try {
            val req = Request.Builder().url("${base(server)}/creations").get().build()
            client.newCall(req).execute().use { res ->
                val body = res.body?.string().orEmpty()
                if (!res.isSuccessful) return@use emptyList()
                val arr = JSONObject(body).optJSONArray("items") ?: return@use emptyList()
                buildList {
                    for (i in 0 until arr.length()) add(parseCreation(arr.getJSONObject(i)))
                }
            }
        } catch (_: Exception) {
            emptyList()
        }
    }

    suspend fun creation(server: String, id: String): Creation? = withContext(Dispatchers.IO) {
        if (server.isBlank() || id.isBlank()) return@withContext null
        try {
            val req = Request.Builder().url("${base(server)}/creations/$id").get().build()
            client.newCall(req).execute().use { res ->
                val body = res.body?.string().orEmpty()
                if (!res.isSuccessful) return@use null
                parseCreation(JSONObject(body))
            }
        } catch (_: Exception) {
            null
        }
    }

    fun mediaHref(server: String, pathOrUrl: String?): String? {
        if (pathOrUrl.isNullOrBlank()) return null
        if (pathOrUrl.startsWith("http")) return pathOrUrl
        if (server.isBlank()) return null
        return "${base(server)}$pathOrUrl"
    }

    suspend fun fetchBytes(server: String, pathOrUrl: String): ByteArray? = withContext(Dispatchers.IO) {
        val href = mediaHref(server, pathOrUrl) ?: return@withContext null
        try {
            val req = Request.Builder().url(href).get().build()
            client.newCall(req).execute().use { res ->
                if (!res.isSuccessful) null else res.body?.bytes()
            }
        } catch (_: Exception) {
            null
        }
    }

    private fun studioPost(server: String, path: String, payload: JSONObject): Creation {
        if (server.isBlank()) {
            return Creation(
                id = "shell_${System.currentTimeMillis()}",
                kind = if (path.endsWith("video")) "video" else "image",
                prompt = payload.optString("prompt"),
                style = payload.optString("style", "Cinematic"),
                aspect = payload.optString("aspect", "1:1"),
                duration = payload.optInt("duration").takeIf { it > 0 },
                url = "",
                videoUrl = null,
                videoStatus = if (path.endsWith("video")) "stub" else null,
                stub = true,
                message = "Shell mode — point Settings at Main to hit Studio hooks."
            )
        }
        return try {
            val req = Request.Builder()
                .url("${base(server)}$path")
                .post(payload.toString().toRequestBody(jsonType))
                .build()
            client.newCall(req).execute().use { res ->
                val body = res.body?.string().orEmpty()
                if (!res.isSuccessful) {
                    Creation(
                        id = "err",
                        kind = "image",
                        prompt = payload.optString("prompt"),
                        style = payload.optString("style"),
                        aspect = payload.optString("aspect", "1:1"),
                        duration = null,
                        url = "",
                        stub = true,
                        message = "Main ${res.code}: $body"
                    )
                } else parseCreation(JSONObject(body))
            }
        } catch (e: Exception) {
            Creation(
                id = "err",
                kind = "image",
                prompt = payload.optString("prompt"),
                style = payload.optString("style"),
                aspect = payload.optString("aspect", "1:1"),
                duration = null,
                url = "",
                stub = true,
                message = "Studio offline. ${e.message ?: ""}"
            )
        }
    }

    private fun parseCreation(o: JSONObject) = Creation(
        id = o.optString("id"),
        kind = o.optString("kind", "image"),
        prompt = o.optString("prompt"),
        style = o.optString("style"),
        aspect = o.optString("aspect", "1:1"),
        duration = o.optInt("duration").takeIf { it > 0 },
        url = o.optString("url"),
        videoUrl = o.optionalString("video_url"),
        videoStatus = o.optionalString("video_status"),
        stub = o.optBoolean("stub", true),
        message = o.optString("message")
    )

    private fun JSONObject.optionalString(key: String): String? {
        if (!has(key) || isNull(key)) return null
        return optString(key).ifBlank { null }
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
