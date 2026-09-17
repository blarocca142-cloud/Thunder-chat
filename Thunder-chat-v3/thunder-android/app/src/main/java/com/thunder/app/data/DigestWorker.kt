package com.thunder.app.data

import android.Manifest
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import androidx.work.Constraints
import androidx.work.CoroutineWorker
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.NetworkType
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import com.thunder.app.MainActivity
import com.thunder.app.R
import org.json.JSONObject
import java.util.concurrent.TimeUnit

/**
 * Checks in with Thunder periodically and speaks up only when something needs
 * a person.
 *
 * Everything it reports already existed behind an endpoint nobody opens -
 * failing drives, claims waiting to be read, memory wanting approval. A system
 * that only answers when asked is one whose warnings arrive late.
 *
 * The restraint is the feature. It posts nothing when the fleet is fine, and it
 * will not repeat a notification for something already shown - a phone that
 * buzzes every hour about the same 6-year-old disk is a phone that gets its
 * notifications turned off, and then the real one goes unseen too.
 */
class DigestWorker(
    context: Context,
    params: WorkerParameters
) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result {
        val prefs = ThunderPrefs(applicationContext)
        val server = prefs.serverUrl
        if (server.isBlank()) return Result.success()

        val api = ThunderApi(token = prefs.apiToken)
        val digest = api.digest(server) ?: return Result.retry()

        if (digest.quiet || (digest.critical == 0 && digest.warning == 0)) {
            return Result.success()
        }

        // Only notify when the situation has actually changed. The headline of
        // the top item plus the counts is a good enough fingerprint: a new
        // problem changes it, the same problem sitting there does not.
        val signature = "${digest.critical}/${digest.warning}/${digest.topHeadline}"
        if (signature == prefs.lastDigestSignature) return Result.success()
        prefs.lastDigestSignature = signature

        notify(digest)
        return Result.success()
    }

    private fun notify(digest: Digest) {
        val ctx = applicationContext
        if (Build.VERSION.SDK_INT >= 33 &&
            ContextCompat.checkSelfPermission(ctx, Manifest.permission.POST_NOTIFICATIONS)
            != PackageManager.PERMISSION_GRANTED
        ) {
            return  // not granted; the app shows the same thing in Settings
        }

        val manager = ctx.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        if (Build.VERSION.SDK_INT >= 26) {
            manager.createNotificationChannel(
                NotificationChannel(
                    CHANNEL, "Thunder alerts",
                    // Default, not high: this is worth seeing, not worth
                    // interrupting a conversation for.
                    NotificationManager.IMPORTANCE_DEFAULT
                ).apply { description = "Hardware, claims and security findings" }
            )
        }

        val open = PendingIntent.getActivity(
            ctx, 0, Intent(ctx, MainActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        )

        val title = when {
            digest.critical > 0 -> "Thunder: ${digest.critical} needing attention"
            else -> "Thunder: ${digest.warning} to look at"
        }
        val body = digest.items.take(3).joinToString("\n") { "• $it" }

        NotificationManagerCompat.from(ctx).notify(
            NOTIFICATION_ID,
            NotificationCompat.Builder(ctx, CHANNEL)
                .setSmallIcon(R.mipmap.ic_launcher)
                .setContentTitle(title)
                .setContentText(digest.items.firstOrNull() ?: "")
                .setStyle(NotificationCompat.BigTextStyle().bigText(body))
                .setPriority(NotificationCompat.PRIORITY_DEFAULT)
                .setAutoCancel(true)
                .setContentIntent(open)
                .build()
        )
    }

    companion object {
        private const val CHANNEL = "thunder_digest"
        private const val NOTIFICATION_ID = 4101
        private const val WORK = "thunder_digest_check"

        /**
         * Every six hours, and only on a network. Not hourly: nothing in the
         * digest changes that fast, and a background job that wakes the radio
         * twenty-four times a day to usually find nothing is a battery
         * complaint waiting to happen.
         */
        fun schedule(context: Context) {
            val work = PeriodicWorkRequestBuilder<DigestWorker>(6, TimeUnit.HOURS)
                .setConstraints(
                    Constraints.Builder()
                        .setRequiredNetworkType(NetworkType.CONNECTED)
                        .build()
                )
                .build()
            WorkManager.getInstance(context).enqueueUniquePeriodicWork(
                WORK, ExistingPeriodicWorkPolicy.KEEP, work
            )
        }
    }
}

/** What Thunder would say if asked "anything I should know?" */
data class Digest(
    val quiet: Boolean,
    val critical: Int,
    val warning: Int,
    val spoken: String,
    val items: List<String>,
    val details: List<DigestItem>
) {
    val topHeadline: String get() = items.firstOrNull().orEmpty()
}

data class DigestItem(
    val kind: String,
    val headline: String,
    val detail: String,
    val action: String,
    val severity: String
)

fun parseDigest(o: JSONObject): Digest {
    val details = mutableListOf<DigestItem>()
    val arr = o.optJSONArray("items")
    for (i in 0 until (arr?.length() ?: 0)) {
        val it = arr!!.getJSONObject(i)
        details.add(
            DigestItem(
                kind = it.optString("kind"),
                headline = it.optString("headline"),
                detail = it.optString("detail"),
                action = it.optString("action"),
                severity = it.optString("severity", "info")
            )
        )
    }
    return Digest(
        quiet = o.optBoolean("quiet", false),
        critical = o.optInt("critical"),
        warning = o.optInt("warning"),
        spoken = o.optString("spoken"),
        items = details.map { it.headline },
        details = details
    )
}
