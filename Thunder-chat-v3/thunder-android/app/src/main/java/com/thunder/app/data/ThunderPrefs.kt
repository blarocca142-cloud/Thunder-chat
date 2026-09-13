package com.thunder.app.data

import android.content.Context

class ThunderPrefs(context: Context) {
    private val prefs = context.applicationContext.getSharedPreferences("thunder", Context.MODE_PRIVATE)

    var serverUrl: String
        get() = prefs.getString(KEY_SERVER, "").orEmpty()
        set(value) {
            prefs.edit().putString(KEY_SERVER, value.trim()).apply()
        }

    companion object {
        private const val KEY_SERVER = "server_url"
    }
}
