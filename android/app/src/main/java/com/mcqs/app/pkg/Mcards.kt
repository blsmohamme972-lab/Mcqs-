package com.mcqs.app.pkg

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.int
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import java.security.MessageDigest

/**
 * Reads a Kafu `MCARDS_*.zip` (image lessons, `motioncards-manifest.json`) as a deck of scenes.
 * Each animation becomes one scene whose `entry` is the compiled landscape HTML card; its voice is embedded in
 * that file and handed to the player (see ui/McardPlayer.kt). Anki cards are untouched: the deck has none.
 */
object Mcards {
    const val MANIFEST_NAME = "motioncards-manifest.json"
    const val BOOK_MANIFEST_NAME = "booklessons-manifest.json"
    private const val BOOK_TYPE = "mcqs-booklessons"
    private const val TYPE = "kafu-motioncards"
    private val QID = Regex("Q\\d{9}")

    /** [read] returns the bytes of a package file (or null when missing) so hashes can be checked. */
    fun convert(text: String, read: (String) -> ByteArray?): Manifest {
        val root = Json.parseToJsonElement(text).jsonObject
        if (root["package_type"]?.jsonPrimitive?.content != TYPE) throw InvalidPackageException("not a $TYPE package")
        if (root["schema_version"]?.jsonPrimitive?.int != 1) throw InvalidPackageException("unsupported MCARDS schema")
        val id = root["package_id"]!!.jsonPrimitive.content
        val revision = root["package_revision"]!!.jsonPrimitive.int
        val rows: JsonArray = root["animations"]!!.jsonArray
        if (rows.isEmpty()) throw InvalidPackageException("package has no lessons")
        val scenes = rows.map { el ->
            val row: JsonObject = el.jsonObject
            val qid = row["qid"]!!.jsonPrimitive.content
            if (!QID.matches(qid)) throw InvalidPackageException("bad lesson id '$qid'")
            val entry = row["entry_path"]!!.jsonPrimitive.content
            if (entry != "entries/$qid.html") throw InvalidPackageException("$qid: unexpected entry path")
            val bytes = read(entry) ?: throw InvalidPackageException("$qid: missing $entry")
            val sha = MessageDigest.getInstance("SHA-256").digest(bytes).joinToString("") { "%02x".format(it) }
            if (!sha.equals(row["entry_sha256"]!!.jsonPrimitive.content, ignoreCase = true)) {
                throw InvalidPackageException("$qid: checksum mismatch")
            }
            val panel = row["final_panel"]?.jsonObject
            SceneDef(
                id = qid,
                title = panel?.get("takeaway")?.jsonPrimitive?.content ?: qid,
                story = panel?.get("correct_answer_statements")?.jsonArray?.joinToString("\n") { it.jsonPrimitive.content },
                entry = entry,
                durationMs = row["duration_ms"]!!.jsonPrimitive.int,
            )
        }
        return Manifest(format = SUPPORTED_FORMAT, id = id, title = "MCARDS $id", version = revision, source = "mcards", scenes = scenes, cards = emptyList())
    }

    /** Book lessons (tools/booklessons.py): one landscape image + voice per topic of the book; same cards, simpler manifest. */
    fun convertBook(text: String, read: (String) -> ByteArray?): Manifest {
        val root = Json.parseToJsonElement(text).jsonObject
        if (root["package_type"]?.jsonPrimitive?.content != BOOK_TYPE) throw InvalidPackageException("not a $BOOK_TYPE package")
        if (root["schema_version"]?.jsonPrimitive?.int != 1) throw InvalidPackageException("unsupported book lesson schema")
        val id = root["package_id"]!!.jsonPrimitive.content
        val rows = root["lessons"]!!.jsonArray
        if (rows.isEmpty()) throw InvalidPackageException("package has no lessons")
        val scenes = rows.map { el ->
            val row = el.jsonObject
            val lid = row["id"]!!.jsonPrimitive.content
            val qid = row["qid"]!!.jsonPrimitive.content
            val entry = row["entry_path"]!!.jsonPrimitive.content
            if (entry != "entries/$qid.html") throw InvalidPackageException("$lid: unexpected entry path")
            val bytes = read(entry) ?: throw InvalidPackageException("$lid: missing $entry")
            val sha = MessageDigest.getInstance("SHA-256").digest(bytes).joinToString("") { "%02x".format(it) }
            if (!sha.equals(row["entry_sha256"]!!.jsonPrimitive.content, ignoreCase = true)) throw InvalidPackageException("$lid: checksum mismatch")
            SceneDef(
                id = lid, title = row["title"]!!.jsonPrimitive.content,
                story = row["takeaway"]?.jsonPrimitive?.content,
                source = row["pages"]?.jsonPrimitive?.content?.let { "p $it" },
                entry = entry, durationMs = row["duration_ms"]!!.jsonPrimitive.int,
            )
        }
        val title = listOfNotNull(root["chapter"]?.jsonPrimitive?.content?.let { "Ch $it" }, root["chapter_title"]?.jsonPrimitive?.content).joinToString(" · ")
        return Manifest(format = SUPPORTED_FORMAT, id = id, title = title.ifBlank { id }, version = root["package_revision"]!!.jsonPrimitive.int,
            source = root["book"]?.jsonPrimitive?.content, scenes = scenes, cards = emptyList())
    }
}
