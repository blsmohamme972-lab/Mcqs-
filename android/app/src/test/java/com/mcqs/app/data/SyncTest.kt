package com.mcqs.app.data

import android.content.Context
import androidx.test.core.app.ApplicationProvider
import com.mcqs.app.BuildConfig
import kotlinx.coroutines.runBlocking
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import java.io.IOException
import java.net.InetAddress
import java.net.ServerSocket
import java.security.MessageDigest
import kotlin.concurrent.thread

/** Sync against a local HTTP server standing in for the GitHub release. */
@RunWith(RobolectricTestRunner::class)
class SyncTest {
    private val context = ApplicationProvider.getApplicationContext<Context>()
    private val zip = javaClass.classLoader!!.getResourceAsStream("sample.zip")!!.readBytes()
    private val sha = MessageDigest.getInstance("SHA-256").digest(zip).joinToString("") { "%02x".format(it) }
    private val files = java.util.concurrent.ConcurrentHashMap<String, ByteArray>()
    private val hits = java.util.concurrent.ConcurrentHashMap<String, Int>()
    // Minimal HTTP/1.0 file server (com.sun.net.httpserver isn't on the Android unit-test classpath).
    private val socket = ServerSocket(0, 50, InetAddress.getByName("127.0.0.1"))
    private val server = thread(isDaemon = true) {
        while (!socket.isClosed) {
            val client = try { socket.accept() } catch (e: IOException) { break }
            client.use { c ->
                val path = c.getInputStream().bufferedReader().readLine()?.split(" ")?.getOrNull(1) ?: return@use
                hits[path] = (hits[path] ?: 0) + 1
                val body = files[path]
                val out = c.getOutputStream()
                if (body == null) {
                    out.write("HTTP/1.0 404 Not Found\r\nContent-Length: 0\r\n\r\n".toByteArray())
                } else {
                    out.write("HTTP/1.0 200 OK\r\nContent-Length: ${body.size}\r\n\r\n".toByteArray())
                    out.write(body)
                }
                out.flush()
            }
        }
    }
    private val base = "http://127.0.0.1:${socket.localPort}"

    @After
    fun stop() = socket.close()

    // AppDb is a process-wide singleton, so start every test without the sample deck.
    @Before
    fun clean() = runBlocking { Repository(context).deleteDeck("ct-ch17-sample") }

    private fun publish(packageSha: String, appVersion: Int) {
        files["/pkg.zip"] = zip
        files["/index.json"] = """
            {"format":1,
             "app":{"versionCode":$appVersion,"versionName":"0.2.9","url":"$base/MCQs.apk","sha256":"x"},
             "packages":[{"id":"ct-ch17-sample","title":"Ch17","version":1,"url":"$base/pkg.zip",
                          "sha256":"$packageSha","size":${zip.size}}]}
        """.trimIndent().toByteArray()
    }

    @Test
    fun downloadsOnlyChangedPackagesAndReportsAppUpdates() = runBlocking {
        val repo = Repository(context)
        val sync = Sync(context, repo)

        publish(sha, appVersion = BuildConfig.VERSION_CODE + 1)
        val first = sync.run("$base/index.json")
        assertEquals(listOf("Ch17"), first.updated)
        assertEquals(sha, repo.dao.deck("ct-ch17-sample")!!.sha256)
        assertEquals(BuildConfig.VERSION_CODE + 1, first.appUpdate!!.versionCode)

        // Same hash published again: nothing downloaded; same app version: no update offered.
        publish(sha, appVersion = BuildConfig.VERSION_CODE)
        val second = sync.run("$base/index.json")
        assertTrue(second.updated.isEmpty())
        assertNull(second.appUpdate)
        assertEquals(1, hits["/pkg.zip"])
    }

    @Test
    fun rejectsChecksumMismatch() = runBlocking {
        val repo = Repository(context)
        publish("0".repeat(64), appVersion = 0)
        try {
            Sync(context, repo).run("$base/index.json")
            fail("expected checksum failure")
        } catch (e: IOException) {
            assertTrue(e.message!!.contains("checksum"))
        }
        assertNull(repo.dao.deck("ct-ch17-sample"))
    }
}
