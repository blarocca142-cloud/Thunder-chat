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

    companion object {
        private const val KEY_SERVER = "server_url"
        private const val KEY_DARK = "dark_mode"
    }
}
