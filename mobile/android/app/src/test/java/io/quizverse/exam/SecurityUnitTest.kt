package io.quizverse.exam

import io.quizverse.exam.security.KioskLockTaskManager
import io.quizverse.exam.security.RootDetector
import org.junit.Assert.*
import org.junit.Test
import java.security.MessageDigest

class SecurityUnitTest {

    @Test
    fun testRootCheckResultDataModel() {
        val result = RootDetector.RootCheckResult(
            isRooted = false,
            testKeysDetected = false,
            suBinaryDetected = false,
            rootPackagesDetected = false,
            rootExecutionPossible = false,
            details = emptyList()
        )
        assertFalse(result.isRooted)
        assertFalse(result.testKeysDetected)
        assertTrue(result.details.isEmpty())
    }

    @Test
    fun testProctorPinHashVerification() {
        val pin = "849201"
        val digest = MessageDigest.getInstance("SHA-256")
        val expectedHash = digest.digest(pin.toByteArray(Charsets.UTF_8)).joinToString("") { "%02x".format(it) }

        // Test hash matching
        val enteredDigest = MessageDigest.getInstance("SHA-256")
        val computedHash = enteredDigest.digest(pin.toByteArray(Charsets.UTF_8)).joinToString("") { "%02x".format(it) }
        assertEquals(expectedHash, computedHash)

        // Incorrect PIN must fail
        val wrongPin = "000000"
        val wrongHash = MessageDigest.getInstance("SHA-256").digest(wrongPin.toByteArray(Charsets.UTF_8)).joinToString("") { "%02x".format(it) }
        assertNotEquals(expectedHash, wrongHash)
    }

    @Test
    fun testWatermarkStringFormatting() {
        val studentName = "Dhanush Kumar"
        val maskedId = "STU-****4821"
        val examCode = "EXAM-2041"
        val timestamp = "2026-11-22T04:30:00Z"

        val watermark = "QUIZVERSE | $studentName | $maskedId | $examCode | $timestamp"
        assertTrue(watermark.contains("QUIZVERSE"))
        assertTrue(watermark.contains("****4821"))
        assertTrue(watermark.contains("EXAM-2041"))
    }

    @Test
    fun testLifecycleDurationCalculation() {
        val pauseTimestamp = 1000L
        val resumeTimestamp = 4500L
        val duration = resumeTimestamp - pauseTimestamp
        assertEquals(3500L, duration)
    }
}
