package com.thunder.app.data

import android.content.ContentValues
import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.LinearGradient
import android.graphics.Paint
import android.graphics.Shader
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import androidx.core.content.FileProvider
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

class CreationStore(context: Context) {
    private val app = context.applicationContext
    private val file = File(app.filesDir, "thunder_creations.json")
    private val lock = Any()

    fun list(): List<Creation> = synchronized(lock) { load() }

    fun add(item: Creation) = synchronized(lock) {
        persist(listOf(item) + load().filterNot { it.id == item.id })
    }

    private fun load(): List<Creation> {
        if (!file.exists()) return emptyList()
        return try {
            val arr = JSONObject(file.readText()).optJSONArray("items") ?: return emptyList()
            buildList {
                for (i in 0 until arr.length()) {
                    val o = arr.getJSONObject(i)
                    add(
                        Creation(
                            id = o.optString("id"),
                            kind = o.optString("kind", "image"),
                            prompt = o.optString("prompt"),
                            style = o.optString("style"),
                            aspect = o.optString("aspect", "1:1"),
                            duration = o.optInt("duration").takeIf { it > 0 },
                            url = o.optString("url"),
                            videoUrl = o.optString("video_url").ifBlank { null },
                            videoStatus = o.optString("video_status").ifBlank { null },
                            stub = o.optBoolean("stub", true),
                            message = o.optString("message")
                        )
                    )
                }
            }
        } catch (_: Exception) {
            emptyList()
        }
    }

    private fun persist(items: List<Creation>) {
        val arr = JSONArray()
        items.take(80).forEach { item ->
            arr.put(
                JSONObject()
                    .put("id", item.id)
                    .put("kind", item.kind)
                    .put("prompt", item.prompt)
                    .put("style", item.style)
                    .put("aspect", item.aspect)
                    .put("duration", item.duration)
                    .put("url", item.url)
                    .put("video_url", item.videoUrl ?: JSONObject.NULL)
                    .put("video_status", item.videoStatus ?: JSONObject.NULL)
                    .put("stub", item.stub)
                    .put("message", item.message)
            )
        }
        val tmp = File(file.parentFile, "${file.name}.tmp")
        tmp.writeText(JSONObject().put("items", arr).toString())
        if (!tmp.renameTo(file)) {
            tmp.copyTo(file, overwrite = true)
            tmp.delete()
        }
    }

    fun sharePng(bytes: ByteArray, name: String) {
        val dir = File(app.cacheDir, "share").apply { mkdirs() }
        val out = File(dir, name.ifBlank { "thunder.png" })
        out.writeBytes(bytes)
        val uri = FileProvider.getUriForFile(app, "${app.packageName}.files", out)
        val intent = Intent(Intent.ACTION_SEND).apply {
            type = "image/png"
            putExtra(Intent.EXTRA_STREAM, uri)
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_ACTIVITY_NEW_TASK)
        }
        app.startActivity(Intent.createChooser(intent, "Share Thunder still").addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
    }

    fun savePng(bytes: ByteArray, name: String): Boolean {
        val display = if (name.endsWith(".png")) name else "$name.png"
        return try {
            if (Build.VERSION.SDK_INT >= 29) {
                val values = ContentValues().apply {
                    put(MediaStore.Images.Media.DISPLAY_NAME, display)
                    put(MediaStore.Images.Media.MIME_TYPE, "image/png")
                    put(MediaStore.Images.Media.RELATIVE_PATH, Environment.DIRECTORY_PICTURES + "/Thunder")
                }
                val uri: Uri = app.contentResolver.insert(
                    MediaStore.Images.Media.EXTERNAL_CONTENT_URI,
                    values
                ) ?: return false
                app.contentResolver.openOutputStream(uri)?.use { it.write(bytes) } ?: return false
                true
            } else {
                val dir = File(app.getExternalFilesDir(Environment.DIRECTORY_PICTURES), "Thunder").apply { mkdirs() }
                File(dir, display).writeBytes(bytes)
                true
            }
        } catch (_: Exception) {
            false
        }
    }

    companion object {
        fun stubBitmap(prompt: String, style: String, aspect: String): Bitmap {
            val (w, h) = when (aspect) {
                "16:9" -> 960 to 540
                "9:16" -> 540 to 960
                "4:3" -> 800 to 600
                else -> 768 to 768
            }
            val bmp = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888)
            val canvas = Canvas(bmp)
            val paint = Paint(Paint.ANTI_ALIAS_FLAG)
            paint.shader = LinearGradient(
                0f, 0f, 0f, h.toFloat(),
                intArrayOf(0xFF2C3340.toInt(), 0xFF16191F.toInt()),
                null,
                Shader.TileMode.CLAMP
            )
            canvas.drawRect(0f, 0f, w.toFloat(), h.toFloat(), paint)
            paint.shader = null
            paint.color = 0xFFC4A35A.toInt()
            paint.style = Paint.Style.STROKE
            paint.strokeWidth = 3f
            canvas.drawRect(28f, 28f, w - 28f, h - 28f, paint)
            paint.style = Paint.Style.FILL
            paint.textSize = 28f
            canvas.drawText("THUNDER  ·  STUDIO", 50f, 80f, paint)
            paint.color = 0xFFEDE8DF.toInt()
            paint.textSize = 36f
            canvas.drawText(style.ifBlank { "Cinematic" }, 50f, 130f, paint)
            paint.textSize = 26f
            val words = prompt.split(Regex("\\s+"))
            var line = ""
            var y = 190f
            words.forEach { word ->
                val trial = if (line.isEmpty()) word else "$line $word"
                if (paint.measureText(trial) > w - 100) {
                    canvas.drawText(line, 50f, y, paint)
                    line = word
                    y += 36f
                } else line = trial
            }
            if (line.isNotEmpty()) canvas.drawText(line, 50f, y, paint)
            return bmp
        }
    }
}
