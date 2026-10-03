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
        // Upload anything waiting whenever the app is opened. The background sync job is the
        // main path, but some phones (Xiaomi without Autostart) won't start the app for it.
        val container = (application as DvCoachApp).container
        container.scope.launch { container.repository.syncNow() }
    }
}
