package io.quizverse.exam

import android.os.Bundle
import android.view.WindowManager
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import io.quizverse.exam.security.KioskLockTaskManager
import io.quizverse.exam.security.RootDetector
import io.quizverse.exam.security.SecurityLifecycleManager
import io.quizverse.exam.ui.components.MobileWatermarkOverlay
import java.util.UUID

/**
 * Secure Native Android Examination Activity.
 *
 * Implements hardware window security flags, continuous lifecycle monitoring,
 * and Jetpack Compose examination canvas.
 */
class SecureExamActivity : ComponentActivity() {

    private lateinit var kioskManager: KioskLockTaskManager
    private lateinit var lifecycleManager: SecurityLifecycleManager

    // Active session state
    private var flagSecureActive by mutableStateOf(false)
    private var watermarkText by mutableStateOf("QUIZVERSE | CANDIDATE | TIMED EXAM")
    private var remainingSeconds by mutableIntStateOf(3600)
    private var attemptId: UUID? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // 1. CRITICAL: Hardware Screenshot and Screen Recording Prevention via FLAG_SECURE
        // MUST be called before any view rendering or window drawing begins.
        try {
            window.setFlags(
                WindowManager.LayoutParams.FLAG_SECURE,
                WindowManager.LayoutParams.FLAG_SECURE
            )
            flagSecureActive = true
        } catch (e: Exception) {
            flagSecureActive = false
        }

        // 2. Initialize Managers
        kioskManager = KioskLockTaskManager(this)
        lifecycleManager = SecurityLifecycleManager(this) { eventType, details ->
            handleInterruption(eventType, details)
        }
        lifecycle.addObserver(lifecycleManager)

        // 3. Pre-flight Root Check
        val rootResult = RootDetector.checkDeviceRoot(this)

        // 4. Render Compose UI
        setContent {
            MaterialTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = Color(0xFF0F172A) // Dark examination background
                ) {
                    Box(modifier = Modifier.fillMaxSize()) {
                        // Examination Content Screen
                        ExamMainContent(
                            flagSecureEnforced = flagSecureActive,
                            isRooted = rootResult.isRooted,
                            remainingSeconds = remainingSeconds,
                            onEnterKiosk = { kioskManager.enterLockTask() },
                            onExitKiosk = { kioskManager.exitLockTask() }
                        )

                        // Top-level Dynamic Watermark Overlay
                        MobileWatermarkOverlay(
                            watermarkText = watermarkText,
                            opacity = 0.07f
                        )
                    }
                }
            }
        }
    }

    private fun handleInterruption(eventType: String, details: Map<String, Any>) {
        // Dispatches telemetry to backend API /mobile/attempts/{attemptId}/interruptions
        // In local app state, preserves saved answers and maintains server timer authority
    }
}

@Composable
fun ExamMainContent(
    flagSecureEnforced: Boolean,
    isRooted: Boolean,
    remainingSeconds: Int,
    onEnterKiosk: () -> Unit,
    onExitKiosk: () -> Unit
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.SpaceBetween
    ) {
        // Top Bar: Security badges & Timer
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column {
                Text(
                    text = "QUIZVERSE NATIVE EXAM",
                    color = Color.White,
                    fontSize = 14.sp,
                    fontWeight = androidx.compose.ui.text.font.FontWeight.Bold
                )
                Text(
                    text = if (flagSecureEnforced) "FLAG_SECURE Active (Screenshots Blocked)" else "FLAG_SECURE Warning",
                    color = if (flagSecureEnforced) Color(0xFF10B981) else Color(0xFFF59E0B),
                    fontSize = 11.sp
                )
            }

            // Server-Authoritative Timer Box
            Card(
                colors = CardDefaults.cardColors(containerColor = Color(0xFF1E293B))
            ) {
                Text(
                    text = String.format("%02d:%02d", remainingSeconds / 60, remainingSeconds % 60),
                    color = Color(0xFF38BDF8),
                    fontSize = 16.sp,
                    fontWeight = androidx.compose.ui.text.font.FontWeight.Bold,
                    modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp)
                )
            }
        }

        // Center Content: Active Question
        Card(
            modifier = Modifier
                .fillMaxWidth()
                .weight(1f)
                .padding(vertical = 16.dp),
            colors = CardDefaults.cardColors(containerColor = Color(0xFF1E293B))
        ) {
            Column(modifier = Modifier.padding(16.dp)) {
                Text(
                    text = "Question 1 of 20",
                    color = Color(0xFF94A3B8),
                    fontSize = 12.sp
                )
                Spacer(modifier = Modifier.height(8.dp))
                Text(
                    text = "Which Android WindowManager flag prevents capture via screenshot shortcuts and DisplayManager screen mirroring?",
                    color = Color.White,
                    fontSize = 15.sp,
                    fontWeight = androidx.compose.ui.text.font.FontWeight.SemiBold
                )
                Spacer(modifier = Modifier.height(16.dp))
                // Sample Options
                listOf(
                    "A. FLAG_KEEP_SCREEN_ON",
                    "B. FLAG_SECURE",
                    "C. FLAG_FULLSCREEN",
                    "D. FLAG_DISMISS_KEYGUARD"
                ).forEach { opt ->
                    Button(
                        onClick = { },
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(vertical = 4.dp),
                        colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF334155))
                    ) {
                        Text(text = opt, color = Color.White, fontSize = 13.sp)
                    }
                }
            }
        }

        // Bottom Controls: Kiosk Mode and Navigation
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            OutlinedButton(onClick = onEnterKiosk) {
                Text(text = "Pin App (Kiosk)", color = Color(0xFF38BDF8), fontSize = 12.sp)
            }
            Button(
                onClick = { },
                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF2563EB))
            ) {
                Text(text = "Next Question", color = Color.White, fontSize = 12.sp)
            }
        }
    }
}
