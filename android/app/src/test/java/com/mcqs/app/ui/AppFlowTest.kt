package com.mcqs.app.ui

import android.graphics.Bitmap
import android.graphics.Canvas
import android.net.Uri
import androidx.compose.ui.test.hasTestTag
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.isEnabled
import androidx.compose.ui.test.isNotEnabled
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.test.core.app.ApplicationProvider
import com.mcqs.app.MainActivity
import com.mcqs.app.data.AppDb
import com.mcqs.app.data.Repository
import com.mcqs.app.data.Sync
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Before
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import org.robolectric.annotation.GraphicsMode
import java.io.File

/**
 * End-to-end on Robolectric: import the sample package, study occlusion and MCQ cards.
 * Screenshots go to app/build/screenshots/ for visual review.
 */
@RunWith(RobolectricTestRunner::class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
@Config(qualifiers = "w400dp-h860dp-xhdpi")
class AppFlowTest {
    @get:Rule val compose = createAndroidComposeRule<MainActivity>()

    private val context get() = ApplicationProvider.getApplicationContext<android.content.Context>()
    private val shots = File("build/screenshots").apply { mkdirs() }

    // The compose rule launches the activity before @Before runs, so disable sync at construction.
    init {
        Sync.enabled = false
    }

    @Before
    fun importSample() {
        val zip = File.createTempFile("sample", ".zip")
        javaClass.classLoader!!.getResourceAsStream("sample.zip")!!.use { input ->
            zip.outputStream().use { input.copyTo(it) }
        }
        val manifest = runBlocking { Repository(context).importZip(Uri.fromFile(zip)) }
        assertEquals(16, manifest.cards.size)
    }

    private fun shot(name: String) {
        compose.waitForIdle()
        // captureToImage() relies on PixelCopy, which Robolectric doesn't support; draw the window instead.
        compose.runOnUiThread {
            val view = compose.activity.window.decorView
            val bmp = Bitmap.createBitmap(view.width, view.height, Bitmap.Config.ARGB_8888)
            view.draw(Canvas(bmp))
            File(shots, "$name.png").outputStream().use { bmp.compress(Bitmap.CompressFormat.PNG, 100, it) }
        }
    }

    private fun waitFor(text: String) = compose.waitUntil(10_000) {
        compose.onAllNodes(hasText(text)).fetchSemanticsNodes().isNotEmpty()
    }

    @Test
    fun importStudyOcclusionAndMcq() {
        waitFor("Ch17 Chest trauma — sample")
        compose.onNodeWithText("16").assertExists()
        shot("1-home")

        // Reels tab lists the scene video.
        compose.onNodeWithText("Reels").performClick()
        waitFor("Tension pneumothorax — the burglar who can't leave")
        shot("1b-reels")
        compose.onNodeWithText("Decks").performClick()
        waitFor("Study")

        compose.onNodeWithText("Study").performClick()
        waitFor("Show answer")
        compose.onNodeWithText("Traumatic pneumothorax — direct lung injury from…?").assertExists()
        compose.waitUntil(10_000) { compose.onAllNodes(hasTestTag("scene-image")).fetchSemanticsNodes().isNotEmpty() }
        shot("2-occlusion-front")

        compose.onNodeWithText("Show answer").performClick()
        waitFor("Again")
        compose.onNodeWithText("Rib fracture.").assertExists()
        shot("3-occlusion-revealed")

        // First review of a new card: Easy graduates it, Good goes to the 10-minute learning step.
        compose.onNodeWithText("Good").performClick()
        waitFor("Traumatic pneumothorax — the other cause besides rib fracture?")
        val dao = AppDb.get(context).dao()
        assertEquals(1, runBlocking { dao.state("ct-ch17-sample/ptx.beam") }!!.step)

        // Clear the remaining 11 occlusion cards with Easy to reach the first MCQ.
        repeat(11) {
            waitFor("Show answer")
            compose.onNodeWithText("Show answer").performClick()
            waitFor("Easy")
            compose.onNodeWithText("Easy").performClick()
        }
        waitFor("Choose an answer")
        compose.onNodeWithText("Per this book, immediate decompression of a tension pneumothorax is performed by:")
            .assertExists()
        shot("4-mcq-front")

        // Pick a wrong option: only Again stays enabled.
        compose.onNodeWithText("Emergency thoracotomy").performClick()
        waitFor("Again")
        compose.onNode(hasText("Again") and isEnabled()).assertExists()
        compose.onNode(hasText("Good") and isNotEnabled()).assertExists()
        shot("5-mcq-wrong")
        compose.onNodeWithText("Again").performClick()
        waitFor("Chest tube for traumatic pneumothorax (4th/5th ICS, midaxillary line) is directed:")
    }
}
