package com.mcqs.app.data

import android.content.Context
import androidx.room.AutoMigration
import androidx.room.ColumnInfo
import androidx.room.Dao
import androidx.room.Database
import androidx.room.Entity
import androidx.room.Index
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.PrimaryKey
import androidx.room.Query
import androidx.room.Room
import androidx.room.RoomDatabase
import androidx.room.Upsert
import kotlinx.coroutines.flow.Flow

@Entity(tableName = "decks")
data class DeckEntity(
    @PrimaryKey val id: String,
    val title: String,
    val version: Int,
    val source: String?,
    /** Absolute path of the extracted package directory. */
    val dir: String,
    val importedAt: Long,
    /** sha256 of the imported zip; sync skips packages whose published hash matches. */
    @ColumnInfo(defaultValue = "NULL") val sha256: String? = null,
)

@Entity(tableName = "scenes", primaryKeys = ["deckId", "id"])
data class SceneEntity(
    val deckId: String,
    val id: String,
    val title: String,
    val image: String?,
    val video: String?,
    val story: String?,
    val source: String?,
    val regionsJson: String,
    val ord: Int,
)

/** [uid] is "deckId/cardId": stable across re-imports so review progress survives updates. */
@Entity(tableName = "cards", indices = [Index("deckId")])
data class CardEntity(
    @PrimaryKey val uid: String,
    val deckId: String,
    val type: String,
    val front: String,
    val back: String?,
    val sceneId: String?,
    val regionId: String?,
    val image: String?,
    val optionsJson: String,
    val answer: Int?,
    val explanation: String?,
    val source: String?,
    val tags: String,
    val ord: Int,
    /** False when a newer package version no longer contains this card. */
    val active: Boolean,
)

@Entity(tableName = "review_state", indices = [Index("deckId", "due")])
data class ReviewStateEntity(
    @PrimaryKey val uid: String,
    val deckId: String,
    val state: Int,
    val step: Int?,
    val stability: Double?,
    val difficulty: Double?,
    val due: Long,
    val lastReview: Long?,
)

@Entity(tableName = "review_log", indices = [Index("deckId", "time")])
data class ReviewLogEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val uid: String,
    val deckId: String,
    val rating: Int,
    val time: Long,
    val durationMs: Long,
    val wasNew: Boolean,
)

data class DeckSummary(
    val id: String,
    val title: String,
    val version: Int,
    val total: Int,
    val due: Int,
    val unseen: Int,
    val scenes: Int,
)

/** A scene with a video, for the Reels feed. */
data class ReelItem(
    val deckId: String,
    val sceneId: String,
    val deckTitle: String,
    val title: String,
    val image: String?,
    val video: String,
    val story: String?,
    val dir: String,
)

@Dao
interface StudyDao {
    @Query(
        """
        SELECT s.deckId, s.id AS sceneId, d.title AS deckTitle, s.title, s.image, s.video, s.story, d.dir
        FROM scenes s JOIN decks d ON d.id = s.deckId
        WHERE s.video IS NOT NULL ORDER BY d.title, s.ord
        """
    )
    fun reels(): Flow<List<ReelItem>>

    @Query(
        """
        SELECT d.id, d.title, d.version,
          (SELECT COUNT(*) FROM cards c WHERE c.deckId = d.id AND c.active) AS total,
          (SELECT COUNT(*) FROM review_state r JOIN cards c ON c.uid = r.uid
             WHERE r.deckId = d.id AND c.active AND r.due <= :now) AS due,
          (SELECT COUNT(*) FROM cards c WHERE c.deckId = d.id AND c.active
             AND c.uid NOT IN (SELECT uid FROM review_state)) AS unseen,
          (SELECT COUNT(*) FROM scenes s WHERE s.deckId = d.id) AS scenes
        FROM decks d ORDER BY d.title
        """
    )
    fun deckSummaries(now: Long): Flow<List<DeckSummary>>

    @Query("SELECT * FROM decks WHERE id = :id")
    suspend fun deck(id: String): DeckEntity?

    @Query("SELECT * FROM decks")
    suspend fun allDecks(): List<DeckEntity>

    @Upsert
    suspend fun upsertDeck(deck: DeckEntity)

    @Query("DELETE FROM decks WHERE id = :id")
    suspend fun deleteDeckRow(id: String)

    @Query("SELECT * FROM scenes WHERE deckId = :deckId ORDER BY ord")
    suspend fun scenes(deckId: String): List<SceneEntity>

    @Query("SELECT * FROM scenes WHERE deckId = :deckId AND id = :id")
    suspend fun scene(deckId: String, id: String): SceneEntity?

    @Query("DELETE FROM scenes WHERE deckId = :deckId")
    suspend fun deleteScenes(deckId: String)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertScenes(scenes: List<SceneEntity>)

    @Upsert
    suspend fun upsertCards(cards: List<CardEntity>)

    @Query("UPDATE cards SET active = 0 WHERE deckId = :deckId")
    suspend fun deactivateAll(deckId: String)

    @Query("SELECT * FROM cards WHERE uid = :uid")
    suspend fun card(uid: String): CardEntity?

    /** Seen cards due before [until], earliest first. */
    @Query(
        """
        SELECT r.* FROM review_state r JOIN cards c ON c.uid = r.uid
        WHERE r.deckId = :deckId AND c.active AND r.due <= :until
        ORDER BY r.due LIMIT 1
        """
    )
    suspend fun nextDue(deckId: String, until: Long): ReviewStateEntity?

    /** Seen learning/relearning cards (state 1 or 3) due before [until]. */
    @Query(
        """
        SELECT r.* FROM review_state r JOIN cards c ON c.uid = r.uid
        WHERE r.deckId = :deckId AND c.active AND r.state IN (1, 3) AND r.due <= :until
        ORDER BY r.due LIMIT 1
        """
    )
    suspend fun nextLearningAhead(deckId: String, until: Long): ReviewStateEntity?

    @Query(
        """
        SELECT * FROM cards WHERE deckId = :deckId AND active
          AND uid NOT IN (SELECT uid FROM review_state)
        ORDER BY ord LIMIT 1
        """
    )
    suspend fun nextUnseen(deckId: String): CardEntity?

    @Query("SELECT COUNT(*) FROM review_log WHERE deckId = :deckId AND wasNew AND time >= :since")
    suspend fun newIntroducedSince(deckId: String, since: Long): Int

    @Query("SELECT * FROM review_state WHERE uid = :uid")
    suspend fun state(uid: String): ReviewStateEntity?

    @Upsert
    suspend fun upsertState(state: ReviewStateEntity)

    @Insert
    suspend fun insertLog(log: ReviewLogEntity)

    @Query("DELETE FROM cards WHERE deckId = :deckId")
    suspend fun deleteCards(deckId: String)

    @Query("DELETE FROM review_state WHERE deckId = :deckId")
    suspend fun deleteStates(deckId: String)

    @Query("DELETE FROM review_log WHERE deckId = :deckId")
    suspend fun deleteLogs(deckId: String)
}

@Database(
    entities = [DeckEntity::class, SceneEntity::class, CardEntity::class, ReviewStateEntity::class, ReviewLogEntity::class],
    version = 2,
    autoMigrations = [AutoMigration(from = 1, to = 2)],
)
abstract class AppDb : RoomDatabase() {
    abstract fun dao(): StudyDao

    companion object {
        @Volatile private var instance: AppDb? = null

        fun get(context: Context): AppDb = instance ?: synchronized(this) {
            instance ?: Room.databaseBuilder(context.applicationContext, AppDb::class.java, "mcqs.db")
                .build().also { instance = it }
        }
    }
}
