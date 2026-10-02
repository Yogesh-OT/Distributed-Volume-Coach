package app.dvcoach.data.auth

import android.content.Context
import com.google.firebase.auth.FirebaseAuth
import kotlinx.coroutines.tasks.await
import java.util.UUID

interface AuthTokenProvider {
    suspend fun token(): String
}

/** Debug builds: a random id kept on this phone. Only accepted by a server running DVC_AUTH_MODE=dev. */
class DevTokenProvider(context: Context) : AuthTokenProvider {
    private val prefs = context.getSharedPreferences("auth", Context.MODE_PRIVATE)

    override suspend fun token(): String {
        val id = prefs.getString(KEY, null) ?: UUID.randomUUID().toString().also {
            prefs.edit().putString(KEY, it).apply()
        }
        return "dev:$id"
    }

    private companion object {
        const val KEY = "dev_id"
    }
}

/**
 * Release builds: Firebase anonymous sign-in, so there's no sign-up screen in the MVP.
 * Linking to a Google account later keeps the same uid. Needs app/google-services.json.
 */
class FirebaseTokenProvider : AuthTokenProvider {
    override suspend fun token(): String {
        val auth = FirebaseAuth.getInstance()
        val user = auth.currentUser ?: auth.signInAnonymously().await().user
            ?: error("Anonymous sign-in returned no user")
        return user.getIdToken(false).await().token ?: error("Firebase returned no ID token")
    }
}
