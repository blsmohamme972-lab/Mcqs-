package com.mcqs.app.ui

import android.net.Uri
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableDoubleStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.translate
import androidx.compose.ui.graphics.drawscope.scale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.media3.common.MediaItem
import androidx.media3.common.Player
import androidx.media3.exoplayer.ExoPlayer
import com.mcqs.app.pkg.LectureTimeline
import kotlinx.coroutines.delay
import java.io.File
import kotlin.math.min
import kotlin.math.sin

/** Playback clock for a lecture: follows the narration audio when there is one, else wall time. */
class LectureClock(private val player: ExoPlayer?, private val timeline: LectureTimeline) {
    var time by mutableDoubleStateOf(0.0)
    var playing by mutableStateOf(true)

    val duration: Double
        get() = timeline.duration(player?.duration?.takeIf { it > 0 }?.div(1000.0))

    val progress: Float get() = (time / duration).toFloat().coerceIn(0f, 1f)

    fun toggle() {
        playing = !playing
        player?.playWhenReady = playing
    }

    internal fun tick(elapsedSeconds: Double) {
        if (player != null) {
            time = player.currentPosition / 1000.0
            playing = player.playWhenReady
        } else if (playing) {
            time += elapsedSeconds
            if (time >= duration) time = 0.0 // loop like a reel
        }
    }
}

@Composable
fun rememberLectureClock(timeline: LectureTimeline, audio: File?, active: Boolean): LectureClock {
    val context = LocalContext.current
    val player = remember(audio, active) {
        if (!active || audio == null) null else ExoPlayer.Builder(context).build().apply {
            setMediaItem(MediaItem.fromUri(Uri.fromFile(audio)))
            repeatMode = Player.REPEAT_MODE_ONE
            prepare()
            playWhenReady = true
        }
    }
    val clock = remember(player, timeline) { LectureClock(player, timeline) }
    val lifecycle = LocalLifecycleOwner.current.lifecycle
    DisposableEffect(player, lifecycle) {
        var resume = false
        val observer = LifecycleEventObserver { _, e ->
            when (e) {
                Lifecycle.Event.ON_PAUSE -> { resume = clock.playing; if (clock.playing) clock.toggle() }
                Lifecycle.Event.ON_RESUME -> if (resume && !clock.playing) clock.toggle()
                else -> Unit
            }
        }
        lifecycle.addObserver(observer)
        onDispose {
            lifecycle.removeObserver(observer)
            player?.release()
        }
    }
    LaunchedEffect(clock, active) {
        if (!active) return@LaunchedEffect
        var last = System.nanoTime()
        while (true) {
            delay(16)
            val now = System.nanoTime()
            clock.tick((now - last) / 1e9)
            last = now
        }
    }
    return clock
}

/**
 * Draws the lecture at [time]: the image under a moving camera, hidden-region masks, the focus
 * outline (optionally pulsing) and the caption. Zoom 1 fits the whole image in the box.
 */
@Composable
fun LectureView(bitmap: ImageBitmap, timeline: LectureTimeline, regions: List<com.mcqs.app.pkg.RegionDef>,
                time: Double, modifier: Modifier = Modifier, captionBottomPadding: Int = 140) {
    Box(modifier.background(Ink).testTag("lecture")) {
        Canvas(Modifier.fillMaxSize()) {
            val iw = bitmap.width.toFloat()
            val ih = bitmap.height.toFloat()
            val cam = timeline.camera(time)
            val s = min(size.width / iw, size.height / ih) * cam.zoom.toFloat()
            val (focusId, effect, focusAge) = timeline.focus(time)
            translate(size.width / 2f, size.height / 2f) {
                scale(s, s, pivot = Offset.Zero) {
                    translate(-(cam.x * iw).toFloat(), -(cam.y * ih).toFloat()) {
                        drawImage(bitmap)
                        val corner = CornerRadius(14f / s)
                        for (r in regions) {
                            val tl = Offset((r.x * iw).toFloat(), (r.y * ih).toFloat())
                            val rs = Size((r.w * iw).toFloat(), (r.h * ih).toFloat())
                            val shown = timeline.revealed(r.id, time).toFloat()
                            if (shown < 1f) drawRoundRect(MaskOther.copy(alpha = 1f - shown), tl, rs, corner)
                            if (r.id == focusId) {
                                val fade = FastOutSlowInEasing.transform((focusAge / 0.4).toFloat().coerceIn(0f, 1f))
                                val pulse = if (effect == "pulse") (0.6f + 0.4f * sin(focusAge * 6.0).toFloat()) else 1f
                                drawRoundRect(Cyan.copy(alpha = 0.9f * fade * pulse), tl, rs, corner,
                                    style = Stroke(width = 4.dp.toPx() / s))
                                drawRoundRect(Cyan.copy(alpha = 0.12f * fade), tl, rs, corner)
                            }
                        }
                    }
                }
            }
        }
        timeline.caption(time)?.let { (text, age) ->
            Text(
                text,
                style = MaterialTheme.typography.titleLarge,
                color = Color.White,
                textAlign = TextAlign.Center,
                modifier = Modifier
                    .align(Alignment.BottomCenter)
                    .padding(start = 24.dp, end = 24.dp, bottom = captionBottomPadding.dp)
                    .alpha((age / 0.25).toFloat().coerceIn(0f, 1f))
                    .clip(RoundedCornerShape(16.dp))
                    .background(Color.Black.copy(alpha = 0.55f))
                    .padding(horizontal = 16.dp, vertical = 10.dp),
            )
        }
    }
}
