package com.mcqs.app.pkg

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Test
import java.security.MessageDigest

class McardsTest {
    private val html = "<html>lesson</html>"
    private val sha = MessageDigest.getInstance("SHA-256").digest(html.toByteArray()).joinToString("") { "%02x".format(it) }

    private fun manifest(hash: String = sha) = """
        {"package_type":"kafu-motioncards","schema_version":1,"package_id":"CH17-TRAUMA","package_revision":3,
         "animations":[{"qid":"Q000000001","entry_path":"entries/Q000000001.html","entry_sha256":"$hash","duration_ms":45000,
           "final_panel":{"takeaway":"Needle goes in the 2nd space","correct_answer_statements":["2nd ICS MCL"]}}]}
    """.trimIndent()

    @Test fun convertsLessonsToScenes() {
        val m = Mcards.convert(manifest()) { html.toByteArray() }
        assertEquals("CH17-TRAUMA", m.id)
        assertEquals(3, m.version)
        assertTrue(m.cards.isEmpty())
        val s = m.scenes.single()
        assertEquals("Q000000001", s.id)
        assertEquals("entries/Q000000001.html", s.entry)
        assertEquals(45000, s.durationMs)
        assertEquals("Needle goes in the 2nd space", s.title)
    }

    @Test fun rejectsTamperedEntry() {
        try { Mcards.convert(manifest("0".repeat(64))) { html.toByteArray() }; fail() }
        catch (e: InvalidPackageException) { assertTrue(e.message!!.contains("checksum")) }
    }

    @Test fun convertsBookLessons() {
        val text = """{"package_type":"mcqs-booklessons","schema_version":1,"package_id":"BOOK-CH01","package_revision":2,"book":"CTS 2e","chapter":1,
          "chapter_title":"Preoperative assessment","lessons":[{"id":"ch01-02-angina","qid":"Q901020000","title":"Angina","pages":"2","takeaway":"Grade it",
          "duration_ms":62000,"entry_path":"entries/Q901020000.html","entry_sha256":"$sha"}]}"""
        val m = Mcards.convertBook(text) { html.toByteArray() }
        assertEquals("BOOK-CH01", m.id); assertEquals("Ch 1 · Preoperative assessment", m.title); assertEquals(2, m.version)
        val s = m.scenes.single(); assertEquals("ch01-02-angina", s.id); assertEquals("p 2", s.source); assertEquals(62000, s.durationMs)
    }
}
