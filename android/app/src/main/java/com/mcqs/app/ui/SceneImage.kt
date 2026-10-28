package com.mcqs.app.ui

import android.graphics.BitmapFactory
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.awaitEachGesture
import androidx.compose.foundation.gestures.awaitFirstDown
import androidx.compose.foundation.gestures.calculatePan
import androidx.compose.foundation.gestures.calculateZoom
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.produceState
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clipToBounds
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.input.pointer.positionChanged
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.layout.onSizeChanged
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.unit.IntSize
import androidx.compose.ui.unit.dp
import com.mcqs.app.pkg.RegionDef
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File

/** Decodes [file] downsampled so neither side exceeds [maxDim] pixels. */
fun decodeSampled(file: File, maxDim: Int): ImageBitmap? {
    if (!file.isFile) return null
    val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
    BitmapFactory.decodeFile(file.path, bounds)
    var sample = 1
    while (bounds.outWidth / sample > maxDim || bounds.outHeight / sample > maxDim) sample *= 2
    return BitmapFactory.decodeFile(file.path, BitmapFactory.Options().apply { inSampleSize = sample })?.asImageBitmap()
}

@Composable
fun rememberBitmap(file: File?, maxDim: Int = 2048): ImageBitmap? {
    val state = produceState<ImageBitmap?>(null, file, maxDim) {
        value = file?.let { withContext(Dispatchers.IO) { decodeSampled(it, maxDim) } }
    }
    return state.value
}

/**
 * Scene image with image-occlusion masks and pinch-zoom.
 *
 * - [targetId]: region being asked; drawn in the accent colour, fades and shrinks on [revealed].
 * - [hideOthers]: mask every other region too ("hide all, guess one"), so shapes don't give hints.
 * - [labels]: outline every region and print its label (scene browsing mode).
 *
 * One-finger drags pass through to the parent scroll unless the image is zoomed; double-tap resets zoom.
 */
@Composable
fun SceneImage(
    bitmap: ImageBitmap,
    regions: List<RegionDef>,
    modifier: Modifier = Modifier,
    targetId: String? = null,
    revealed: Boolean = false,
    hideOthers: Boolean = true,
    labels: Boolean = false,
) {
    val reveal by animateFloatAsState(if (revealed) 1f else 0f, tween(220), label = "reveal")
    var scale by remember { mutableFloatStateOf(1f) }
    var offset by remember { mutableStateOf(Offset.Zero) }
    var boxSize by remember { mutableStateOf(IntSize.Zero) }

    fun clampOffset(o: Offset): Offset {
        val maxX = (scale - 1f) * boxSize.width / 2f
        val maxY = (scale - 1f) * boxSize.height / 2f
        return Offset(o.x.coerceIn(-maxX, maxX), o.y.coerceIn(-maxY, maxY))
    }

    Box(
        modifier
            .testTag("scene-image")
            .fillMaxWidth()
            .clipToBounds()
            .onSizeChanged { boxSize = it }
            .pointerInput(Unit) {
                awaitEachGesture {
                    awaitFirstDown(requireUnconsumed = false)
                    do {
                        val event = awaitPointerEvent()
                        val pressed = event.changes.count { it.pressed }
                        if (pressed >= 2 || scale > 1f) {
                            scale = (scale * event.calculateZoom()).coerceIn(1f, 5f)
                            offset = if (scale == 1f) Offset.Zero else clampOffset(offset + event.calculatePan())
                            event.changes.forEach { if (it.positionChanged()) it.consume() }
                        }
                    } while (event.changes.any { it.pressed })
                }
            }
            .pointerInput(Unit) {
                detectTapGestures(onDoubleTap = { scale = 1f; offset = Offset.Zero })
            }
    ) {
        BoxWithConstraints(
            Modifier
                .fillMaxWidth()
                .aspectRatio(bitmap.width.toFloat() / bitmap.height)
                .graphicsLayer {
                    scaleX = scale
                    scaleY = scale
                    translationX = offset.x
                    translationY = offset.y
                }
        ) {
            Image(bitmap, contentDescription = null, modifier = Modifier.fillMaxSize(), contentScale = ContentScale.FillBounds)
            Canvas(Modifier.fillMaxSize()) {
                val corner = CornerRadius(6.dp.toPx())
                for (r in regions) {
                    val topLeft = Offset((r.x * size.width).toFloat(), (r.y * size.height).toFloat())
                    val rs = Size((r.w * size.width).toFloat(), (r.h * size.height).toFloat())
                    when {
                        r.id == targetId -> {
                            if (reveal < 1f) {
                                val inset = Offset(rs.width, rs.height) * (reveal * 0.1f)
                                drawRoundRect(
                                    MaskTarget.copy(alpha = 1f - reveal), topLeft + inset,
                                    Size(rs.width - 2 * inset.x, rs.height - 2 * inset.y), corner,
                                )
                            }
                            if (reveal > 0f) {
                                drawRoundRect(RevealOutline.copy(alpha = reveal), topLeft, rs, corner, style = Stroke(3.dp.toPx()))
                            }
                        }
                        labels -> drawRoundRect(Color.White.copy(alpha = 0.9f), topLeft, rs, corner, style = Stroke(2.dp.toPx()))
                        hideOthers && targetId != null -> drawRoundRect(MaskOther, topLeft, rs, corner)
                    }
                }
            }
            if (labels) {
                for (r in regions) {
                    val label = r.label ?: continue
                    Text(
                        label,
                        style = MaterialTheme.typography.labelSmall,
                        color = Color.White,
                        modifier = Modifier
                            .offset(maxWidth * r.x.toFloat(), maxHeight * r.y.toFloat())
                            .background(Color.Black.copy(alpha = 0.65f), RoundedCornerShape(4.dp))
                            .padding(horizontal = 4.dp, vertical = 1.dp),
                    )
                }
            }
        }
    }
}
