package com.thunder.app

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.fragment.app.FragmentActivity
import com.thunder.app.data.DigestWorker
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import com.thunder.app.ui.ThunderRoot

// FragmentActivity rather than ComponentActivity: the Odris fingerprint
// prompt (BiometricPrompt) hosts its dialog in a fragment. It is a
// ComponentActivity underneath, so Compose is unaffected.
class MainActivity : FragmentActivity() {
    /** Set by the digest notification so the app opens on the finding that
     *  caused the buzz instead of on a chat that knows nothing about it. */
    private var openFleet = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        // Ask once. Declining is fine - the same findings are on the Fleet tab
        // either way, this only decides whether they come to him.
        if (Build.VERSION.SDK_INT >= 33 &&
            ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS)
            != PackageManager.PERMISSION_GRANTED
        ) {
            ActivityCompat.requestPermissions(
                this, arrayOf(Manifest.permission.POST_NOTIFICATIONS), 1)
        }
        DigestWorker.schedule(this)
        openFleet = intent?.getBooleanExtra(DigestWorker.EXTRA_OPEN_FLEET, false) == true
        setContent { ThunderRoot(startOnFleet = openFleet) }
    }

    /** The activity is singleTop, so a second tap on the notification arrives
     *  here rather than through onCreate. Without this the app would come to
     *  the front still showing whatever tab was last open. */
    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        if (intent.getBooleanExtra(DigestWorker.EXTRA_OPEN_FLEET, false)) {
            recreate()
        }
    }
}
