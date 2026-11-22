package io.quizverse.exam.data.api

import retrofit2.Response
import retrofit2.http.*
import java.util.UUID

/**
 * Retrofit REST API interface connecting QuizVerse Android / iOS client
 * to the shared FastAPI /mobile backend endpoints.
 */
interface QuizVerseMobileApi {

    @POST("api/v1/mobile/devices/register")
    suspend fun registerDevice(
        @Header("Authorization") bearerToken: String,
        @Body request: DeviceRegisterRequest
    ): Response<DeviceRegisterResponse>

    @POST("api/v1/mobile/compatibility")
    suspend fun verifyCompatibility(
        @Header("Authorization") bearerToken: String,
        @Body request: MobileCompatibilityRequest
    ): Response<MobileCompatibilityResponse>

    @POST("api/v1/mobile/attempts/{attemptId}/session")
    suspend fun initExamSession(
        @Path("attemptId") attemptId: UUID,
        @Header("Authorization") bearerToken: String,
        @Body request: MobileExamSessionInitRequest
    ): Response<MobileExamSessionResponse>

    @POST("api/v1/mobile/attempts/{attemptId}/interruptions")
    suspend fun submitInterruption(
        @Path("attemptId") attemptId: UUID,
        @Header("Authorization") bearerToken: String,
        @Body request: MobileInterruptionSubmitRequest
    ): Response<MobileInterruptionSubmitResponse>

    @POST("api/v1/mobile/attempts/{attemptId}/recover")
    suspend fun recoverExamSession(
        @Path("attemptId") attemptId: UUID,
        @Header("Authorization") bearerToken: String,
        @Body request: MobileRecoveryRequest
    ): Response<MobileRecoveryResponse>

    @GET("api/v1/mobile/quizzes/{quizId}/mobile-policy")
    suspend fun getQuizMobilePolicy(
        @Path("quizId") quizId: UUID
    ): Response<MobileQuizSecurityPolicyResponse>
}

// Request & Response Data Transfer Objects matching FastAPI backend schemas
data class DeviceRegisterRequest(
    val device_fingerprint: String,
    val device_model: String,
    val os_platform: String = "android",
    val os_version: String,
    val app_version: String = "1.0.0",
    val app_build_number: Int = 1,
    val device_metadata: Map<String, Any>? = null
)

data class DeviceRegisterResponse(
    val success: Boolean,
    val device_id: UUID,
    val device_fingerprint: String,
    val is_trusted: Boolean,
    val is_blocked: Boolean,
    val registered_at: String,
    val message: String
)

data class MobileCompatibilityRequest(
    val quiz_id: UUID?,
    val os_platform: String = "android",
    val os_version: String,
    val app_version: String = "1.0.0",
    val flag_secure_supported: Boolean = true,
    val root_or_jailbreak_detected: Boolean = false,
    val kiosk_mode_supported: Boolean = true,
    val screen_capture_detection_available: Boolean = true
)

data class MobileCompatibilityResponse(
    val compatible: Boolean,
    val can_proceed: Boolean,
    val overall_status: String,
    val checks: List<Map<String, Any>>,
    val timestamp: String
)

data class MobileExamSessionInitRequest(
    val device_id: UUID? = null,
    val device_fingerprint: String,
    val flag_secure_active: Boolean = true,
    val kiosk_mode_active: Boolean = false,
    val root_detected: Boolean = false
)

data class MobileExamSessionResponse(
    val session_id: UUID,
    val attempt_id: UUID,
    val quiz_id: UUID,
    val remaining_seconds: Int,
    val server_time: String,
    val deadline_at: String?,
    val watermark_text: String,
    val watermark_code: String,
    val flag_secure_enforced: Boolean,
    val message: String
)

data class MobileInterruptionSubmitRequest(
    val interruption_type: String,
    val duration_ms: Long? = null,
    val client_timestamp: String? = null,
    val details: Map<String, Any>? = null
)

data class MobileInterruptionSubmitResponse(
    val success: Boolean,
    val interruption_id: UUID,
    val total_interruptions: Int,
    val action_taken: String,
    val requires_review: Boolean,
    val message: String
)

data class MobileRecoveryRequest(
    val device_fingerprint: String,
    val recovery_reason: String = "APP_RELAUNCH",
    val client_timestamp: String? = null
)

data class MobileRecoveryResponse(
    val success: Boolean,
    val recovered: Boolean,
    val attempt_id: UUID,
    val remaining_seconds: Int,
    val server_time: String,
    val status: String,
    val recovery_count: Int,
    val message: String
)

data class MobileQuizSecurityPolicyResponse(
    val quiz_id: UUID,
    val require_native_app: Boolean,
    val android_secure_mode: Boolean,
    val ios_secure_mode: Boolean,
    val require_kiosk_mode: Boolean,
    val min_android_version: Int,
    val min_ios_version: String,
    val mobile_interruption_policy: String,
    val allow_device_recovery: Boolean,
    val block_rooted_devices: Boolean
)
