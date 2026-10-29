package com.mcqs.app.pkg

import java.io.File
import java.io.InputStream
import java.util.zip.ZipInputStream

/**
 * Extracts a content zip into [target] (which must not exist yet) and returns its parsed manifest.
 * Rejects path traversal ("zip slip"), absolute paths, oversized archives and invalid manifests.
 * On any failure [target] is deleted.
 */
object ZipExtractor {
    const val MAX_TOTAL_BYTES = 2L * 1024 * 1024 * 1024
    const val MAX_ENTRIES = 20_000

    fun extract(input: InputStream, target: File): Manifest {
        require(!target.exists()) { "target already exists: $target" }
        target.mkdirs()
        val root = target.canonicalFile
        try {
            var total = 0L
            var count = 0
            ZipInputStream(input.buffered()).use { zip ->
                val buf = ByteArray(64 * 1024)
                while (true) {
                    val entry = zip.nextEntry ?: break
                    if (++count > MAX_ENTRIES) throw InvalidPackageException("too many files in zip")
                    val name = entry.name.replace('\\', '/')
                    if (name.startsWith("/") || name.split('/').any { it == ".." }) {
                        throw InvalidPackageException("unsafe path in zip: ${entry.name}")
                    }
                    val out = File(root, name).canonicalFile
                    if (!out.path.startsWith(root.path + File.separator)) {
                        throw InvalidPackageException("unsafe path in zip: ${entry.name}")
                    }
                    if (entry.isDirectory) {
                        out.mkdirs()
                        continue
                    }
                    out.parentFile?.mkdirs()
                    out.outputStream().use { os ->
                        while (true) {
                            val n = zip.read(buf)
                            if (n < 0) break
                            total += n
                            if (total > MAX_TOTAL_BYTES) throw InvalidPackageException("zip too large")
                            os.write(buf, 0, n)
                        }
                    }
                }
            }
            val manifestFile = File(root, "manifest.json")
            val mcards = File(root, Mcards.MANIFEST_NAME)
            val manifest = try {
                when {
                    manifestFile.isFile -> manifestJson.decodeFromString(Manifest.serializer(), manifestFile.readText())
                    mcards.isFile -> Mcards.convert(mcards.readText()) { path -> File(root, path).takeIf { isSafeFile(root, path) }?.readBytes() }
                    else -> throw InvalidPackageException("manifest.json not found at zip root (nor ${Mcards.MANIFEST_NAME})")
                }
            } catch (e: InvalidPackageException) {
                throw e
            } catch (e: Exception) {
                throw InvalidPackageException("manifest is not valid: ${e.message}")
            }
            val errors = manifest.validate { path -> isSafeFile(root, path) }
            if (errors.isNotEmpty()) throw InvalidPackageException(errors.take(10).joinToString("\n"))
            return manifest
        } catch (e: Throwable) {
            target.deleteRecursively()
            throw e
        }
    }

    private fun isSafeFile(root: File, path: String): Boolean {
        val f = File(root, path).canonicalFile
        return f.path.startsWith(root.path + File.separator) && f.isFile
    }
}
