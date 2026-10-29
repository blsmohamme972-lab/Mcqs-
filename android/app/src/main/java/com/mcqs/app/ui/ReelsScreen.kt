package com.mcqs.app.ui

import android.net.Uri
import androidx.annotation.OptIn
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxScope
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.pager.VerticalPager
import androidx.compose.foundation.pager.rememberPagerState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.media3.common.MediaItem
import androidx.media3.common.Player
import androidx.media3.common.VideoSize
import androidx.media3.common.util.UnstableApi
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.ui.AspectRatioFrameLayout
import androidx.media3.ui.PlayerView
import com.mcqs.app.data.ReelItem
import com.mcqs.app.data.Repository
import com.mcqs.app.pkg.LectureDef
import com.mcqs.app.pkg.LectureTimeline
import com.mcqs.app.pkg.RegionDef
import com.mcqs.app.pkg.manifestJson
import kotlinx.serialization.builtins.ListSerializer
import kotlinx.coroutines.delay
import java.io.File

/**
 * Shorts-style feed of every scene that has a video: swipe up/down, autoplay on loop,
 * tap to pause. One ExoPlayer is shared and attached only to the visible page.
 */
@OptIn(UnstableApi::class)
@Composable
fun ReelsScreen(repo: Repository, onStudy: (String) -> Unit, onScene: (String, String) -> Unit) {
    val items by remember { repo.dao.reels() }.collectAsState(initial = null)
    val reels = items ?: return
    if (reels.isEmpty()) {
        Column(Modifier.fillMaxSize().padding(32.dp), verticalArrangement = Arrangement.Center,
            horizontalAlignment = Alignment.CenterHorizontally) {
            Text("No lectures yet", style = MaterialTheme.typography.headlineSmall.brand())
            Text("Scenes with a lecture or a video show up here.", color = TextLo)
        }
        return
    }

    val context = LocalContext.current
    val player = remember {
        ExoPlayer.Builder(context).build().apply { repeatMode = Player.REPEAT_MODE_ONE }
    }
    var playing by remember { mutableStateOf(true) }
    var portrait by remember { mutableStateOf(true) }
    var progress by remember { mutableFloatStateOf(0f) }

    val lifecycle = LocalLifecycleOwner.current.lifecycle
    DisposableEffect(player, lifecycle) {
        val listener = object : Player.Listener {
            override fun onVideoSizeChanged(videoSize: VideoSize) {
                if (videoSize.width > 0) portrait = videoSize.height >= videoSize.width
            }
            override fun onPlayWhenReadyChanged(playWhenReady: Boolean, reason: Int) { playing = playWhenReady }
        }
        player.addListener(listener)
        // Leaving the app pauses; coming back resumes only if the reel was playing before.
        var resumeOnReturn = false
        val observer = LifecycleEventObserver { _, e ->
            when (e) {
                Lifecycle.Event.ON_PAUSE -> { resumeOnReturn = player.playWhenReady; player.pause() }
                Lifecycle.Event.ON_RESUME -> if (resumeOnReturn) player.play()
                else -> Unit
            }
        }
        lifecycle.addObserver(observer)
        onDispose {
            lifecycle.removeObserver(observer)
            player.removeListener(listener)
            player.release()
        }
    }

    val pager = rememberPagerState { reels.size }
    LaunchedEffect(pager.currentPage, reels) {
        val reel = reels.getOrNull(pager.currentPage) ?: return@LaunchedEffect
        progress = 0f
        // The shared player is for video reels; lecture pages run their own audio clock.
        if (reel.lectureJson == null && reel.video != null) {
            player.setMediaItem(MediaItem.fromUri(Uri.fromFile(File(reel.dir, reel.video))))
            player.prepare()
            player.play()
        } else {
            player.stop()
            player.clearMediaItems()
        }
    }
    LaunchedEffect(player) {
        while (true) {
            val d = player.duration
            if (d > 0) progress = (player.currentPosition.toFloat() / d).coerceIn(0f, 1f)
            delay(80)
        }
    }

    VerticalPager(
        state = pager,
        modifier = Modifier.fillMaxSize().background(Color.Black).testTag("reels"),
        key = { "${reels[it].deckId}/${reels[it].sceneId}" },
    ) { page ->
        val reel = reels[page]
        val active = page == pager.currentPage
        if (reel.lectureJson != null) {
            LecturePage(reel, active, onStudy = { onStudy(reel.deckId) }, onScene = { onScene(reel.deckId, reel.sceneId) })
            return@VerticalPager
        }
        Box(
            Modifier.fillMaxSize().pointerInput(page) {
                detectTapGestures(onTap = { if (player.playWhenReady) player.pause() else player.play() })
            }
        ) {
            val poster = rememberBitmap(reel.image?.let { File(reel.dir, it) }, maxDim = 1080)
            if (poster != null) {
                Image(poster, null, Modifier.fillMaxSize(), contentScale = ContentScale.Crop, alpha = 0.35f)
            }
            if (active) {
                AndroidView(
                    factory = {
                        PlayerView(it).apply {
                            useController = false
                            setShutterBackgroundColor(android.graphics.Color.TRANSPARENT)
                        }
                    },
                    update = {
                        it.player = player
                        it.resizeMode = if (portrait) AspectRatioFrameLayout.RESIZE_MODE_ZOOM
                        else AspectRatioFrameLayout.RESIZE_MODE_FIT
                    },
                    onRelease = { it.player = null },
                    modifier = Modifier.fillMaxSize(),
                )
            }
            ReelChrome(reel, active, playing, progress, onStudy = { onStudy(reel.deckId) },
                onScene = { onScene(reel.deckId, reel.sceneId) })
        }
    }
}

