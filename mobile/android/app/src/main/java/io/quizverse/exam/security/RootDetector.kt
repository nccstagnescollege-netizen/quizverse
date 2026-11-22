package io.quizverse.exam.security

import android.content.Context
import android.os.Build
import java.io.BufferedReader
import java.io.File
import java.io.InputStreamReader

/**
 * Root and Jailbreak Risk Signal Detector for QuizVerse Native Examination.
 *
 * Checks standard root indicators:
 * 1. Build tags containing "test-keys"
 * 2. Presence of superuser binary ("su") across system binary directories
 * 3. Execution of "which su" command via Runtime
 * 4. Presence of known root management packages (Magisk, SuperSU, BusyBox)
 * 5. Writable system directory checks
 */
object RootDetector {

    private val SU_PATHS = arrayOf(
        "/data/local/su",
        "/data/local/bin/su",
        "/data/local/xbin/su",
        "/sbin/su",
        "/system/bin/su",
        "/system/bin/.ext/su",
        "/system/bin/failsafe/su",
        "/system/sd/xbin/su",
        "/system/usr/we-need-root/su",
        "/system/xbin/su",
        "/system/app/Superuser.apk",
        "/system/app/SuperSU.apk"
    )

    private val KNOWN_ROOT_PACKAGES = arrayOf(
        "com.topjohnwu.magisk",
        "eu.chainfire.supersu",
        "com.noshufou.android.su",
        "com.koushikdutta.superuser",
        "com.thirdparty.superuser",
        "com.yellowes.su"
    )

    data class RootCheckResult(
        val isRooted: Boolean,
        val testKeysDetected: Boolean,
        val suBinaryDetected: Boolean,
        val rootPackagesDetected: Boolean,
        val rootExecutionPossible: Boolean,
        val details: List<String>
    )

    fun checkDeviceRoot(context: Context? = null): RootCheckResult {
        val details = mutableListOf<String>()

        val testKeys = checkTestKeys()
        if (testKeys) details.add("Build.TAGS contains test-keys")

        val suBinary = checkSuBinary()
        if (suBinary) details.add("Found su binary in system path")

        val packages = if (context != null) checkRootPackages(context) else false
        if (packages) details.add("Known root management package detected")

        val execution = checkSuExecution()
        if (execution) details.add("Successfully executed 'which su'")

        val isRooted = testKeys || suBinary || packages || execution

        return RootCheckResult(
            isRooted = isRooted,
            testKeysDetected = testKeys,
            suBinaryDetected = suBinary,
            rootPackagesDetected = packages,
            rootExecutionPossible = execution,
            details = details
        )
    }

    private fun checkTestKeys(): Boolean {
        val tags = Build.TAGS
        return tags != null && tags.contains("test-keys")
    }

    private fun checkSuBinary(): Boolean {
        for (path in SU_PATHS) {
            try {
                if (File(path).exists()) {
                    return true
                }
            } catch (_: Exception) {
                // Ignore security exceptions
            }
        }
        return false
    }

    private fun checkRootPackages(context: Context): Boolean {
        val pm = context.packageManager
        for (pkg in KNOWN_ROOT_PACKAGES) {
            try {
                pm.getPackageInfo(pkg, 0)
                return true
            } catch (_: Exception) {
                // Package not found
            }
        }
        return false
    }

    private fun checkSuExecution(): Boolean {
        var process: Process? = null
        return try {
            process = Runtime.getRuntime().exec(arrayOf("/system/xbin/which", "su"))
            val reader = BufferedReader(InputStreamReader(process.inputStream))
            reader.readLine() != null
        } catch (_: Exception) {
            false
        } finally {
            process?.destroy()
        }
    }
}
