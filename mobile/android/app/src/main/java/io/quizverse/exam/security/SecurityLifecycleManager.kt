package io.quizverse.exam.security

import android.app.Activity
import android.content.Context
import android.telephony.PhoneStateListener
import android.telephony.TelephonyCallback
import android.telephony.TelephonyManager
import android.os.Build
import androidx.lifecycle.DefaultLifecycleObserver
import androidx.lifecycle.LifecycleOwner

/**
 * Monitors Android lifecycle transitions and phone hardware interruptions during an active examination.
 *
 * Detects:
 * - Activity background / defocus events (`onPause`, `onStop`)
 * - Activity restoration (`onResume`)
 * - Incoming cellular calls / ringing interruptions via TelephonyManager
 */
class SecurityLifecycleManager(
    private val activity: Activity,
    private val onInterruptionDetected: (type: String, details: Map<String, Any>) -> Unit
) : DefaultLifecycleObserver {

    private val telephonyManager = activity.getSystemService(Context.TELEPHONY_SERVICE) as? TelephonyManager
    private var isCallInProgress = false
    private var lastBackgroundTimestamp = 0L

    init {
        registerPhoneStateListener()
    }

    override fun onResume(owner: LifecycleOwner) {
        super.onResume(owner)
        val now = System.currentTimeMillis()
        val durationMs = if (lastBackgroundTimestamp > 0) now - lastBackgroundTimestamp else 0L
        lastBackgroundTimestamp = 0L

        onInterruptionDetected(
            "NATIVE_APP_FOREGROUND",
            mapOf(
                "action" to "RESUME",
                "duration_ms" to durationMs,
                "timestamp" to now
            )
        )
    }

    override fun onPause(owner: LifecycleOwner) {
        super.onPause(owner)
        lastBackgroundTimestamp = System.currentTimeMillis()
        onInterruptionDetected(
            "NATIVE_APP_BACKGROUND",
            mapOf(
                "action" to "PAUSE",
                "timestamp" to lastBackgroundTimestamp,
                "is_call_in_progress" to isCallInProgress
            )
        )
    }

    override fun onStop(owner: LifecycleOwner) {
        super.onStop(owner)
        onInterruptionDetected(
            "NATIVE_APP_STOP",
            mapOf(
                "action" to "STOP",
                "timestamp" to System.currentTimeMillis()
            )
        )
    }

    private fun registerPhoneStateListener() {
        if (telephonyManager == null) return

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            val callback = object : TelephonyCallback(), TelephonyCallback.CallStateListener {
                override fun onCallStateChanged(state: Int) {
                    handleCallState(state)
                }
            }
            try {
                telephonyManager.registerTelephonyCallback(activity.mainExecutor, callback)
            } catch (_: SecurityException) {
                // Permission not granted or restricted
            }
        } else {
            @Suppress("DEPRECATION")
            val listener = object : PhoneStateListener() {
                @Deprecated("Deprecated in Java")
                override fun onCallStateChanged(state: Int, phoneNumber: String?) {
                    handleCallState(state)
                }
            }
            try {
                @Suppress("DEPRECATION")
                telephonyManager.listen(listener, PhoneStateListener.LISTEN_CALL_STATE)
            } catch (_: SecurityException) {
                // Ignore
            }
        }
    }

    private fun handleCallState(state: Int) {
        when (state) {
            TelephonyManager.CALL_STATE_RINGING -> {
                isCallInProgress = true
                onInterruptionDetected(
                    "INCOMING_PHONE_CALL",
                    mapOf("state" to "RINGING", "timestamp" to System.currentTimeMillis())
                )
            }
            TelephonyManager.CALL_STATE_OFFHOOK -> {
                isCallInProgress = true
                onInterruptionDetected(
                    "PHONE_CALL_ACTIVE",
                    mapOf("state" to "OFFHOOK", "timestamp" to System.currentTimeMillis())
                )
            }
            TelephonyManager.CALL_STATE_IDLE -> {
                if (isCallInProgress) {
                    isCallInProgress = false
                    onInterruptionDetected(
                        "PHONE_CALL_DISCONNECTED",
                        mapOf("state" to "IDLE", "timestamp" to System.currentTimeMillis())
                    )
                }
            }
        }
    }
}
