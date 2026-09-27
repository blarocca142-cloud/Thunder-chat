package com.thunder.app.data

import android.content.Context

class ThunderPrefs(context: Context) {
    private val prefs = context.applicationContext.getSharedPreferences("thunder", Context.MODE_PRIVATE)

    var serverUrl: String
        get() = prefs.getString(KEY_SERVER, "").orEmpty()
        set(value) {
            prefs.edit().putString(KEY_SERVER, value.trim()).apply()
        }

    var darkMode: Boolean
        get() = prefs.getBoolean(KEY_DARK, false)
        set(value) {
            prefs.edit().putBoolean(KEY_DARK, value).apply()
        }

    var speakReplies: Boolean
        get() = prefs.getBoolean(KEY_SPEAK, false)
        set(value) {
            prefs.edit().putBoolean(KEY_SPEAK, value).apply()
        }

    /** Empty means use the phone's built-in TTS. */
    var voice: String
        get() = prefs.getString(KEY_VOICE, "us_male").orEmpty()
        set(value) {
            prefs.edit().putString(KEY_VOICE, value).apply()
        }

    /** Bearer token for Main. Empty until one is pasted in Settings. */
    var apiToken: String
        get() = prefs.getString(KEY_TOKEN, "").orEmpty()
        set(value) {
            prefs.edit().putString(KEY_TOKEN, value.trim()).apply()
        }

    /** Where the Odris admin dashboard lives. Odris is a separate machine with
     *  its own service, so this is not derived from the Main server URL. */
    var odrisUrl: String
        get() = prefs.getString(KEY_ODRIS_URL, "http://10.168.168.15:9005").orEmpty()
        set(value) {
            prefs.edit().putString(KEY_ODRIS_URL, value.trim()).apply()
        }

    /** The dashboard password, for the embedded dashboard to log itself in.
     *
     *  Odris is the one service on the fleet that actually authenticates, and
     *  that stays true - the alternative was proxying it through Main, whose own
     *  auth defaults to off, which would have put an admin dashboard that can
     *  deploy code on the LAN unauthenticated. Storing it here keeps the lock on
     *  the door and puts the key on Blayne's own phone.
     *
     *  Generated on Odris at ~/dashboard_password.txt. Delete that file to
     *  rotate it; the service writes a fresh one. */
    var odrisPassword: String
        get() = prefs.getString(KEY_ODRIS_PW, "").orEmpty()
        set(value) {
            prefs.edit().putString(KEY_ODRIS_PW, value.trim()).apply()
        }

    /** Fingerprint of the last digest shown, so the same finding does not
     *  notify twice. A phone that buzzes every six hours about one six-year-old
     *  disk is a phone with notifications switched off, and then the one that
     *  mattered goes unseen too. */
    var lastDigestSignature: String
        get() = prefs.getString(KEY_DIGEST_SIG, "").orEmpty()
        set(value) {
            prefs.edit().putString(KEY_DIGEST_SIG, value).apply()
        }

    companion object {
        private const val KEY_DIGEST_SIG = "last_digest_sig"
        private const val KEY_SERVER = "server_url"
        private const val KEY_DARK = "dark_mode"
        private const val KEY_SPEAK = "speak_replies"
        private const val KEY_VOICE = "voice"
        private const val KEY_TOKEN = "api_token"
        private const val KEY_ODRIS_URL = "odris_url"
        private const val KEY_ODRIS_PW = "odris_password"
    }
}
