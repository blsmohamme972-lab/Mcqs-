package com.mcqs.app.pkg

import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json

/**
 * `manifest.json` at the root of a content zip. See docs/package-format.md.
 * IDs are stable: re-importing a newer version keeps review progress for cards whose id is unchanged.
 */
@Serializable
data class Manifest(
    val format: Int,
    val id: String,
    val title: String,
    val version: Int = 1,
    val source: String? = null,
    val scenes: List<SceneDef> = emptyList(),
    val cards: List<CardDef>,
)

@Serializable
data class SceneDef(
    val id: String,
    val title: String,
    val image: String? = null,
    val video: String? = null,
    val story: String? = null,
    val source: String? = null,
    val regions: List<RegionDef> = emptyList(),
    /** Live lecture: image + narration + camera/highlight timeline (see Lecture.kt). */
    val lecture: LectureDef? = null,
    /** MCARDS image lesson: compiled HTML card (landscape) with its voice embedded (see Mcards.kt). */
    val entry: String? = null,
    val durationMs: Int? = null,
)

/** Rectangle in normalized image coordinates (0..1, origin top-left). */
@Serializable
data class RegionDef(
    val id: String,
    val x: Double,
    val y: Double,
    val w: Double,
    val h: Double,
    val label: String? = null,
)

@Serializable
data class CardDef(
    val id: String,
    val type: String,
    val front: String,
    val back: String? = null,
    val scene: String? = null,
    val region: String? = null,
    val image: String? = null,
    val options: List<String> = emptyList(),
    val answer: Int? = null,
    val explanation: String? = null,
    val source: String? = null,
    val tags: List<String> = emptyList(),
)

object CardType {
    const val BASIC = "basic"
    const val OCCLUSION = "occlusion"
    const val MCQ = "mcq"
    val all = setOf(BASIC, OCCLUSION, MCQ)
}

const val SUPPORTED_FORMAT = 1

val manifestJson = Json { ignoreUnknownKeys = true }

class InvalidPackageException(message: String) : Exception(message)

private val ID_RE = Regex("[A-Za-z0-9._-]{1,128}")

/** Returns a list of problems; empty means the manifest is valid. [hasFile] checks media paths. */
fun Manifest.validate(hasFile: (String) -> Boolean): List<String> {
    val errors = mutableListOf<String>()
    if (format != SUPPORTED_FORMAT) errors += "unsupported format $format (expected $SUPPORTED_FORMAT)"
    if (!ID_RE.matches(id)) errors += "invalid package id '$id'"
    if (title.isBlank()) errors += "empty title"

    fun media(owner: String, path: String?) {
        if (path != null && !hasFile(path)) errors += "$owner: missing file '$path'"
    }

    val sceneById = mutableMapOf<String, SceneDef>()
    for (s in scenes) {
        if (!ID_RE.matches(s.id)) errors += "invalid scene id '${s.id}'"
        if (sceneById.put(s.id, s) != null) errors += "duplicate scene id '${s.id}'"
        media("scene ${s.id}", s.image)
        media("scene ${s.id}", s.video)
        media("scene ${s.id}", s.entry)
        errors += s.lectureErrors(hasFile)
        val regionIds = mutableSetOf<String>()
        for (r in s.regions) {
            if (!regionIds.add(r.id)) errors += "scene ${s.id}: duplicate region '${r.id}'"
            val inside = r.x >= 0 && r.y >= 0 && r.w > 0 && r.h > 0 && r.x + r.w <= 1.0001 && r.y + r.h <= 1.0001
            if (!inside) errors += "scene ${s.id}: region '${r.id}' outside 0..1"
        }
    }

    val cardIds = mutableSetOf<String>()
    for (c in cards) {
        val who = "card ${c.id}"
        if (!ID_RE.matches(c.id)) errors += "invalid card id '${c.id}'"
        if (!cardIds.add(c.id)) errors += "duplicate card id '${c.id}'"
        if (c.type !in CardType.all) errors += "$who: unknown type '${c.type}'"
        if (c.front.isBlank()) errors += "$who: empty front"
        media(who, c.image)
        when (c.type) {
            CardType.BASIC -> if (c.back.isNullOrBlank()) errors += "$who: basic card needs back"
            CardType.OCCLUSION -> {
                val scene = c.scene?.let { sceneById[it] }
                when {
                    scene == null -> errors += "$who: unknown scene '${c.scene}'"
                    scene.image == null -> errors += "$who: scene '${scene.id}' has no image"
                    scene.regions.none { it.id == c.region } -> errors += "$who: unknown region '${c.region}'"
                }
                if (c.back.isNullOrBlank()) errors += "$who: occlusion card needs back"
            }
            CardType.MCQ -> {
                if (c.options.size < 2) errors += "$who: mcq needs at least 2 options"
                if (c.answer == null || c.answer !in c.options.indices) errors += "$who: mcq answer index invalid"
            }
        }
        if (c.type != CardType.OCCLUSION && c.scene != null && c.scene !in sceneById) {
            errors += "$who: unknown scene '${c.scene}'"
        }
    }
    return errors
}
