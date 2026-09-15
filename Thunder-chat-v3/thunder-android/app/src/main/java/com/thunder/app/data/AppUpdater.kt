package com.thunder.app.data

import android.content.Context
import android.content.Intent
import android.net.Uri
import androidx.core.content.FileProvider
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.File
import java.util.concurrent.TimeUnit

/**
 * Sideloaded APK updates. The app is not on Play, so it checks Main for a
 * published build and hands the file to Android's package installer.
 *
 * The user must have allowed "install unknown apps" for Thunder. If they have
 * not, the installer intent is refused, so [installApk] reports failure and the
 * caller falls back to opening the URL in a browser.
 */
object AppUpdater {

    /** True when [available] is a higher dotted version than [installed]. */
    fun isNewer(available: String?, installed: String): Boolean {
        if (available.isNullOrBlank()) return false
        val a = available.split('.').mapNotNull { it.trim().toIntOrNull() }
        val b = installed.split('.').mapNotNull { it.trim().toIntOrNull() }
        if (a.isEmpty()) return false
        for (i in 0 until maxOf(a.size, b.size)) {
            val x = a.getOrElse(i) { 0 }
            val y = b.getOrElse(i) { 0 }
            if (x != y) return x > y
        }
        return false
    }

    suspend fun download(context: Context, url: String): File? = withContext(Dispatchers.IO) {
        val client = OkHttpClient.Builder()
            .connectTimeout(15, TimeUnit.SECONDS)
            .readTimeout(5, TimeUnit.MINUTES)
            .build()
        val dir = File(context.cacheDir, "share").apply { mkdirs() }
        val out = File(dir, "thunder-update.apk")
        try {
            client.newCall(Request.Builder().url(url).get().build()).execute().use { res ->
                if (!res.isSuccessful) return@withContext null
                val body = res.body ?: return@withContext null
                out.outputStream().use { sink -> body.byteStream().copyTo(sink) }
            }
            out
        } catch (_: Exception) {
            null
        }
    }

    /** Returns false if the installer could not be launched at all. */
    fun installApk(context: Context, apk: File): Boolean {
        return try {
            val uri = FileProvider.getUriForFile(context, "${context.packageName}.files", apk)
            val intent = Intent(Intent.ACTION_VIEW).apply {
                setDataAndType(uri, "application/vnd.android.package-archive")
                addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
            context.startActivity(intent)
            true
        } catch (_: Exception) {
            false
        }
    }

    fun openInBrowser(context: Context, url: String) {
        runCatching {
            context.startActivity(
                Intent(Intent.ACTION_VIEW, Uri.parse(url)).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            )
        }
    }
}
