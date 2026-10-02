package app.dvcoach.data

import android.content.Context
import okhttp3.HttpUrl.Companion.toHttpUrlOrNull

/**
 * Where the API lives. Debug builds let you change it in the app, because the right
 * address depends on the device: http://10.0.2.2:8000 on the emulator, http://127.0.0.1:8000
 * on a phone with `adb reverse`, or the computer's Wi-Fi address. Release builds always
 * use the address they were built with.
 */
class ServerConfig(context: Context, private val default: String, val isEditable: Boolean) {
    private val prefs = context.getSharedPreferences("server", Context.MODE_PRIVATE)

    fun baseUrl(): String = if (isEditable) prefs.getString(KEY, null) ?: default else default

    /** Saves [input] and returns null, or returns what's wrong with it. */
    fun set(input: String): String? {
        val trimmed = input.trim().trimEnd('/')
        val url = trimmed.toHttpUrlOrNull()
        if (url == null || url.scheme !in setOf("http", "https")) {
            return "Enter a full address, like http://127.0.0.1:8000"
        }
        prefs.edit().putString(KEY, "$trimmed/").apply()
        return null
    }

    private companion object {
        const val KEY = "base_url"
    }
}
