package io.quizverse.exam.security

import android.app.Activity
import android.app.ActivityManager
import android.app.admin.DevicePolicyManager
import android.content.ComponentName
import android.content.Context
import android.os.Build

/**
 * Manages Android Lock Task Mode (Kiosk Mode) for High-Stakes Institutional Examinations.
 *
 * Supported Modes:
 * 1. App Pinning (Screen Pinning) - User-consented pinning on personal (BYOD) devices.
 * 2. Dedicated Kiosk Mode - Device Owner / Profile Owner managed environments where Home,
 *    Recents, and Status Bar notifications are completely restricted via DevicePolicyManager.
 */
class KioskLockTaskManager(private val activity: Activity) {

    private val activityManager = activity.getSystemService(Context.ACTIVITY_SERVICE) as ActivityManager
    private val devicePolicyManager = activity.getSystemService(Context.DEVICE_POLICY_SERVICE) as? DevicePolicyManager
    private val adminComponent = ComponentName(activity, ExamDeviceAdminReceiver::class.java)

    /**
     * Checks if the app is currently whitelisted as a Lock Task package by the Device Owner.
     */
    fun isLockTaskPermitted(): Boolean {
        if (devicePolicyManager == null) return false
        val pkg = activity.packageName
        return devicePolicyManager.isLockTaskPermitted(pkg)
    }

    /**
     * Checks if Lock Task Mode is currently active.
     */
    fun isLockTaskActive(): Boolean {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            val state = activityManager.lockTaskModeState
            state == ActivityManager.LOCK_TASK_MODE_LOCKED || state == ActivityManager.LOCK_TASK_MODE_PINNED
        } else {
            @Suppress("DEPRECATION")
            activityManager.isInLockTaskMode
        }
    }

    /**
     * Requests entry into Lock Task Mode.
     * On personal devices without Device Owner, this prompts Android's system "Pin this app" screen.
     * On managed devices with Device Owner, this starts immediate, unescapable kiosk lockdown.
     */
    fun enterLockTask(): Boolean {
        return try {
            activity.startLockTask()
            true
        } catch (e: Exception) {
            e.printStackTrace()
            false
        }
    }

    /**
     * Exits Lock Task Mode when examination is submitted or proctor authorizes exit.
     */
    fun exitLockTask(): Boolean {
        return try {
            activity.stopLockTask()
            true
        } catch (e: Exception) {
            e.printStackTrace()
            false
        }
    }

    /**
     * Emergency / Invigilator PIN verification for proctored early exit.
     */
    fun verifyProctorOverridePin(enteredPin: String, expectedPinHash: String): Boolean {
        val digest = java.security.MessageDigest.getInstance("SHA-256")
        val hashBytes = digest.digest(enteredPin.toByteArray(Charsets.UTF_8))
        val hexString = hashBytes.joinToString("") { "%02x".format(it) }
        return hexString.equals(expectedPinHash, ignoreCase = true)
    }
}
