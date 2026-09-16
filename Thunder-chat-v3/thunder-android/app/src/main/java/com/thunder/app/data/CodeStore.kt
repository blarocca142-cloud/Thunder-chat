package com.thunder.app.data

import android.content.ContentValues
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import androidx.core.content.FileProvider
import java.io.File

/**
 * Getting code off the phone.
 *
 * Code lives on Main - this is only the last hop onto the device. Two routes,
 * because they are used for different things: **save** drops the file in
 * Downloads where a file manager or a laptop on the same cable will find it,
 * and **share** hands it to whatever app is open next.
 *
 * Mirrors [CreationStore]'s handling of stills rather than inventing a second
 * way of doing the same job.
 */
class CodeStore(private val app: Context) {

    /** Downloads/Thunder/<name>. Returns false rather than throwing. */
    fun saveToDownloads(bytes: ByteArray, name: String, mime: String = "text/plain"): Boolean {
        val display = name.ifBlank { "thunder.txt" }
        return try {
            if (Build.VERSION.SDK_INT >= 29) {
                val values = ContentValues().apply {
                    put(MediaStore.MediaColumns.DISPLAY_NAME, display)
                    put(MediaStore.MediaColumns.MIME_TYPE, mime)
                    put(
                        MediaStore.MediaColumns.RELATIVE_PATH,
                        Environment.DIRECTORY_DOWNLOADS + "/Thunder"
                    )
                }
                val uri: Uri = app.contentResolver.insert(
                    MediaStore.Downloads.EXTERNAL_CONTENT_URI, values
                ) ?: return false
                app.contentResolver.openOutputStream(uri)?.use { it.write(bytes) } ?: return false
                true
            } else {
                // Before scoped storage, writing to the public Downloads folder
                // needs a runtime permission this app does not ask for. The
                // app-specific directory needs none and is still reachable over
                // USB, which is the better trade for a phone this old.
                val dir = File(
                    app.getExternalFilesDir(Environment.DIRECTORY_DOWNLOADS), "Thunder"
                ).apply { mkdirs() }
                File(dir, display).writeBytes(bytes)
                true
            }
        } catch (_: Exception) {
            false
        }
    }

    fun share(bytes: ByteArray, name: String, mime: String = "text/plain") {
        val dir = File(app.cacheDir, "share").apply { mkdirs() }
        val out = File(dir, name.ifBlank { "thunder.txt" })
        out.writeBytes(bytes)
        val uri = FileProvider.getUriForFile(app, "${app.packageName}.files", out)
        val intent = Intent(Intent.ACTION_SEND).apply {
            type = mime
            putExtra(Intent.EXTRA_STREAM, uri)
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_ACTIVITY_NEW_TASK)
        }
        app.startActivity(
            Intent.createChooser(intent, "Send $name")
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        )
    }

    /** Where a saved file ended up, for telling the user something true. */
    fun savedLocation(): String =
        if (Build.VERSION.SDK_INT >= 29) "Downloads/Thunder"
        else "Android/data/${app.packageName}/files/Download/Thunder"
}
