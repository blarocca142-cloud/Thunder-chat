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
    val message: String,
    val quality: String? = null
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

/** What the single GPU is doing, so the UI can show real progress rather than
 *  an indefinite spinner. Mirrors the "gpu" object on /status. */
data class GpuState(
    val up: Boolean = false,
    val loading: String? = null,
    val busy: Boolean = false,
    val step: Int = 0,
    val totalSteps: Int = 0
) {
    fun hasProgress(): Boolean = busy && totalSteps > 0 && step > 0
    fun fraction(): Float = if (totalSteps > 0) step.toFloat() / totalSteps else 0f
}

data class AppRelease(
    val backendVersion: String,
    val apkVersion: String?,
    val apkUrl: String?,
    val notes: String,
    val mandatory: Boolean
)

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
    val maintenanceUntilEpochSec: Long? = null,
    val gpu: GpuState = GpuState()
)

class ThunderApi(
    private val client: OkHttpClient = OkHttpClient.Builder()
        .connectTimeout(8, TimeUnit.SECONDS)
        .readTimeout(120, TimeUnit.SECONDS)
        .build()
) {
    private val jsonType = "application/json; charset=utf-8".toMediaType()

    // A stream stays open for the whole reply, so it must not inherit the
    // 120s read timeout used for one-shot calls.
    private val streamClient: OkHttpClient = client.newBuilder()
        .readTimeout(10, TimeUnit.MINUTES)
        .build()
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
                val g = o.optJSONObject("gpu")
                val gp = g?.optJSONObject("progress")
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
                    maintenanceUntilEpochSec = maint?.let { if (it.isNull("until")) null else it.optLong("until") },
                    gpu = GpuState(
                        up = g?.optBoolean("up", false) ?: false,
                        loading = g?.optionalString("loading"),
                        busy = g?.optBoolean("busy", false) ?: false,
                        step = gp?.optInt("step", 0) ?: 0,
                        totalSteps = gp?.optInt("total", 0) ?: 0
                    )
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

    /**
     * Streams a reply, calling [onDelta] as text arrives. Falls back to the
     * blocking endpoint if the server is older or the stream dies before any
     * text appeared, so a partial rollout cannot leave chat broken.
     */
    suspend fun chatStream(
        server: String,
        message: String,
        onDelta: (String) -> Unit
    ): String = withContext(Dispatchers.IO) {
        if (server.isBlank()) return@withContext chat(server, message)
        // History comes from Serverus server-side, same as the blocking path.
        val payload = JSONObject().put("message", message)
        val built = StringBuilder()
        try {
            val req = Request.Builder()
                .url("${base(server)}/chat/stream")
                .post(payload.toString().toRequestBody(jsonType))
                .build()
            streamClient.newCall(req).execute().use { res ->
                if (!res.isSuccessful) return@withContext chat(server, message)
                val src = res.body?.source() ?: return@withContext chat(server, message)
                while (true) {
                    val line = src.readUtf8Line() ?: break
                    if (line.isBlank()) continue
                    val o = runCatching { JSONObject(line) }.getOrNull() ?: continue
                    if (o.optBoolean("done")) break
                    val delta = o.optString("delta")
                    if (delta.isNotEmpty()) {
                        built.append(delta)
                        withContext(Dispatchers.Main) { onDelta(delta) }
                    }
                }
            }
        } catch (e: Exception) {
            if (built.isEmpty()) return@withContext chat(server, message)
            built.append("\n[connection dropped]")
        }
        if (built.isEmpty()) chat(server, message) else built.toString()
    }

    suspend fun image(server: String, prompt: String, style: String, aspect: String): Creation =
        withContext(Dispatchers.IO) {
            studioPost(server, "/image", JSONObject()
                .put("prompt", prompt)
                .put("style", style)
                .put("aspect", aspect))
        }

    suspend fun video(
        server: String,
        prompt: String,
        style: String,
        duration: Int,
        quality: String
    ): Creation = withContext(Dispatchers.IO) {
        studioPost(server, "/video", JSONObject()
            .put("prompt", prompt)
            .put("style", style)
            .put("duration", duration)
            .put("quality", quality))
    }

    suspend fun appRelease(server: String): AppRelease? = withContext(Dispatchers.IO) {
        if (server.isBlank()) return@withContext null
        try {
            val req = Request.Builder().url("${base(server)}/app/version").get().build()
            client.newCall(req).execute().use { res ->
                if (!res.isSuccessful) return@use null
                val o = JSONObject(res.body?.string().orEmpty())
                AppRelease(
                    backendVersion = o.optString("backend_version"),
                    apkVersion = o.optionalString("apk_version"),
                    apkUrl = o.optionalString("apk_url"),
                    notes = o.optString("notes"),
                    mandatory = o.optBoolean("mandatory", false)
                )
            }
        } catch (_: Exception) {
            null
        }
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
        message = o.optString("message"),
        quality = o.optionalString("quality")
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
