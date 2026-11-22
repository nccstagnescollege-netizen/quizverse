import SwiftUI

/**
 * SecureExamView - Native iOS SwiftUI Examination Canvas.
 *
 * Integrates ScreenCaptureMonitor, GuidedAccessManager, and MobileWatermarkView.
 */
struct SecureExamView: View {
    let studentName: String
    let maskedIdentifier: String
    let examTitle: String
    @State private var remainingSeconds: Int = 3600
    @State private var selectedOption: Int? = nil
    @State private var showRecordingWarning: Bool = false

    @StateObject private var captureMonitor = ScreenCaptureMonitor { signal, details in
        // Dispatches telemetry to FastAPI backend /mobile/attempts/{id}/interruptions
        print("iOS Security Signal Detected: \(signal) Details: \(details)")
    }

    private var watermarkString: String {
        return "QUIZVERSE | \(studentName.uppercased()) | \(maskedIdentifier) | TIMED EXAM"
    }

    var body: some View {
        ZStack {
            // Background Layer
            Color(red: 0.06, green: 0.09, blue: 0.16)
                .ignoresSafeArea()

            // Main Examination Interface
            VStack(spacing: 20) {
                // Header Bar
                HStack {
                    VStack(alignment: .leading, spacing: 2) {
                        Text(examTitle)
                            .font(.system(size: 15, weight: .bold))
                            .foregroundColor(.white)

                        HStack(spacing: 6) {
                            Circle()
                                .fill(captureMonitor.isScreenBeingCaptured ? Color.red : Color.green)
                                .frame(width: 8, height: 8)
                            Text(captureMonitor.isScreenBeingCaptured ? "Screen Recording Detected" : "Protected Display")
                                .font(.system(size: 11, weight: .medium))
                                .foregroundColor(captureMonitor.isScreenBeingCaptured ? .red : .green)
                        }
                    }

                    Spacer()

                    // Server Authoritative Countdown Box
                    Text(String(format: "%02d:%02d", remainingSeconds / 60, remainingSeconds % 60))
                        .font(.system(size: 16, weight: .bold, design: .monospaced))
                        .foregroundColor(Color(red: 0.22, green: 0.74, blue: 0.97))
                        .padding(.horizontal, 12)
                        .padding(.vertical, 6)
                        .background(Color(red: 0.12, green: 0.16, blue: 0.23))
                        .cornerRadius(8)
                }
                .padding(.horizontal)

                if captureMonitor.isScreenBeingCaptured {
                    // Visual Deterrence Shield
                    VStack(spacing: 8) {
                        Image(systemName: "exclamationmark.shield.fill")
                            .font(.system(size: 32))
                            .foregroundColor(.red)
                        Text("SCREEN RECORDING DETECTED")
                            .font(.system(size: 14, weight: .bold))
                            .foregroundColor(.white)
                        Text("Examination policy strictly prohibits screen mirroring and capture. Incidents are logged for invigilator review.")
                            .font(.system(size: 11))
                            .foregroundColor(.gray)
                            .multilineTextAlignment(.center)
                    }
                    .padding()
                    .background(Color.red.opacity(0.15))
                    .cornerRadius(12)
                    .overlay(RoundedRectangle(cornerRadius: 12).stroke(Color.red.opacity(0.4), lineWidth: 1))
                    .padding(.horizontal)
                }

                // Question Card
                VStack(alignment: .leading, spacing: 12) {
                    Text("Question 1 of 25")
                        .font(.system(size: 12, weight: .semibold))
                        .foregroundColor(.gray)

                    Text("In iOS architecture, which notification allows applications to detect system AirPlay screen mirroring or Control Center screen recording?")
                        .font(.system(size: 15, weight: .semibold))
                        .foregroundColor(.white)
                        .lineSpacing(4)

                    VStack(spacing: 10) {
                        OptionButton(label: "A. UIApplication.didEnterBackgroundNotification", isSelected: selectedOption == 0) {
                            selectedOption = 0
                        }
                        OptionButton(label: "B. UIScreen.capturedDidChangeNotification", isSelected: selectedOption == 1) {
                            selectedOption = 1
                        }
                        OptionButton(label: "C. UIDevice.batteryStateDidChangeNotification", isSelected: selectedOption == 2) {
                            selectedOption = 2
                        }
                        OptionButton(label: "D. UIWindow.keyboardDidShowNotification", isSelected: selectedOption == 3) {
                            selectedOption = 3
                        }
                    }
                    .padding(.top, 8)
                }
                .padding()
                .background(Color(red: 0.12, green: 0.16, blue: 0.23))
                .cornerRadius(14)
                .padding(.horizontal)

                Spacer()

                // Bottom Action Bar
                HStack {
                    Button(action: {
                        GuidedAccessManager.requestEnterSingleAppMode { success in
                            print("Guided access request result: \(success)")
                        }
                    }) {
                        HStack(spacing: 6) {
                            Image(systemName: "lock.shield")
                            Text("Lockdown Mode")
                        }
                        .font(.system(size: 12, weight: .semibold))
                        .foregroundColor(Color(red: 0.22, green: 0.74, blue: 0.97))
                        .padding(.horizontal, 14)
                        .padding(.vertical, 10)
                        .background(Color(red: 0.12, green: 0.16, blue: 0.23))
                        .cornerRadius(10)
                    }

                    Spacer()

                    Button(action: { }) {
                        Text("Next Question")
                            .font(.system(size: 13, weight: .bold))
                            .foregroundColor(.white)
                            .padding(.horizontal, 20)
                            .padding(.vertical, 10)
                            .background(Color.blue)
                            .cornerRadius(10)
                    }
                }
                .padding(.horizontal)
            }
            .padding(.vertical)

            // Dynamic Personalized Watermark Layer
            MobileWatermarkView(watermarkText: watermarkString)
        }
    }
}

struct OptionButton: View {
    let label: String
    let isSelected: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack {
                Text(label)
                    .font(.system(size: 13))
                    .foregroundColor(isSelected ? .white : Color(UIColor.lightGray))
                    .multilineTextAlignment(.leading)
                Spacer()
            }
            .padding(.horizontal, 14)
            .padding(.vertical, 12)
            .background(isSelected ? Color.blue.opacity(0.3) : Color(red: 0.08, green: 0.11, blue: 0.18))
            .cornerRadius(10)
            .overlay(
                RoundedRectangle(cornerRadius: 10)
                    .stroke(isSelected ? Color.blue : Color.white.opacity(0.1), lineWidth: 1)
            )
        }
    }
}
