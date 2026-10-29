package com.mcqs.app.data

import android.content.Context
import android.net.Uri
import androidx.room.withTransaction
import com.mcqs.app.pkg.InvalidPackageException
import com.mcqs.app.pkg.LectureDef
import com.mcqs.app.pkg.Manifest
import com.mcqs.app.pkg.RegionDef
import com.mcqs.app.pkg.ZipExtractor
import com.mcqs.app.pkg.manifestJson
import com.mcqs.app.srs.CardState
import com.mcqs.app.srs.Rating
import com.mcqs.app.srs.Scheduler
import com.mcqs.app.srs.SrsCard
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.builtins.ListSerializer
import kotlinx.serialization.builtins.serializer
import java.io.File
import java.security.DigestInputStream
import java.security.MessageDigest
import java.util.Calendar

class Repository(private val context: Context) {
    private val db = AppDb.get(context)
    val dao = db.dao()
    val scheduler = Scheduler()

    private val decksRoot get() = File(context.filesDir, "decks")

    /** Imports (or updates) a content zip. Review progress is kept for cards whose id is unchanged. */
    suspend fun importZip(uri: Uri): Manifest = withContext(Dispatchers.IO) {
        val staging = File(decksRoot, "staging-${System.nanoTime()}")
        // Copy first so the hash covers the whole file (ZipInputStream stops before the central directory).
        val copy = File(context.cacheDir, "import-${System.nanoTime()}.zip")
        val digest = MessageDigest.getInstance("SHA-256")
        val manifest = try {
            val input = context.contentResolver.openInputStream(uri)
                ?: throw InvalidPackageException("cannot open file")
            DigestInputStream(input, digest).use { src -> copy.outputStream().use { src.copyTo(it) } }
            copy.inputStream().use { ZipExtractor.extract(it, staging) }
        } finally {
            copy.delete()
        }
        val sha = digest.digest().joinToString("") { "%02x".format(it) }

        val dir = File(decksRoot, "${manifest.id}-${System.currentTimeMillis()}")
        if (!staging.renameTo(dir)) {
            staging.deleteRecursively()
            throw InvalidPackageException("cannot store package")
        }
        val old = dao.deck(manifest.id)
        try {
            db.withTransaction { writeManifest(manifest, dir, sha) }
        } catch (e: Throwable) {
            dir.deleteRecursively()
            throw e
        }
        if (old != null && old.dir != dir.path) File(old.dir).deleteRecursively()
        manifest
    }

    private suspend fun writeManifest(m: Manifest, dir: File, sha: String) {
        dao.upsertDeck(DeckEntity(m.id, m.title, m.version, m.source, dir.path, System.currentTimeMillis(), sha))
        dao.deleteScenes(m.id)
        dao.insertScenes(m.scenes.mapIndexed { i, s ->
            SceneEntity(
                deckId = m.id, id = s.id, title = s.title, image = s.image, video = s.video,
                story = s.story, source = s.source,
                regionsJson = manifestJson.encodeToString(ListSerializer(RegionDef.serializer()), s.regions),
                ord = i,
                lectureJson = s.lecture?.let { manifestJson.encodeToString(LectureDef.serializer(), it) },
            )
        })
        val cards = m.cards.mapIndexed { i, c ->
            CardEntity(
                uid = "${m.id}/${c.id}", deckId = m.id, type = c.type, front = c.front, back = c.back,
                sceneId = c.scene, regionId = c.region, image = c.image,
                optionsJson = manifestJson.encodeToString(ListSerializer(String.serializer()), c.options),
                answer = c.answer, explanation = c.explanation, source = c.source,
                tags = c.tags.joinToString(" "), ord = i, active = true,
            )
        }
        // Cards absent from this version stay deactivated (history kept); the rest come back active.
        dao.deactivateAll(m.id)
        dao.upsertCards(cards)
    }

    suspend fun deleteDeck(id: String) = withContext(Dispatchers.IO) {
        val deck = dao.deck(id) ?: return@withContext
        db.withTransaction {
            dao.deleteLogs(id)
            dao.deleteStates(id)
            dao.deleteCards(id)
            dao.deleteScenes(id)
            dao.deleteDeckRow(id)
        }
        File(deck.dir).deleteRecursively()
    }

    /** Removes leftover extraction folders (e.g. after a crash mid-import). */
    suspend fun cleanOrphanDirs() = withContext(Dispatchers.IO) {
        val used = dao.allDecks().map { File(it.dir).name }.toSet()
        decksRoot.listFiles()?.filter { it.name !in used }?.forEach { it.deleteRecursively() }
    }

    fun file(deck: DeckEntity, relative: String?): File? = relative?.let { File(deck.dir, it) }

    /**
     * Picks the next card: due cards first, then unseen cards (daily limit), then learning
     * cards up to [LEARN_AHEAD_MS] early so a session doesn't stall on 1–10 minute steps.
     */
    suspend fun nextCard(deckId: String, now: Long = System.currentTimeMillis()): CardEntity? {
        dao.nextDue(deckId, now)?.let { return dao.card(it.uid) }
        val introduced = dao.newIntroducedSince(deckId, dayStart(now))
        if (introduced < NEW_PER_DAY) dao.nextUnseen(deckId)?.let { return it }
        dao.nextLearningAhead(deckId, now + LEARN_AHEAD_MS)?.let { return dao.card(it.uid) }
        return null
    }

    suspend fun srsCard(uid: String, now: Long): SrsCard =
        dao.state(uid)?.toSrs() ?: SrsCard(due = now)

    suspend fun answer(card: CardEntity, rating: Rating, durationMs: Long, now: Long = System.currentTimeMillis()) {
        val existing = dao.state(card.uid)
        val before = existing?.toSrs() ?: SrsCard(due = now)
        val after = scheduler.review(before, rating, now)
        db.withTransaction {
            dao.upsertState(
                ReviewStateEntity(
                    uid = card.uid, deckId = card.deckId, state = after.state.code, step = after.step,
                    stability = after.stability, difficulty = after.difficulty,
                    due = after.due, lastReview = after.lastReview,
                )
            )
            dao.insertLog(ReviewLogEntity(uid = card.uid, deckId = card.deckId, rating = rating.value,
                time = now, durationMs = durationMs, wasNew = existing == null))
        }
    }

    private fun ReviewStateEntity.toSrs() = SrsCard(CardState.of(state), step, stability, difficulty, due, lastReview)

    companion object {
        const val NEW_PER_DAY = 20
        const val LEARN_AHEAD_MS = 20 * 60_000L

        /** The study day starts at 04:00 local time, like Anki. */
        fun dayStart(now: Long): Long {
            val cal = Calendar.getInstance().apply {
                timeInMillis = now
                set(Calendar.HOUR_OF_DAY, 4)
                set(Calendar.MINUTE, 0)
                set(Calendar.SECOND, 0)
                set(Calendar.MILLISECOND, 0)
            }
            if (cal.timeInMillis > now) cal.add(Calendar.DAY_OF_MONTH, -1)
            return cal.timeInMillis
        }
    }
}
