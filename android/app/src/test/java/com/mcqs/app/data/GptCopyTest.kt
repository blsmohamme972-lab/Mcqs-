package com.mcqs.app.data

import com.mcqs.app.srs.CardState
import com.mcqs.app.srs.DAY_MS
import com.mcqs.app.srs.SrsCard
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class GptCopyTest {
    private fun card(id: String, ord: Int) = CardEntity(
        uid = "d/$id", deckId = "d", type = "basic", front = "Question $id?", back = "Answer $id.", sceneId = null,
        regionId = null, image = null, optionsJson = "[]", answer = null, explanation = "Key points: a; b",
        source = "Ch1 p2", tags = "", ord = ord, active = true,
    )

    @Test
    fun listsEveryQuestionWithItsAnswerAndInterval() {
        val now = 100 * DAY_MS
        val due = SrsCard(CardState.Review, null, 5.0, 5.0, due = now - 2 * DAY_MS, lastReview = now - 9 * DAY_MS)
        val text = GptCopy.text("Ch1 viva", listOf(Repository.BatchCard(card("a", 0), due), Repository.BatchCard(card("b", 1), null)), now)
        assertTrue(text.startsWith("You are my oral examiner"))
        assertTrue(text.contains("these 2 questions"))
        assertTrue(text.contains("1. [review, last interval 7d, overdue 2d] Q: Question a?\n   Answer: Answer a.\n   Key points: a; b"))
        assertTrue(text.contains("2. [new] Q: Question b?"))
        assertEquals(2, Regex("""(?m)^\d+\. \[""").findAll(text).count())
        assertFalse(text.endsWith("\n"))
    }
}
