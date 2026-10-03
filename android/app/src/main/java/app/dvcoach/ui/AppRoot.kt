package app.dvcoach.ui

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.DateRange
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Person
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.navigation.NavDestination.Companion.hierarchy
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import app.dvcoach.data.Repository
import app.dvcoach.data.local.LocalProfile
import kotlinx.coroutines.flow.map

private sealed interface RootState {
    data object Loading : RootState
    data object NeedsOnboarding : RootState
    data object NeedsMaxTest : RootState
    data object Ready : RootState
}

/** Onboarding, then the first max test, then the main app. Driven by the saved profile. */
@Composable
fun AppRoot(repository: Repository) {
    val state by remember(repository) {
        repository.profile.map<LocalProfile?, RootState> { profile ->
            when {
                profile == null -> RootState.NeedsOnboarding
                profile.maxReps == null -> RootState.NeedsMaxTest
                else -> RootState.Ready
            }
        }
    }.collectAsStateWithLifecycle(initialValue = RootState.Loading)

    Surface(modifier = Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
        when (state) {
            RootState.Loading -> Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                CircularProgressIndicator()
            }
            RootState.NeedsOnboarding -> OnboardingScreen(repository, Modifier.safeDrawingPadding())
            RootState.NeedsMaxTest -> MaxTestScreen(repository, Modifier.safeDrawingPadding())
            RootState.Ready -> MainScaffold(repository)
        }
    }
}

private enum class Tab(val route: String, val label: String, val icon: ImageVector) {
    TODAY("today", "Today", Icons.Filled.Home),
    PROGRESS("progress", "Progress", Icons.Filled.DateRange),
    BODY("body", "Body", Icons.Filled.Person),
}

@Composable
private fun MainScaffold(repository: Repository) {
    val nav = rememberNavController()
    val backStack by nav.currentBackStackEntryAsState()
    val destination = backStack?.destination

    Scaffold(
        bottomBar = {
            NavigationBar {
                Tab.entries.forEach { tab ->
                    NavigationBarItem(
                        selected = destination?.hierarchy?.any { it.route == tab.route } == true,
                        onClick = {
                            nav.navigate(tab.route) {
                                popUpTo(nav.graph.findStartDestination().id) { saveState = true }
                                launchSingleTop = true
                                restoreState = true
                            }
                        },
                        icon = { Icon(tab.icon, contentDescription = null) },
                        label = { Text(tab.label) },
                    )
                }
            }
        },
    ) { padding ->
        NavHost(navController = nav, startDestination = Tab.TODAY.route, modifier = Modifier.padding(padding)) {
            composable(Tab.TODAY.route) {
                TodayScreen(
                    repository,
                    onCheckIn = { nav.navigate("checkin") },
                    onEditSchedule = { nav.navigate("schedule") },
                )
            }
            composable("checkin") { CheckInScreen(repository, onDone = { nav.popBackStack() }) }
            composable("schedule") { ScheduleScreen(repository, onDone = { nav.popBackStack() }) }
            composable(Tab.PROGRESS.route) { ProgressScreen(repository, onRetest = { nav.navigate("maxtest") }) }
            composable("maxtest") { MaxTestScreen(repository, onDone = { nav.popBackStack() }) }
            composable(Tab.BODY.route) { BodyScreen(repository) }
        }
    }
}
