package com.thunder.app.ui

import android.content.Context
import android.content.ContextWrapper
import android.os.SystemClock
import androidx.biometric.BiometricManager
import androidx.biometric.BiometricManager.Authenticators.BIOMETRIC_WEAK
import androidx.biometric.BiometricManager.Authenticators.DEVICE_CREDENTIAL
import androidx.biometric.BiometricPrompt
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.core.content.ContextCompat
import androidx.fragment.app.FragmentActivity
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner

// WEAK rather than STRONG: STRONG together with the PIN fallback is not
// supported below Android 11. Without the PIN fallback, a cut finger or a wet
// sensor would lock him out of his own admin dashboard.
private const val AUTHENTICATORS = BIOMETRIC_WEAK or DEVICE_CREDENTIAL
private const val RELOCK_MS = 60_000L

/**
 * Whether the Odris tab is unlocked. Held above the tab so switching to Chat
 * and back does not ask again; a minute with the app in the background does.
 */
class OdrisLockState {
    var unlocked by mutableStateOf(false)
    var message by mutableStateOf<String?>(null)
    internal var leftAt = 0L
    internal var prompting = false
    internal var autoPrompted = false
}

@Composable
fun rememberOdrisLock(): OdrisLockState {
    val state = remember { OdrisLockState() }
    val owner = LocalLifecycleOwner.current
    DisposableEffect(owner) {
        val observer = LifecycleEventObserver { _, event ->
            when (event) {
                Lifecycle.Event.ON_STOP -> state.leftAt = SystemClock.elapsedRealtime()
                Lifecycle.Event.ON_START ->
                    if (state.leftAt > 0 && SystemClock.elapsedRealtime() - state.leftAt > RELOCK_MS) {
                        state.unlocked = false
                        state.message = null
                        state.autoPrompted = false
                    }
                else -> Unit
            }
        }
        owner.lifecycle.addObserver(observer)
        onDispose { owner.lifecycle.removeObserver(observer) }
    }
    return state
}

/** Only lock when the phone can unlock it again. A phone with no screen lock
 *  set up at all would otherwise shut him out of Odris for good. */
fun canLock(context: Context): Boolean =
    BiometricManager.from(context).canAuthenticate(AUTHENTICATORS) == BiometricManager.BIOMETRIC_SUCCESS

/**
 * Shows [content] (the Odris tab) only after a fingerprint or the phone's PIN.
 * The dashboard it guards can deploy code to the fleet.
 */
@Composable
fun OdrisGate(
    enabled: Boolean,
    state: OdrisLockState,
    modifier: Modifier = Modifier,
    content: @Composable () -> Unit
) {
    val context = LocalContext.current
    val activity = remember(context) { context.findFragmentActivity() }
    if (!enabled || state.unlocked || activity == null || !canLock(context)) {
        content()
        return
    }
    val prompt = { unlock(activity, state) }
    LaunchedEffect(state.unlocked, state.autoPrompted) {
        if (!state.unlocked && !state.autoPrompted) {
            state.autoPrompted = true
            prompt()
        }
    }
    LockScreen(
        title = "Odris is locked",
        message = state.message,
        onUnlock = prompt,
        modifier = modifier
    )
}

private fun unlock(activity: FragmentActivity, state: OdrisLockState) {
    if (state.prompting) return
    state.prompting = true
    val callback = object : BiometricPrompt.AuthenticationCallback() {
        override fun onAuthenticationSucceeded(result: BiometricPrompt.AuthenticationResult) {
            state.prompting = false
            state.unlocked = true
            state.message = null
        }

        override fun onAuthenticationError(errorCode: Int, errString: CharSequence) {
            state.prompting = false
            state.message = when (errorCode) {
                BiometricPrompt.ERROR_USER_CANCELED,
                BiometricPrompt.ERROR_NEGATIVE_BUTTON,
                BiometricPrompt.ERROR_CANCELED -> null
                else -> errString.toString()
            }
        }
        // A single bad read is not an error; the system prompt stays up and
        // says "not recognised" itself.
    }
    BiometricPrompt(activity, ContextCompat.getMainExecutor(activity), callback).authenticate(
        BiometricPrompt.PromptInfo.Builder()
            .setTitle("Unlock Odris")
            .setSubtitle("Fingerprint, or your phone's PIN")
            .setAllowedAuthenticators(AUTHENTICATORS)
            .build()
    )
}

private tailrec fun Context.findFragmentActivity(): FragmentActivity? = when (this) {
    is FragmentActivity -> this
    is ContextWrapper -> baseContext.findFragmentActivity()
    else -> null
}
