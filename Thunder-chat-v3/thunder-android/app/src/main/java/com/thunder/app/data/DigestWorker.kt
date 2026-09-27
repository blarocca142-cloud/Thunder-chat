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
import java.util.concurrent.TimeUnit

/**
 * Checks in with Thunder periodically and speaks up only when something needs
 * a person.
 *
 * The restraint is the feature. It posts nothing when the fleet is fine, and it
 * will not repeat a notification for something already dealt with - a phone that
 * buzzes every six hours about the same 6-year-old disk is a phone that gets its
 * notifications turned off, and then the real one goes unseen too.
 *
 * **It used to ignore acknowledgement entirely, which made "mark as read" a lie.**
 * This worker read `/digest`, which is computed fresh from live readings and knows
 * nothing about what has already been seen. So marking the serverus drive as read
 * silenced nothing: six hours later the same finding came back, because from the
 * digest's point of view the drive was still six years old. It was.
 *
 * So the decision now comes from `/alerts`, which persists acknowledgement, and
 * only *unacknowledged* findings are allowed to buzz. `/digest` is still called
 * first, because building the digest is what records new findings into that
 * history in the first place - the two calls are refresh, then decide.
 *
 * A finding that is acknowledged and then goes away and comes back is
 * un-acknowledged again server-side, so genuinely new trouble still gets through.
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

        // Refresh first: building the digest is what folds new findings into the
        // persistent history. Skipping this would mean deciding from a stale list.
        if (!api.refreshFindings(server)) return Result.retry()

        val active = api.alerts(server, includeResolved = false)
        val unacked = active.filter { !it.acknowledged }
        if (unacked.isEmpty()) {
            // Nothing outstanding. Clear anything still sitting in the shade, so
            // the phone agrees with the app rather than contradicting it.
            clear(applicationContext)
            prefs.lastDigestSignature = ""
            return Result.success()
        }

        // Fingerprint the outstanding findings themselves, not a count and a
        // headline. Ids are stable across a reworded headline and a changed
        // count, so the same situation cannot re-notify, and a genuinely new
        // finding always can.
        val signature = unacked.sortedBy { it.id }
            .joinToString(",") { it.id + ":" + it.severity }
        if (signature == prefs.lastDigestSignature) return Result.success()
        prefs.lastDigestSignature = signature

        notify(unacked)
        return Result.success()
    }

    private fun notify(items: List<FleetAlert>) {
        val ctx = applicationContext
        if (Build.VERSION.SDK_INT >= 33 &&
            ContextCompat.checkSelfPermission(ctx, Manifest.permission.POST_NOTIFICATIONS)
            != PackageManager.PERMISSION_GRANTED
        ) {
            return  // not granted; the Odris tab shows the same findings anyway
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

        // The extra is what gives the notification somewhere to land. It used to
        // open a bare MainActivity, which is chat - and chat had never been told
        // the digest existed, so tapping it looked like Thunder making things up.
        val open = PendingIntent.getActivity(
            ctx, 0,
            Intent(ctx, MainActivity::class.java)
                .putExtra(EXTRA_OPEN_FLEET, true)
                .addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        )

        val critical = items.count { it.severity == "critical" }
        val title = when {
            critical > 0 -> "Thunder: $critical needing attention"
            items.size == 1 -> "Thunder: 1 to look at"
            else -> "Thunder: ${items.size} to look at"
        }
        val body = items.take(3).joinToString("\n") { "• ${it.headline}" }

        NotificationManagerCompat.from(ctx).notify(
            NOTIFICATION_ID,
            NotificationCompat.Builder(ctx, CHANNEL)
                .setSmallIcon(R.mipmap.ic_launcher)
                .setContentTitle(title)
                .setContentText(items.first().headline)
                .setStyle(NotificationCompat.BigTextStyle().bigText(body))
                .setPriority(NotificationCompat.PRIORITY_DEFAULT)
                .setAutoCancel(true)
                .setContentIntent(open)
                .build()
        )
    }

    companion object {
        /** Tells MainActivity to open the Odris tab on its alerts. */
        const val EXTRA_OPEN_FLEET = "com.thunder.app.OPEN_FLEET"

        private const val CHANNEL = "thunder_digest"
        private const val NOTIFICATION_ID = 4101
        private const val WORK = "thunder_digest_check"

        /**
         * Take the notification out of the shade.
         *
         * Called when the alerts are actually looked at, and when nothing is
         * outstanding. Without this, marking a finding as read inside the app
         * left the notification sitting in the shade saying the opposite - which
         * is exactly as untrustworthy as the original bug, just quieter.
         */
        fun clear(context: Context) {
            NotificationManagerCompat.from(context).cancel(NOTIFICATION_ID)
        }

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
