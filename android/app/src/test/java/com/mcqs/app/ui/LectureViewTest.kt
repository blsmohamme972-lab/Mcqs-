package com.mcqs.app.ui

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Canvas
import androidx.activity.ComponentActivity
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.mutableDoubleStateOf
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onNodeWithText
import com.mcqs.app.pkg.CueDef
import com.mcqs.app.pkg.LectureDef
import com.mcqs.app.pkg.LectureTimeline
import com.mcqs.app.pkg.Manifest
import com.mcqs.app.pkg.manifestJson
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import org.robolectric.annotation.GraphicsMode
import java.io.File
import java.util.zip.ZipInputStream

/** Renders a lecture at fixed times; screenshots go to app/build/screenshots/lecture-*.png. */
@RunWith(RobolectricTestRunner::class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
@Config(qualifiers = "w400dp-h860dp-xhdpi")
class LectureViewTest {
    @get:Rule val compose = createAndroidComposeRule<ComponentActivity>()

    private fun fixture(): Pair<Manifest, ByteArray> {
        var manifest: Manifest? = null
        var image: ByteArray? = null
        ZipInputStream(javaClass.classLoader!!.getResourceAsStream("sample.zip")!!).use { z ->
            while (true) {
                val e = z.nextEntry ?: break
                when (e.name) {
                    "manifest.json" -> manifest = manifestJson.decodeFromString(Manifest.serializer(), z.readBytes().decodeToString())
                    "media/scene.png" -> image = z.readBytes()
                }
            }
        }
        return manifest!! to image!!
    }

    private fun shot(name: String) {
        compose.waitForIdle()
        compose.runOnUiThread {
            val view = compose.activity.window.decorView
            val bmp = Bitmap.createBitmap(view.width, view.height, Bitmap.Config.ARGB_8888)
            view.draw(Canvas(bmp))
            File("build/screenshots").apply { mkdirs() }.resolve("lecture-$name.png").outputStream()
                .use { bmp.compress(Bitmap.CompressFormat.PNG, 100, it) }
        }
    }

    @Test
    fun cameraHighlightCaptionAndReveal() {
        val (manifest, png) = fixture()
        val regions = manifest.scenes.first().regions
        val bitmap = BitmapFactory.decodeByteArray(png, 0, png.size).asImageBitmap()
        val lecture = LectureDef(
            hidden = listOf("firefighter"),
            cues = listOf(
                CueDef(at = 0.0, caption = "Overview"),
                CueDef(at = 2.0, focus = "car", caption = "Focus on one region"),
                CueDef(at = 5.0, focus = "firefighter", reveal = listOf("firefighter"), caption = "Revealed"),
            ),
        )
        val timeline = LectureTimeline(lecture, regions)
        val time = mutableDoubleStateOf(0.5)
        compose.setContent {
            McqsTheme { LectureView(bitmap, timeline, regions, time.doubleValue, Modifier.fillMaxSize()) }
        }
        compose.onNodeWithText("Overview").assertExists()
        shot("1-overview")

        time.doubleValue = 4.0
        compose.onNodeWithText("Focus on one region").assertExists()
        shot("2-focus")

        time.doubleValue = 4.9
        shot("3-before-reveal")

        time.doubleValue = 7.0
        compose.onNodeWithText("Revealed").assertExists()
        shot("4-revealed")
    }
}
