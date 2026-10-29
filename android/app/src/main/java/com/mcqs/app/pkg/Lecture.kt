package com.mcqs.app.pkg

import kotlinx.serialization.Serializable
import kotlin.math.exp
import kotlin.math.ln
import kotlin.math.min

/**
 * A lecture: one scene image + optional narration audio + a timeline of cues that move the
 * camera over the image, highlight and reveal regions, and show captions. The app renders it
 * live (no pre-rendered video), synced to the audio clock.
 */
@Serializable
data class LectureDef(
    /** Narration file in the package; the lecture clock follows its playback position. */
    val audio: String? = null,
    /** Seconds. Defaults to the audio length, or the last cue + 3 s for silent lectures. */
    val duration: Double? = null,
    /** Regions masked at the start; a cue's [CueDef.reveal] uncovers them. */
    val hidden: List<String> = emptyList(),
    val cues: List<CueDef> = emptyList(),
)

@Serializable
data class CueDef(
    /** Seconds from the start. Cues must be in time order. */
    val at: Double,
    /** Move the camera onto this region (and outline it). */
    val focus: String? = null,
    /** Zoom for [focus]; default fits the region with some margin. */
    val zoom: Double? = null,
    /** Explicit camera position instead of [focus]. */
    val camera: CameraDef? = null,
    /** Subtitle shown from this cue on; "" clears it. */
    val caption: String? = null,
    /** "pulse" makes the focus outline throb. */
    val effect: String? = null,
    /** Regions from [LectureDef.hidden] to uncover at this cue. */
    val reveal: List<String> = emptyList(),
    /** Seconds the camera takes to reach this cue's target. */
    val transition: Double = 0.8,
)

/** Camera centre in normalized image coordinates; zoom 1 = whole image fitted to the screen. */
@Serializable
data class CameraDef(val x: Double, val y: Double, val zoom: Double = 1.0)

val OVERVIEW = CameraDef(0.5, 0.5, 1.0)

private fun ease(t: Double): Double {
    val c = t.coerceIn(0.0, 1.0)
    return c * c * (3 - 2 * c)
}

/** Pure timeline evaluation, kept free of Android so it is unit-tested directly. */
class LectureTimeline(val lecture: LectureDef, regions: List<RegionDef>) {
    private val regions = regions.associateBy { it.id }
    private val moves = lecture.cues.filter { it.focus != null || it.camera != null }

    val lastCue: Double get() = lecture.cues.maxOfOrNull { it.at } ?: 0.0

    fun duration(audioSeconds: Double?): Double =
        lecture.duration ?: audioSeconds?.takeIf { it > 0 } ?: (lastCue + 3.0)

    private fun target(cue: CueDef): CameraDef {
        cue.camera?.let { return it }
        val r = regions[cue.focus] ?: return OVERVIEW
        val fit = min(1.0 / (r.w * 1.6), 1.0 / (r.h * 1.6)).coerceIn(1.0, 4.0)
        return CameraDef(r.x + r.w / 2, r.y + r.h / 2, cue.zoom ?: fit)
    }

    /** Camera at time [t]: eases from the previous target to the latest one. Zoom moves in log space. */
    fun camera(t: Double): CameraDef {
        val i = moves.indexOfLast { it.at <= t }
        if (i < 0) return OVERVIEW
        val from = if (i == 0) OVERVIEW else target(moves[i - 1])
        val to = target(moves[i])
        val k = ease((t - moves[i].at) / moves[i].transition.coerceAtLeast(0.01))
        return CameraDef(
            from.x + (to.x - from.x) * k,
            from.y + (to.y - from.y) * k,
            exp(ln(from.zoom) + (ln(to.zoom) - ln(from.zoom)) * k),
        )
    }

    /** Current focus region, the effect, and seconds since that cue (for fade-ins). */
    fun focus(t: Double): Triple<String?, String?, Double> {
        val cue = moves.lastOrNull { it.at <= t } ?: return Triple(null, null, 0.0)
        return Triple(cue.focus, cue.effect, t - cue.at)
    }

    /** Current caption and seconds since it appeared, or null. */
    fun caption(t: Double): Pair<String, Double>? {
        val cue = lecture.cues.lastOrNull { it.at <= t && it.caption != null } ?: return null
        return cue.caption!!.takeIf { it.isNotEmpty() }?.let { it to (t - cue.at) }
    }

    /** 0 = still masked, 1 = fully revealed (0.3 s fade). Regions not in `hidden` are always 1. */
    fun revealed(regionId: String, t: Double): Double {
        if (regionId !in lecture.hidden) return 1.0
        val cue = lecture.cues.firstOrNull { regionId in it.reveal && it.at <= t } ?: return 0.0
        return ((t - cue.at) / 0.3).coerceIn(0.0, 1.0)
    }
}

/** Validation for a scene's lecture; [hasFile] checks media paths. */
fun SceneDef.lectureErrors(hasFile: (String) -> Boolean): List<String> {
    val l = lecture ?: return emptyList()
    val who = "scene $id lecture"
    val errors = mutableListOf<String>()
    if (image == null) errors += "$who: needs the scene image"
    l.audio?.let { if (!hasFile(it)) errors += "$who: missing file '$it'" }
    if (l.duration != null && l.duration <= 0) errors += "$who: duration must be > 0"
    val ids = regions.map { it.id }.toSet()
    l.hidden.filter { it !in ids }.forEach { errors += "$who: unknown hidden region '$it'" }
    var last = 0.0
    for ((i, c) in l.cues.withIndex()) {
        if (c.at < last) errors += "$who: cue $i is before the previous cue"
        last = maxOf(last, c.at)
        if (c.focus != null && c.focus !in ids) errors += "$who: cue $i unknown focus region '${c.focus}'"
        c.reveal.filter { it !in l.hidden }.forEach { errors += "$who: cue $i reveals '$it' which is not hidden" }
        if (c.zoom != null && c.zoom <= 0) errors += "$who: cue $i zoom must be > 0"
        if (c.camera != null && c.camera.zoom <= 0) errors += "$who: cue $i camera zoom must be > 0"
        if (c.effect != null && c.effect != "pulse") errors += "$who: cue $i unknown effect '${c.effect}'"
    }
    return errors
}
