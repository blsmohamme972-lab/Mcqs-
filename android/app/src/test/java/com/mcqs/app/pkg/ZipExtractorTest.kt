package com.mcqs.app.pkg

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder
import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream
import java.util.zip.ZipEntry
import java.util.zip.ZipOutputStream

class ZipExtractorTest {
    @get:Rule val tmp = TemporaryFolder()

    private fun zip(vararg files: Pair<String, String>): ByteArrayInputStream {
        val bytes = ByteArrayOutputStream()
        ZipOutputStream(bytes).use { z ->
            for ((name, content) in files) {
                z.putNextEntry(ZipEntry(name))
                z.write(content.toByteArray())
                z.closeEntry()
            }
        }
        return ByteArrayInputStream(bytes.toByteArray())
    }

    private val validManifest = """
        {"format":1,"id":"ch17","title":"Chest trauma","version":2,
         "scenes":[{"id":"ptx","title":"Tension pneumothorax","image":"media/ptx.png",
                    "regions":[{"id":"car","x":0.1,"y":0.6,"w":0.2,"h":0.3}]}],
         "cards":[
           {"id":"ptx.car","type":"occlusion","scene":"ptx","region":"car","front":"Causes?","back":"Rib fracture"},
           {"id":"q1","type":"mcq","front":"Needle site?","options":["2nd ICS MCL","5th ICS"],"answer":0},
           {"id":"b1","type":"basic","front":"Thoracotomy?","back":"Rarely indicated","futureField":1}
         ]}
    """.trimIndent()

    private fun expectInvalid(vararg files: Pair<String, String>, contains: String) {
        val target = tmp.root.resolve("out")
        try {
            ZipExtractor.extract(zip(*files), target)
            fail("expected InvalidPackageException")
        } catch (e: InvalidPackageException) {
            assertTrue("'${e.message}' should contain '$contains'", e.message!!.contains(contains))
        }
        assertFalse("target must be cleaned up", target.exists())
    }

    @Test
    fun extractsValidPackage() {
        val target = tmp.root.resolve("out")
        val m = ZipExtractor.extract(zip("manifest.json" to validManifest, "media/ptx.png" to "png"), target)
        assertEquals("ch17", m.id)
        assertEquals(3, m.cards.size)
        assertTrue(target.resolve("media/ptx.png").isFile)
    }

    @Test
    fun rejectsPathTraversal() = expectInvalid(
        "manifest.json" to validManifest, "../evil.txt" to "x", contains = "unsafe path",
    )

    @Test
    fun rejectsAbsolutePath() = expectInvalid(
        "manifest.json" to validManifest, "/etc/evil" to "x", contains = "unsafe path",
    )

    @Test
    fun rejectsMissingMedia() = expectInvalid("manifest.json" to validManifest, contains = "missing file 'media/ptx.png'")

    @Test
    fun rejectsMissingManifest() = expectInvalid("media/ptx.png" to "png", contains = "manifest.json not found")

    @Test
    fun rejectsBadReferences() = expectInvalid(
        "manifest.json" to validManifest.replace("\"region\":\"car\"", "\"region\":\"nope\"")
            .replace("\"answer\":0", "\"answer\":5"),
        "media/ptx.png" to "png",
        contains = "unknown region 'nope'",
    )

    @Test
    fun rejectsDuplicateIds() = expectInvalid(
        "manifest.json" to validManifest.replace("\"id\":\"b1\"", "\"id\":\"q1\""),
        "media/ptx.png" to "png",
        contains = "duplicate card id 'q1'",
    )
}
