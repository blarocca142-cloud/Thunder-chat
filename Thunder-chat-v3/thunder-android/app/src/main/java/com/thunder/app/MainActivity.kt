package com.thunder.app

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.os.SystemClock
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.biometric.BiometricManager
import androidx.biometric.BiometricManager.Authenticators.BIOMETRIC_WEAK
import androidx.biometric.BiometricManager.Authenticators.DEVICE_CREDENTIAL
import androidx.biometric.BiometricPrompt
import androidx.compose.foundation.layout.Box
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.fragment.app.FragmentActivity
import com.thunder.app.data.DigestWorker
import com.thunder.app.data.ThunderPrefs
import com.thunder.app.ui.LockScreen
import com.thunder.app.ui.ThunderRoot

// FragmentActivity rather than ComponentActivity: BiometricPrompt hosts its
// dialog in a fragment. It is a ComponentActivity underneath, so Compose is
// unaffected.
class MainActivity : FragmentActivity() {
    /** Set by the digest notification so the app opens on the finding that
     *  caused the buzz instead of on a chat that knows nothing about it. */
    private var openFleet = false

    private lateinit var prefs: ThunderPrefs
    private var locked by mutableStateOf(false)
    // The app underneath is not composed at all until the first unlock. After
    // that the lock covers it instead of replacing it, so relocking does not
    // throw away the conversation on screen.
    private var everUnlocked by mutableStateOf(false)
    private var lockMessage by mutableStateOf<String?>(null)
    private var leftAt = 0L
    private var prompting = false
    private var autoPrompted = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        prefs = ThunderPrefs(this)
        // Rotation and the notification's recreate() rebuild the activity; an
        // unlock from moments ago still counts. The time check stops a restore
        // after the process was killed hours later from skipping the lock.
        val unlockedAt = savedInstanceState?.getLong(KEY_UNLOCKED_AT, 0L) ?: 0L
        val stillUnlocked = unlockedAt > 0 && SystemClock.elapsedRealtime() - unlockedAt < RELOCK_MS
        locked = lockWanted() && !stillUnlocked
        everUnlocked = !locked
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
        setContent {
            Box {
                if (everUnlocked) ThunderRoot(startOnFleet = openFleet)
                if (locked) LockScreen(dark = prefs.darkMode, message = lockMessage, onUnlock = ::prompt)
            }
        }
    }

    override fun onStart() {
        super.onStart()
        // A minute of grace, so stepping out to pick a photo or answer a text
        // does not mean a fingerprint every time.
        if (!locked && lockWanted() && leftAt > 0 && SystemClock.elapsedRealtime() - leftAt > RELOCK_MS) {
            locked = true
            lockMessage = null
            autoPrompted = false
        }
    }

    override fun onResume() {
        super.onResume()
        if (locked && !autoPrompted) {
            autoPrompted = true
            prompt()
        }
    }

    override fun onSaveInstanceState(outState: Bundle) {
        super.onSaveInstanceState(outState)
        if (!locked) outState.putLong(KEY_UNLOCKED_AT, SystemClock.elapsedRealtime())
    }

    override fun onStop() {
        super.onStop()
        leftAt = SystemClock.elapsedRealtime()
    }

    /** Only lock when the phone can actually unlock it again. A phone with no
     *  screen lock set up at all would otherwise lock him out of his own app. */
    private fun lockWanted(): Boolean =
        prefs.fingerprintLock &&
            BiometricManager.from(this).canAuthenticate(AUTHENTICATORS) == BiometricManager.BIOMETRIC_SUCCESS

    private fun prompt() {
        if (prompting) return
        if (!lockWanted()) {
            // The fingerprint or screen lock was removed while the app was
            // locked; nothing can unlock it, so do not hold the app hostage.
            locked = false
            everUnlocked = true
            return
        }
        prompting = true
        val callback = object : BiometricPrompt.AuthenticationCallback() {
            override fun onAuthenticationSucceeded(result: BiometricPrompt.AuthenticationResult) {
                prompting = false
                locked = false
                everUnlocked = true
                lockMessage = null
            }

            override fun onAuthenticationError(errorCode: Int, errString: CharSequence) {
                prompting = false
                lockMessage = when (errorCode) {
                    BiometricPrompt.ERROR_USER_CANCELED,
                    BiometricPrompt.ERROR_NEGATIVE_BUTTON,
                    BiometricPrompt.ERROR_CANCELED -> null
                    else -> errString.toString()
                }
            }
            // A single bad read is not an error; the system prompt stays up and
            // says "not recognised" itself.
        }
        BiometricPrompt(this, ContextCompat.getMainExecutor(this), callback).authenticate(
            BiometricPrompt.PromptInfo.Builder()
                .setTitle("Unlock Thunder")
                .setSubtitle("Fingerprint, or your phone's PIN")
                .setAllowedAuthenticators(AUTHENTICATORS)
                .build()
        )
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

    private companion object {
        const val RELOCK_MS = 60_000L
        const val KEY_UNLOCKED_AT = "unlocked_at"
        // WEAK rather than STRONG: STRONG together with the PIN fallback is not
        // supported below Android 11. Without the PIN fallback, a cut finger
        // or a wet sensor would lock him out.
        const val AUTHENTICATORS = BIOMETRIC_WEAK or DEVICE_CREDENTIAL
    }
}
