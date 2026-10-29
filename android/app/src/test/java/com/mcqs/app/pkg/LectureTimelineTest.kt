package com.mcqs.app.pkg

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class LectureTimelineTest {
    private val regions = listOf(
        RegionDef("a", 0.0, 0.0, 0.2, 0.2),
        RegionDef("b", 0.6, 0.6, 0.4, 0.4),
    )
    private val lecture = LectureDef(
        hidden = listOf("b"),
        cues = listOf(
            CueDef(at = 0.0, caption = "Intro"),
            CueDef(at = 2.0, focus = "a", caption = "Region A", transition = 1.0),
            CueDef(at = 5.0, focus = "b", zoom = 2.0, reveal = listOf("b"), effect = "pulse"),
            CueDef(at = 8.0, camera = CameraDef(0.5, 0.5, 1.0), caption = ""),
        ),
    )
    private val tl = LectureTimeline(lecture, regions)

    @Test
    fun cameraStartsOnOverviewAndEasesToFocus() {
        assertEquals(OVERVIEW, tl.camera(1.0))
        val start = tl.camera(2.0)
        assertEquals(0.5, start.x, 1e-9)
        val end = tl.camera(3.5)
        assertEquals(0.1, end.x, 1e-9) // centre of region a
        assertEquals(0.1, end.y, 1e-9)
        assertEquals(3.125, end.zoom, 1e-9) // fits 0.2 * 1.6 = 0.32 → 1/0.32
        val mid = tl.camera(2.5)
        assertTrue(mid.x in 0.1..0.5)
    }

    @Test
    fun explicitZoomAndCameraCues() {
        val b = tl.camera(6.0)
        assertEquals(0.8, b.x, 1e-9)
        assertEquals(2.0, b.zoom, 1e-9)
        val back = tl.camera(10.0)
        assertEquals(0.5, back.x, 1e-9)
        assertEquals(0.5, back.y, 1e-9)
        assertEquals(1.0, back.zoom, 1e-9)
    }

    @Test
    fun captionsPersistUntilChangedOrCleared() {
        assertEquals("Intro", tl.caption(1.0)!!.first)
        assertEquals("Region A", tl.caption(6.0)!!.first)
        assertEquals(4.0, tl.caption(6.0)!!.second, 1e-9) // seconds since its cue at 2.0
        assertNull(tl.caption(9.0))
    }

    @Test
    fun hiddenRegionsRevealOnTheirCue() {
        assertEquals(1.0, tl.revealed("a", 0.0), 0.0)
        assertEquals(0.0, tl.revealed("b", 4.9), 0.0)
        assertEquals(0.5, tl.revealed("b", 5.15), 1e-9)
        assertEquals(1.0, tl.revealed("b", 7.0), 0.0)
    }

    @Test
    fun focusAndEffect() {
        assertEquals(Triple(null, null, 0.0), tl.focus(1.0))
        val (id, effect, age) = tl.focus(5.5)
        assertEquals("b", id)
        assertEquals("pulse", effect)
        assertEquals(0.5, age, 1e-9)
    }

    @Test
    fun durationFallbacks() {
        assertEquals(11.0, tl.duration(null), 1e-9)
        assertEquals(42.0, tl.duration(42.0), 1e-9)
        assertEquals(7.0, LectureTimeline(lecture.copy(duration = 7.0), regions).duration(42.0), 1e-9)
    }

    @Test
    fun validationCatchesBadLectures() {
        val scene = SceneDef(
            id = "s", title = "S", image = "img.png", regions = regions,
            lecture = LectureDef(
                audio = "missing.mp3",
                hidden = listOf("zzz"),
                cues = listOf(
                    CueDef(at = 3.0, focus = "nope"),
                    CueDef(at = 1.0, reveal = listOf("a"), effect = "spin"),
                ),
            ),
        )
        val errors = scene.lectureErrors { it == "img.png" }.joinToString("\n")
        for (expected in listOf("missing file 'missing.mp3'", "unknown hidden region 'zzz'", "unknown focus region 'nope'",
                "cue 1 is before the previous cue", "reveals 'a' which is not hidden", "unknown effect 'spin'")) {
            assertTrue("missing: $expected\n$errors", expected in errors)
        }
        assertTrue(SceneDef("ok", "Ok", image = "img.png", regions = regions, lecture = lecture)
            .lectureErrors { true }.isEmpty())
    }
}