/** A live lecture page: the app moves the image itself, synced to the narration. */
@Composable
private fun LecturePage(reel: ReelItem, active: Boolean, onStudy: () -> Unit, onScene: () -> Unit) {
    val regions = remember(reel) { manifestJson.decodeFromString(ListSerializer(RegionDef.serializer()), reel.regionsJson) }
    val timeline = remember(reel) {
        LectureTimeline(manifestJson.decodeFromString(LectureDef.serializer(), reel.lectureJson!!), regions)
    }
    val clock = rememberLectureClock(timeline, timeline.lecture.audio?.let { File(reel.dir, it) }, active)
    val bitmap = rememberBitmap(reel.image?.let { File(reel.dir, it) }, maxDim = 2048)
    Box(Modifier.fillMaxSize().pointerInput(reel) { detectTapGestures(onTap = { clock.toggle() }) }) {
        if (bitmap != null) {
            LectureView(bitmap, timeline, regions, if (active) clock.time else 0.0, Modifier.fillMaxSize())
        }
        ReelChrome(reel, active, clock.playing, clock.progress, onStudy, onScene)
    }
}

/** Overlay shared by video and lecture reels: play icon, title/story, actions, progress bar. */
@Composable
private fun BoxScope.ReelChrome(reel: ReelItem, active: Boolean, playing: Boolean, progress: Float,
                                onStudy: () -> Unit, onScene: () -> Unit) {
    AnimatedVisibility(!playing && active, Modifier.align(Alignment.Center), enter = fadeIn(), exit = fadeOut()) {
        Box(Modifier.size(84.dp).clip(CircleShape).background(Color.Black.copy(alpha = 0.45f)),
            contentAlignment = Alignment.Center) {
            Icon(Icons.Filled.PlayArrow, "Play", tint = Color.White, modifier = Modifier.size(52.dp))
        }
    }
    ReelOverlay(reel, Modifier.align(Alignment.BottomStart), onStudy = onStudy, onScene = onScene)
    if (active) {
        Box(Modifier.align(Alignment.BottomStart).fillMaxWidth().height(3.dp).background(Color.White.copy(alpha = 0.2f))) {
            Box(Modifier.fillMaxWidth(progress).height(3.dp).background(BrandGradient))
        }
    }
    Text("Reels", style = MaterialTheme.typography.titleLarge, color = Color.White,
        modifier = Modifier.statusBarsPadding().padding(16.dp))
}

@Composable
private fun ReelOverlay(reel: ReelItem, modifier: Modifier, onStudy: () -> Unit, onScene: () -> Unit) {
    var expanded by remember(reel) { mutableStateOf(false) }
    Row(
        modifier
            .fillMaxWidth()
            .background(Brush.verticalGradient(listOf(Color.Transparent, Color.Black.copy(alpha = 0.85f))))
            .padding(start = 16.dp, end = 8.dp, top = 48.dp, bottom = 20.dp),
        verticalAlignment = Alignment.Bottom,
    ) {
        Column(Modifier.weight(1f)) {
            Text(
                reel.deckTitle,
                style = MaterialTheme.typography.labelMedium,
                color = Color.White,
                modifier = Modifier.clip(RoundedCornerShape(50)).background(BrandGradient)
                    .padding(horizontal = 10.dp, vertical = 3.dp),
            )
            Text(reel.title, style = MaterialTheme.typography.titleLarge, color = Color.White,
                modifier = Modifier.padding(top = 8.dp))
            reel.story?.let {
                Text(
                    it,
                    style = MaterialTheme.typography.bodyMedium,
                    color = Color.White.copy(alpha = 0.85f),
                    maxLines = if (expanded) 12 else 2,
                    overflow = TextOverflow.Ellipsis,
                    modifier = Modifier.padding(top = 4.dp).clickable { expanded = !expanded },
                )
            }
        }
        Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(18.dp),
            modifier = Modifier.padding(start = 8.dp)) {
            ReelAction(Icons.Filled.CheckCircle, "Cards", onStudy)
            ReelAction(Icons.Filled.Info, "Scene", onScene)
        }
    }
}

@Composable
private fun ReelAction(icon: ImageVector, label: String, onClick: () -> Unit) {
    Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.clickable(onClick = onClick)) {
        Box(Modifier.size(48.dp).clip(CircleShape).background(Color.White.copy(alpha = 0.15f)),
            contentAlignment = Alignment.Center) {
            Icon(icon, label, tint = Color.White)
        }
        Text(label, style = MaterialTheme.typography.labelSmall, color = Color.White)
    }
}
