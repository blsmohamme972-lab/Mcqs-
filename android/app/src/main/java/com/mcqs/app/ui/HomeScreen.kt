package com.mcqs.app.ui

import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.compose.LifecycleEventEffect
import com.mcqs.app.BuildConfig
import com.mcqs.app.data.DeckSummary
import com.mcqs.app.data.NotPublishedException
import com.mcqs.app.data.RemoteApp
import com.mcqs.app.data.Repository
import com.mcqs.app.data.Sync
import com.mcqs.app.pkg.InvalidPackageException
import kotlinx.coroutines.launch

/** Process-wide sync state so tab switches don't re-sync; [SYNC_EVERY_MS] throttles automatic runs. */
private object SyncState {
    var lastRun = 0L
    var status by mutableStateOf<String?>(null)
    var appUpdate by mutableStateOf<RemoteApp?>(null)
    var running by mutableStateOf(false)
}

private const val SYNC_EVERY_MS = 2 * 60_000L

@Composable
fun HomeScreen(repo: Repository, sync: Sync, onStudy: (String) -> Unit, onScenes: (String) -> Unit) {
    var now by remember { mutableLongStateOf(System.currentTimeMillis()) }
    val decks by remember(now) { repo.dao.deckSummaries(now) }.collectAsState(initial = emptyList())

    val scope = rememberCoroutineScope()
    val snackbar = remember { SnackbarHostState() }
    var importing by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }
    var confirmDelete by remember { mutableStateOf<DeckSummary?>(null) }

    fun runSync(force: Boolean) {
        if (!Sync.enabled || SyncState.running) return
        if (!force && System.currentTimeMillis() - SyncState.lastRun < SYNC_EVERY_MS) return
        SyncState.running = true
        scope.launch {
            try {
                val result = sync.run()
                SyncState.appUpdate = result.appUpdate
                SyncState.status = if (result.updated.isEmpty()) "Up to date" else "Updated: ${result.updated.joinToString()}"
                now = System.currentTimeMillis()
            } catch (e: NotPublishedException) {
                SyncState.status = "Nothing published yet"
            } catch (e: Exception) {
                SyncState.status = "Offline — using saved content"
            } finally {
                SyncState.lastRun = System.currentTimeMillis()
                SyncState.running = false
            }
        }
    }

    LifecycleEventEffect(Lifecycle.Event.ON_RESUME) {
        now = System.currentTimeMillis()
        runSync(force = false)
    }

    val picker = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri: Uri? ->
        if (uri == null) return@rememberLauncherForActivityResult
        importing = true
        scope.launch {
            try {
                val m = repo.importZip(uri)
                now = System.currentTimeMillis()
                snackbar.showSnackbar("Imported \"${m.title}\" v${m.version}: ${m.cards.size} cards")
            } catch (e: InvalidPackageException) {
                error = e.message
            } catch (e: Exception) {
                error = "Import failed: ${e.message}"
            } finally {
                importing = false
            }
        }
    }

    Box(Modifier.fillMaxSize()) {
        LazyColumn(
            Modifier.fillMaxSize(),
            contentPadding = PaddingValues(start = 20.dp, end = 20.dp, bottom = 32.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            item {
                Row(Modifier.statusBarsPadding().padding(top = 16.dp), verticalAlignment = Alignment.CenterVertically) {
                    Column(Modifier.weight(1f)) {
                        Text("MCQs", style = MaterialTheme.typography.headlineLarge.brand())
                        Text(
                            SyncState.status ?: "v${BuildConfig.VERSION_NAME}",
                            style = MaterialTheme.typography.bodySmall, color = TextLo,
                        )
                    }
                    IconButton(onClick = { runSync(force = true) }) { Icon(Icons.Filled.Refresh, "Check for updates", tint = TextHi) }
                    IconButton(onClick = {
                        if (!importing) picker.launch(arrayOf("application/zip", "application/x-zip-compressed", "application/octet-stream"))
                    }) { Icon(Icons.Filled.Add, "Import zip", tint = TextHi) }
                }
                if (importing || SyncState.running) LinearProgressIndicator(Modifier.fillMaxWidth().padding(top = 8.dp))
            }
            SyncState.appUpdate?.let { app ->
                item { UpdateBanner(app) { scope.launch { runCatching { sync.installApp(app) }.onFailure { error = "Update failed: ${it.message}" } } } }
            }
            if (decks.isEmpty()) {
                item {
                    Column(Modifier.fillMaxWidth().padding(top = 80.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                        Text("No decks yet", style = MaterialTheme.typography.headlineSmall)
                        Spacer(Modifier.height(6.dp))
                        Text("Content arrives automatically when published,\nor tap + to import a zip.", color = TextLo)
                    }
                }
            }
            items(decks, key = { it.id }) { d ->
                DeckCard(d, onStudy = { onStudy(d.id) }, onScenes = { onScenes(d.id) }, onDelete = { confirmDelete = d })
            }
        }
        SnackbarHost(snackbar, Modifier.align(Alignment.BottomCenter))
    }

    error?.let {
        AlertDialog(
            onDismissRequest = { error = null },
            confirmButton = { TextButton(onClick = { error = null }) { Text("OK") } },
            title = { Text("Something went wrong") },
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
private fun UpdateBanner(app: RemoteApp, onUpdate: () -> Unit) {
    Row(
        Modifier.fillMaxWidth().clip(RoundedCornerShape(20.dp)).background(BrandGradient).padding(16.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(Modifier.weight(1f)) {
            Text("New version ${app.versionName}", style = MaterialTheme.typography.titleMedium, color = Color.White)
            Text("Tap update, then confirm install", style = MaterialTheme.typography.bodySmall, color = Color.White.copy(alpha = 0.85f))
        }
        Text(
            "Update",
            style = MaterialTheme.typography.labelLarge, color = Ink,
            modifier = Modifier.clip(RoundedCornerShape(50)).background(Color.White)
                .clickable(onClick = onUpdate).padding(horizontal = 16.dp, vertical = 8.dp),
        )
    }
}

@Composable
private fun DeckCard(d: DeckSummary, onStudy: () -> Unit, onScenes: () -> Unit, onDelete: () -> Unit) {
    Column(
        Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(24.dp))
            .background(Panel)
            .border(1.dp, Line, RoundedCornerShape(24.dp))
            .padding(18.dp)
    ) {
        Row(verticalAlignment = Alignment.Top) {
            Column(Modifier.weight(1f)) {
                Text(d.title, style = MaterialTheme.typography.titleLarge)
                Text("v${d.version} · ${d.total} cards · ${d.scenes} scenes",
                    style = MaterialTheme.typography.bodySmall, color = TextLo)
            }
            IconButton(onClick = onDelete) { Icon(Icons.Filled.Delete, "Delete deck", tint = TextLo) }
        }
        Row(Modifier.padding(top = 10.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Stat("${d.due}", "due", Pink)
            Stat("${d.unseen}", "new", Cyan)
        }
        Row(Modifier.padding(top = 14.dp), verticalAlignment = Alignment.CenterVertically) {
            GradientButton(onClick = onStudy) { Text("Study", style = MaterialTheme.typography.labelLarge, color = Color.White) }
            if (d.scenes > 0) {
                Spacer(Modifier.width(10.dp))
                GradientButton(onClick = onScenes, brush = androidx.compose.ui.graphics.SolidColor(Panel2)) {
                    Text("Scenes", style = MaterialTheme.typography.labelLarge, color = TextHi)
                }
            }
        }
    }
}

@Composable
private fun Stat(value: String, label: String, color: Color) {
    Row(
        Modifier.clip(RoundedCornerShape(50)).background(color.copy(alpha = 0.14f)).padding(horizontal = 12.dp, vertical = 5.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(value, style = MaterialTheme.typography.labelLarge, color = color)
        Text(" $label", style = MaterialTheme.typography.labelMedium, color = color.copy(alpha = 0.8f))
    }
}
