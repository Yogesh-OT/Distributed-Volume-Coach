package app.dvcoach

import android.app.Application
import android.content.Context
import android.util.Log
import app.dvcoach.data.Repository
import app.dvcoach.data.ServerConfig
import app.dvcoach.data.auth.AuthTokenProvider
import app.dvcoach.data.auth.DevTokenProvider
import app.dvcoach.data.auth.FirebaseTokenProvider
import app.dvcoach.data.local.AppDatabase
import app.dvcoach.data.remote.Api
import app.dvcoach.reminders.Notifier
import app.dvcoach.reminders.PromptScheduler
import kotlinx.coroutines.CoroutineExceptionHandler
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob

class DvCoachApp : Application() {
    lateinit var container: AppContainer
        private set

    override fun onCreate() {
        super.onCreate()
        container = AppContainer(this)
        Notifier.createChannels(this)
    }
}

/** Hand-wired dependencies. Small enough that a DI framework would add more than it saves. */
class AppContainer(context: Context) {
    /** For work started by alarms and notification buttons, which outlives any screen. */
    val scope = CoroutineScope(
        SupervisorJob() + Dispatchers.IO + CoroutineExceptionHandler { _, e -> Log.e("DvCoach", "Background task failed", e) }
    )

    private val tokens: AuthTokenProvider =
        if (BuildConfig.AUTH_MODE == "firebase") FirebaseTokenProvider() else DevTokenProvider(context)

    private val server = ServerConfig(
        context,
        default = if (ServerConfig.isEmulator()) BuildConfig.API_BASE_URL else BuildConfig.DEVICE_API_BASE_URL,
        isEditable = BuildConfig.DEBUG,
    )

    val repository = Repository(
        context = context.applicationContext,
        db = AppDatabase.build(context),
        api = Api.create(server, tokens),
        scheduler = PromptScheduler(context.applicationContext),
        server = server,
    )
}
