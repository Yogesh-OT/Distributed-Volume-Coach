package app.dvcoach.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedCard
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import app.dvcoach.data.Repository
import app.dvcoach.data.remote.ApiResult
import kotlinx.coroutines.launch

/** Debug builds only: point the app at your server and check it answers. */
@Composable
fun ServerAddressCard(repository: Repository) {
    val server = repository.server
    if (!server.isEditable) return

    var address by rememberSaveable { mutableStateOf(server.baseUrl().trimEnd('/')) }
    var status by remember { mutableStateOf<String?>(null) }
    var failed by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()

    OutlinedCard(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text("Server address (test builds only)", style = MaterialTheme.typography.titleSmall)
            Text(
                "Emulator: http://10.0.2.2:8000. Phone over USB with adb reverse: http://127.0.0.1:8000.",
                style = MaterialTheme.typography.bodySmall,
            )
            OutlinedTextField(
                value = address,
                onValueChange = { address = it },
                label = { Text("Address") },
                singleLine = true,
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Uri),
                modifier = Modifier.fillMaxWidth(),
            )
            Button(onClick = {
                val problem = server.set(address)
                if (problem != null) {
                    status = problem
                    failed = true
                } else {
                    status = "Checking…"
                    failed = false
                    scope.launch {
                        when (val result = repository.checkServer()) {
                            is ApiResult.Ok -> {
                                status = "Connected. The server is in ${result.value.authMode} mode."
                                failed = false
                            }
                            is ApiResult.Failed -> {
                                status = result.message
                                failed = true
                            }
                        }
                    }
                }
            }) { Text("Save and test") }
            status?.let {
                Text(
                    it,
                    style = MaterialTheme.typography.bodySmall,
                    color = if (failed) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.primary,
                )
            }
        }
    }
}
