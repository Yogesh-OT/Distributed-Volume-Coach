package app.dvcoach

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import app.dvcoach.ui.AppRoot
import app.dvcoach.ui.theme.DvCoachTheme

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
}
