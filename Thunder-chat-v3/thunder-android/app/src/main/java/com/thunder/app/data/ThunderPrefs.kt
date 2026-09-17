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
    }
}
