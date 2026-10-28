package com.mcqs.app.ui

import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExtendedFloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.compose.LifecycleEventEffect
import com.mcqs.app.data.DeckSummary
import com.mcqs.app.data.Repository
import com.mcqs.app.pkg.InvalidPackageException
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HomeScreen(repo: Repository, onStudy: (String) -> Unit, onScenes: (String) -> Unit) {
    var now by remember { mutableLongStateOf(System.currentTimeMillis()) }
    LifecycleEventEffect(Lifecycle.Event.ON_RESUME) { now = System.currentTimeMillis() }
    val decks by remember(now) { repo.dao.deckSummaries(now) }.collectAsState(initial = emptyList())

    val scope = rememberCoroutineScope()
    val snackbar = remember { SnackbarHostState() }
    var importing by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }
    var confirmDelete by remember { mutableStateOf<DeckSummary?>(null) }

    LaunchedEffect(Unit) { repo.cleanOrphanDirs() }

    val picker = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri: Uri? ->
        if (uri == null) return@rememberLauncherForActivityResult
        importing = true
        scope.launch {
            try {
                val m = repo.importZip(uri)
                now = System.currentTimeMillis()
                snackbar.showSnackbar("Imported \"${m.title}\" v${m.version}: ${m.cards.size} cards, ${m.scenes.size} scenes")
            } catch (e: InvalidPackageException) {
                error = e.message
            } catch (e: Exception) {
                error = "Import failed: ${e.message}"
            } finally {
                importing = false
            }
        }
    }

    Scaffold(
        topBar = { TopAppBar(title = { Text("MCQs") }) },
        snackbarHost = { SnackbarHost(snackbar) },
        floatingActionButton = {
            ExtendedFloatingActionButton(
                onClick = { if (!importing) picker.launch(arrayOf("application/zip", "application/x-zip-compressed", "application/octet-stream")) },
                icon = { Icon(Icons.Filled.Add, null) },
                text = { Text("Import zip") },
            )
        },
    ) { padding ->
        Column(Modifier.padding(padding).fillMaxSize()) {
            if (importing) LinearProgressIndicator(Modifier.fillMaxWidth())
            if (decks.isEmpty()) {
                Column(Modifier.fillMaxSize().padding(32.dp), verticalArrangement = Arrangement.Center,
                    horizontalAlignment = Alignment.CenterHorizontally) {
                    Text("No decks yet", style = MaterialTheme.typography.headlineSmall)
                    Spacer(Modifier.padding(4.dp))
                    Text("Tap \"Import zip\" and choose a content package (manifest.json + media).")
                }
            } else {
                LazyColumn(contentPadding = PaddingValues(16.dp, 16.dp, 16.dp, 96.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    items(decks, key = { it.id }) { d ->
                        DeckCard(d, onStudy = { onStudy(d.id) }, onScenes = { onScenes(d.id) },
                            onDelete = { confirmDelete = d })
                    }
                }
            }
        }
    }

    error?.let {
        AlertDialog(
            onDismissRequest = { error = null },
            confirmButton = { TextButton(onClick = { error = null }) { Text("OK") } },
            title = { Text("Could not import") },
            text = { Text(it) },
        )
    }
    confirmDelete?.let { d ->
        AlertDialog(
            onDismissRequest = { confirmDelete = null },
            confirmButton = {
                TextButton(onClick = {
                    confirmDelete = null
                    scope.launch { repo.deleteDeck(d.id) }
                }) { Text("Delete") }
            },
            dismissButton = { TextButton(onClick = { confirmDelete = null }) { Text("Cancel") } },
            title = { Text("Delete \"${d.title}\"?") },
            text = { Text("This removes the deck, its media and all review history.") },
        )
    }
}

@Composable
private fun DeckCard(d: DeckSummary, onStudy: () -> Unit, onScenes: () -> Unit, onDelete: () -> Unit) {
    Card(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f)) {
                    Text(d.title, style = MaterialTheme.typography.titleMedium)
                    Text("v${d.version} · ${d.total} cards · ${d.scenes} scenes",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
                IconButton(onClick = onDelete) { Icon(Icons.Filled.Delete, "Delete deck") }
            }
            Text("Due: ${d.due}   New: ${d.unseen}", style = MaterialTheme.typography.bodyMedium)
            Row(Modifier.padding(top = 8.dp)) {
                Button(onClick = onStudy) { Text("Study") }
                if (d.scenes > 0) {
                    Spacer(Modifier.width(8.dp))
                    OutlinedButton(onClick = onScenes) { Text("Scenes") }
                }
            }
        }
    }
}
