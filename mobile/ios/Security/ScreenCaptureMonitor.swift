import UIKit
import Combine

/**
 * ScreenCaptureMonitor for iOS Secure Examination.
 *
 * Monitors:
 * 1. `UIScreen.capturedDidChangeNotification` (iOS 11+)
 *    Detects system screen recording, AirPlay screen mirroring, and QuickTime recording.
 * 2. `UIApplication.userDidTakeScreenshotNotification`
 *    Detects physical button screenshot combinations (Side + Volume Up).
 */
final class ScreenCaptureMonitor: ObservableObject {

    @Published var isScreenBeingCaptured: Boolean = false
    @Published var screenshotCount: Int = 0

    private var cancellables = Set<AnyCancellable>()
    private let onSecuritySignalDetected: (String, [String: Any]) -> Void

    init(onSecuritySignalDetected: @escaping (String, [String: Any]) -> Void) {
        self.onSecuritySignalDetected = onSecuritySignalDetected
        setupNotificationObservers()
        checkInitialCaptureState()
    }

    private func checkInitialCaptureState() {
        let isCaptured = UIScreen.main.isCaptured
        self.isScreenBeingCaptured = isCaptured
        if isCaptured {
            onSecuritySignalDetected("SCREEN_RECORDING_SIGNAL", [
                "active_at_launch": true,
                "timestamp": ISO8601DateFormatter().string(from: Date())
            ])
        }
    }

    private func setupNotificationObservers() {
        // 1. Screen recording / AirPlay mirroring state changes
        NotificationCenter.default.publisher(for: UIScreen.capturedDidChangeNotification)
            .sink { [weak self] _ in
                guard let self = self else { return }
                let isCaptured = UIScreen.main.isCaptured
                self.isScreenBeingCaptured = isCaptured

                self.onSecuritySignalDetected(
                    isCaptured ? "SCREEN_RECORDING_SIGNAL" : "SCREEN_RECORDING_STOPPED",
                    [
                        "is_captured": isCaptured,
                        "timestamp": ISO8601DateFormatter().string(from: Date())
                    ]
                )
            }
            .store(in: &cancellables)

        // 2. Hardware button screenshot capture
        NotificationCenter.default.publisher(for: UIApplication.userDidTakeScreenshotNotification)
            .sink { [weak self] _ in
                guard let self = self else { return }
                self.screenshotCount += 1

                self.onSecuritySignalDetected(
                    "SCREENSHOT_SIGNAL",
                    [
                        "capture_method": "PHYSICAL_BUTTON_COMBO",
                        "occurrence_count": self.screenshotCount,
                        "timestamp": ISO8601DateFormatter().string(from: Date())
                    ]
                )
            }
            .store(in: &cancellables)
    }
}
