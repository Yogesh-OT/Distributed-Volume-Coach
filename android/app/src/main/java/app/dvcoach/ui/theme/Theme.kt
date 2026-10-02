package app.dvcoach.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

// Same palette as the architecture page: green for the phone, cobalt accents, red for hard/pain.
private val Light = lightColorScheme(
    primary = Color(0xFF1E7651),
    onPrimary = Color(0xFFFFFFFF),
    primaryContainer = Color(0xFFD3ECDF),
    onPrimaryContainer = Color(0xFF0B3B27),
    secondary = Color(0xFF2C4CC4),
    onSecondary = Color(0xFFFFFFFF),
    secondaryContainer = Color(0xFFE4E9F9),
    onSecondaryContainer = Color(0xFF16245E),
    background = Color(0xFFF3F5F4),
    onBackground = Color(0xFF16201C),
    surface = Color(0xFFF3F5F4),
    onSurface = Color(0xFF16201C),
    surfaceVariant = Color(0xFFE2E8E5),
    onSurfaceVariant = Color(0xFF56635E),
    error = Color(0xFFC0391F),
    errorContainer = Color(0xFFF8E2DC),
    onErrorContainer = Color(0xFF5C1708),
)

private val Dark = darkColorScheme(
    primary = Color(0xFF4FC08F),
    onPrimary = Color(0xFF00391F),
    primaryContainer = Color(0xFF14412C),
    onPrimaryContainer = Color(0xFFCDEEDC),
    secondary = Color(0xFF8AA3FF),
    onSecondary = Color(0xFF0E1B52),
    secondaryContainer = Color(0xFF19213B),
    onSecondaryContainer = Color(0xFFDDE3FF),
    background = Color(0xFF0E1412),
    onBackground = Color(0xFFE4EBE8),
    surface = Color(0xFF0E1412),
    onSurface = Color(0xFFE4EBE8),
    surfaceVariant = Color(0xFF26302C),
    onSurfaceVariant = Color(0xFF97A59F),
    error = Color(0xFFFF7D60),
    errorContainer = Color(0xFF3A1A12),
    onErrorContainer = Color(0xFFFFDAD1),
)

@Composable
fun DvCoachTheme(content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = if (isSystemInDarkTheme()) Dark else Light, content = content)
}
