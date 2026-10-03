package app.dvcoach

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import app.dvcoach.ui.AppRoot
import app.dvcoach.ui.theme.DvCoachTheme
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        val repository = (application as DvCoachApp).container.repository
        setContent {
            DvCoachTheme {
                AppRoot(repository)
            }
        }
    }

    override fun onResume() {
        super.onResume()
        val container = (application as DvCoachApp).container
        container.scope.launch {
            // Android drops an app's alarms when it's force-stopped or reinstalled, so put
            // today's set reminders and the check-in reminder back each time the app opens.
            container.repository.rescheduleAll()
            // The background sync job is the main path, but some phones (Xiaomi without
            // Autostart) won't start the app for it, so also upload anything waiting now.
            container.repository.syncNow()
        }
    }
}
