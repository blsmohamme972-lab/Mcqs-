package com.mcqs.app.data

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.provider.Settings
import androidx.core.content.FileProvider
import com.mcqs.app.BuildConfig
import com.mcqs.app.pkg.manifestJson
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.Serializable
import java.io.File
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL
import java.security.MessageDigest

/** `index.json` published with every release (tools/make_index.py). */
@Serializable
data class RemoteIndex(val format: Int, val app: RemoteApp? = null, val packages: List<RemotePackage> = emptyList())

@Serializable
data class RemoteApp(val versionCode: Int, val versionName: String, val url: String, val sha256: String)

@Serializable
data class RemotePackage(val id: String, val title: String, val version: Int, val url: String, val sha256: String, val size: Long)

/** The release (or its index.json) doesn't exist yet: nothing has been published. */
class NotPublishedException(url: String) : IOException("nothing published at $url")

data class SyncResult(val updated: List<String>, val appUpdate: RemoteApp?)

/**
 * Pulls content and app updates from the GitHub release that CI publishes on every push.
 * A package is downloaded only when its sha256 differs from the installed one.
 */
class Sync(private val context: Context, private val repo: Repository) {
    companion object {
        /** Tests switch this off so they never touch the network. */
        @Volatile var enabled = true
    }

    suspend fun run(indexUrl: String = BuildConfig.UPDATE_INDEX_URL): SyncResult = withContext(Dispatchers.IO) {
        val index = manifestJson.decodeFromString(RemoteIndex.serializer(), download(indexUrl).decodeToString())
        val installed = repo.dao.allDecks().associate { it.id to it.sha256 }
        val updated = mutableListOf<String>()
        for (p in index.packages) {
            if (installed[p.id] == p.sha256) continue
            val file = File(context.cacheDir, "sync-${p.id}.zip")
            try {
                downloadTo(p.url, file, p.sha256)
                repo.importZip(Uri.fromFile(file))
                updated += p.title
            } finally {
                file.delete()
            }
        }
        val app = index.app?.takeIf { it.versionCode > BuildConfig.VERSION_CODE }
        SyncResult(updated, app)
    }

    /** Downloads the new APK and opens the system installer (Android always asks the user to confirm). */
    suspend fun installApp(app: RemoteApp) {
        if (!context.packageManager.canRequestPackageInstalls()) {
            context.startActivity(
                Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES, Uri.parse("package:${context.packageName}"))
                    .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            )
            return
        }
        val dir = File(context.cacheDir, "updates").apply { mkdirs() }
        val apk = File(dir, "MCQs-${app.versionName}.apk")
        withContext(Dispatchers.IO) { downloadTo(app.url, apk, app.sha256) }
        val uri = FileProvider.getUriForFile(context, "${context.packageName}.files", apk)
        context.startActivity(
            Intent(Intent.ACTION_VIEW)
                .setDataAndType(uri, "application/vnd.android.package-archive")
                .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_ACTIVITY_NEW_TASK)
        )
    }

    private fun open(url: String): HttpURLConnection {
        val conn = URL(url).openConnection() as HttpURLConnection
        conn.connectTimeout = 15_000
        conn.readTimeout = 30_000
        conn.instanceFollowRedirects = true
        val code = conn.responseCode
        if (code == 404) throw NotPublishedException(url)
        if (code != 200) throw IOException("HTTP $code for $url")
        return conn
    }

    private fun download(url: String): ByteArray = open(url).inputStream.use { it.readBytes() }

    private fun downloadTo(url: String, target: File, expectedSha: String) {
        val digest = MessageDigest.getInstance("SHA-256")
        open(url).inputStream.use { input ->
            target.outputStream().use { out ->
                val buf = ByteArray(64 * 1024)
                while (true) {
                    val n = input.read(buf)
                    if (n < 0) break
                    digest.update(buf, 0, n)
                    out.write(buf, 0, n)
                }
            }
        }
        val sha = digest.digest().joinToString("") { "%02x".format(it) }
        if (sha != expectedSha) {
            target.delete()
            throw IOException("checksum mismatch for $url")
        }
    }
}
