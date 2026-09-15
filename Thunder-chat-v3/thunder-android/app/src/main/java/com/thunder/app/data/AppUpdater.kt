package com.thunder.app.data

import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import androidx.core.content.FileProvider
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONObject
import java.io.File
import java.util.concurrent.TimeUnit

/**
 * Sideloaded APK updates. The app is not on Play, so it looks for a published
 * build and hands the file to Android's package installer.
 *
 * Main gets first say (so a build can be pinned), but the fallback asks GitHub
 * from the phone - that way updates still surface when Main is off, and Main
 * needs no outbound internet access of its own.
 *
 * The user must have allowed "install unknown apps" for Thunder. If they have
 * not, the installer intent is refused, so [installApk] reports failure and the
 * caller falls back to opening the URL in a browser.
 */
object AppUpdater {

    /** CI publishes the APK as a release asset with no version in its name, so
     *  the download URL this returns is stable across releases. */
    private const val LATEST_API =
        "https://api.github.com/repos/blarocca142-cloud/Thunder-chat/releases/latest"

    /** Reads the newest published release straight from GitHub. */
    suspend fun latestRelease(): AppRelease? = withContext(Dispatchers.IO) {
        val client = OkHttpClient.Builder()
            .connectTimeout(10, TimeUnit.SECONDS)
            .readTimeout(20, TimeUnit.SECONDS)
            .build()
        try {
            val req = Request.Builder().url(LATEST_API)
                .header("Accept", "application/vnd.github+json")
                .get().build()
            client.newCall(req).execute().use { res ->
                if (!res.isSuccessful) return@withContext null
                val o = JSONObject(res.body?.string().orEmpty())
                val version = o.optString("tag_name").removePrefix("v").ifBlank { null }
                    ?: return@withContext null
                val assets = o.optJSONArray("assets") ?: return@withContext null
                var url: String? = null
                for (i in 0 until assets.length()) {
                    val a = assets.getJSONObject(i)
                    if (a.optString("name").endsWith(".apk")) {
                        url = a.optString("browser_download_url").ifBlank { null }
                        break
                    }
                }
                if (url == null) return@withContext null
                AppRelease(
                    backendVersion = "",
                    apkVersion = version,
                    apkUrl = url,
                    notes = o.optString("name").ifBlank { "Thunder $version" },
                    mandatory = false
                )
            }
        } catch (_: Exception) {
            null
        }
    }

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

    /**
     * True when [apk] is signed with the same certificate as the installed app.
     * Android silently refuses an update whose signature differs, so checking
     * first turns a confusing "App not installed" into something explainable.
     */
    fun signatureMatchesInstalled(context: Context, apk: File): Boolean {
        return try {
            val pm = context.packageManager
            val flags = PackageManager.GET_SIGNING_CERTIFICATES
            val incoming = pm.getPackageArchiveInfo(apk.absolutePath, flags)
                ?.signingInfo?.apkContentsSigners ?: return false
            val installed = pm.getPackageInfo(context.packageName, flags)
                .signingInfo?.apkContentsSigners ?: return false
            val a = incoming.map { it.toCharsString() }.toSet()
            val b = installed.map { it.toCharsString() }.toSet()
            a.isNotEmpty() && a == b
        } catch (_: Exception) {
            // Unknown rather than mismatched - do not block the update on a
            // check that itself failed.
            true
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
