package com.mcqs.app.data

import com.mcqs.app.pkg.CardType
import com.mcqs.app.srs.formatInterval

/**
 * "Copy for GPT": the next cards of a deck as one block of text to paste into a ChatGPT (or Claude) voice chat. The
 * examiner reads each question aloud while the owner follows the same cards in the app and rates them there, so the
 * schedule stays in the app.
 */
object GptCopy {
    fun text(deckTitle: String, cards: List<Repository.BatchCard>, now: Long): String = buildString {
        appendLine("You are my oral examiner (a viva) in cardiothoracic surgery, in a VOICE call. Deck: $deckTitle.")
        appendLine("Ask me these ${cards.size} questions one at a time, in this order. I follow the same questions in my app.")
        appendLine("- Read only the question. Never read the answer or the key points before I have answered.")
        appendLine("- Wait for my whole answer. I may answer in English or Arabic: judge the content.")
        appendLine("- Then say in one or two sentences what was right and what was missing, from the answer below,")
        appendLine("  and say which button I should press in my app: Again (wrong or blank), Hard (partial or needed a")
        appendLine("  hint), Good (right but slow or incomplete), Easy (complete and at once). Then the next question.")
        appendLine("- At the end, list every number with its button, so I can check my ratings.")
        appendLine()
        cards.forEachIndexed { i, (card, srs) ->
            val last = srs?.lastReview
            val tag = if (srs == null || last == null) "new"
            else "review, last interval ${formatInterval(srs.due - last)}" +
                if (srs.due < now) ", overdue ${formatInterval(now - srs.due)}" else ""
            appendLine("${i + 1}. [$tag] Q: ${card.front}")
            card.back?.let { appendLine("   Answer: $it") }
            card.explanation?.let { appendLine("   $it") }
            if (card.type == CardType.MCQ) appendLine("   (multiple choice in the app: ask it as an open question)")
        }
    }.trimEnd()
}
