package com.mcqs.app.ui

import android.net.Uri
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.ui.draw.clip
import androidx.compose.ui.input.pointer.pointerInput
import com.mcqs.app.pkg.LectureDef
import com.mcqs.app.pkg.LectureTimeline
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.Card
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.produceState
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.media3.common.MediaItem
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.ui.PlayerView
import com.mcqs.app.data.DeckEntity
import com.mcqs.app.data.Repository
import com.mcqs.app.data.SceneEntity
import com.mcqs.app.pkg.RegionDef
import com.mcqs.app.pkg.manifestJson
import kotlinx.serialization.builtins.ListSerializer
import java.io.File

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ScenesScreen(repo: Repository, deckId: String, onBack: () -> Unit, onOpen: (String) -> Unit) {
    val data by produceState<Pair<DeckEntity?, List<SceneEntity>>>(null to emptyList(), deckId) {
        value = repo.dao.deck(deckId) to repo.dao.scenes(deckId)
    }
    val (deck, scenes) = data
    Scaffold(topBar = {
        TopAppBar(
            title = { Text("Scenes · ${deck?.title ?: ""}", maxLines = 1) },
            navigationIcon = { IconButton(onClick = onBack) { Icon(Icons.AutoMirrored.Filled.ArrowBack, "Back") } },
        )
    }) { padding ->
        LazyColumn(Modifier.padding(padding), contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)) {
            items(scenes, key = { it.id }) { s ->
                Card(Modifier.fillMaxWidth().clickable { onOpen(s.id) }) {
                    Row(Modifier.padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
                        val thumb = rememberBitmap(deck?.let { d -> s.image?.let { File(d.dir, it) } }, maxDim = 384)
                        if (thumb != null) {
                            Image(thumb, null, Modifier.width(120.dp).aspectRatio(16 / 9f), contentScale = ContentScale.Crop)
                            Box(Modifier.width(12.dp))
                        }
                        Column(Modifier.weight(1f)) {
                            Text(s.title, style = MaterialTheme.typography.titleMedium)
                            val meta = listOfNotNull(if (s.lectureJson != null) "▶ lecture" else if (s.video != null) "▶ video" else null, s.source).joinToString(" · ")
                            if (meta.isNotEmpty()) Text(meta, style = MaterialTheme.typography.bodySmall)
                        }
                    }
                }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SceneDetailScreen(repo: Repository, deckId: String, sceneId: String, onBack: () -> Unit) {
    val data by produceState<Pair<DeckEntity?, SceneEntity?>>(null to null, deckId, sceneId) {
        value = repo.dao.deck(deckId) to repo.dao.scene(deckId, sceneId)
    }
    val (deck, scene) = data
    var labels by remember { mutableStateOf(false) }
    Scaffold(topBar = {
        TopAppBar(
            title = { Text(scene?.title ?: "", maxLines = 1) },
            navigationIcon = { IconButton(onClick = onBack) { Icon(Icons.AutoMirrored.Filled.ArrowBack, "Back") } },
        )
    }) { padding ->
        if (deck == null || scene == null) return@Scaffold
        Column(
            Modifier.padding(padding).fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            scene.video?.let { VideoPlayer(File(deck.dir, it)) }
            val bitmap = rememberBitmap(scene.image?.let { File(deck.dir, it) })
            if (bitmap != null) {
                val regions = remember(scene) {
                    manifestJson.decodeFromString(ListSerializer(RegionDef.serializer()), scene.regionsJson)
                }
                scene.lectureJson?.let { json ->
                    val timeline = remember(scene) {
                        LectureTimeline(manifestJson.decodeFromString(LectureDef.serializer(), json), regions)
                    }
                    val clock = rememberLectureClock(timeline, timeline.lecture.audio?.let { File(deck.dir, it) }, active = true)
                    Box(
                        Modifier.fillMaxWidth().aspectRatio(4 / 5f).clip(RoundedCornerShape(20.dp))
                            .pointerInput(scene) { detectTapGestures(onTap = { clock.toggle() }) }
                    ) {
                        LectureView(bitmap, timeline, regions, clock.time, Modifier.fillMaxSize(), captionBottomPadding = 20)
                        Box(Modifier.align(Alignment.BottomStart).fillMaxWidth().height(3.dp).background(Panel2)) {
                            Box(Modifier.fillMaxWidth(clock.progress).height(3.dp).background(BrandGradient))
                        }
                    }
                }
                if (regions.any { it.label != null }) {
                    FilterChip(selected = labels, onClick = { labels = !labels }, label = { Text("Show labels") })
                }
                SceneImage(bitmap, regions, labels = labels, hideOthers = false)
            }
            scene.story?.let { Text(it, style = MaterialTheme.typography.bodyLarge) }
            scene.source?.let { Text("Source: $it", style = MaterialTheme.typography.labelSmall) }
        }
    }
}

@Composable
fun VideoPlayer(file: File, modifier: Modifier = Modifier) {
    val context = LocalContext.current
    val player = remember(file) {
        ExoPlayer.Builder(context).build().apply {
            setMediaItem(MediaItem.fromUri(Uri.fromFile(file)))
            prepare()
            playWhenReady = true
        }
    }
    val lifecycle = LocalLifecycleOwner.current.lifecycle
    DisposableEffect(player, lifecycle) {
        val observer = LifecycleEventObserver { _, event -> if (event == Lifecycle.Event.ON_PAUSE) player.pause() }
        lifecycle.addObserver(observer)
        onDispose {
            lifecycle.removeObserver(observer)
            player.release()
        }
    }
    AndroidView(
        factory = { PlayerView(it).apply { this.player = player } },
        modifier = modifier.fillMaxWidth().aspectRatio(16 / 9f),
    )
}
