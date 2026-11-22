import UIKit

/**
 * SecureExamSceneDelegate for iOS Examination Privacy Blanking.
 *
 * When an iOS user swipes up into the App Switcher or an incoming phone call banner appears,
 * iOS automatically captures a snapshot image of the current screen to show in the multitasking switcher.
 *
 * This SceneDelegate blankets the window with a solid privacy shield before the snapshot is taken,
 * ensuring no examination questions or answers are ever exposed in system multitasking caches.
 */
class SecureExamSceneDelegate: UIResponder, UIWindowSceneDelegate {

    var window: UIWindow?
    private var privacyBlankingView: UIView?

    func sceneWillResignActive(_ scene: UIScene) {
        // App is losing focus (incoming call banner, notification shade, or multitasking swipe)
        showPrivacyBlankingOverlay()
    }

    func sceneDidBecomeActive(_ scene: UIScene) {
        // App has regained full foreground focus
        hidePrivacyBlankingOverlay()
    }

    func sceneDidEnterBackground(_ scene: UIScene) {
        // App entered background; ensure privacy blanket persists
        showPrivacyBlankingOverlay()
    }

    private func showPrivacyBlankingOverlay() {
        guard let window = self.window, privacyBlankingView == nil else { return }

        let blanking = UIView(frame: window.bounds)
        blanking.backgroundColor = UIColor(red: 0.06, green: 0.09, blue: 0.16, alpha: 1.0) // Slate-900

        let label = UILabel()
        label.text = "QUIZVERSE SECURE EXAMINATION ACTIVE\nContent masked for security"
        label.textColor = .white
        label.textAlignment = .center
        label.numberOfLines = 2
        label.font = UIFont.monospacedSystemFont(ofSize: 14, weight: .bold)
        label.translatesAutoresizingMaskIntoConstraints = false

        blanking.addSubview(label)
        NSLayoutConstraint.activate([
            label.centerXAnchor.constraint(equalTo: blanking.centerXAnchor),
            label.centerYAnchor.constraint(equalTo: blanking.centerYAnchor),
            label.leadingAnchor.constraint(greaterThanOrEqualTo: blanking.leadingAnchor, constant: 20),
            label.trailingAnchor.constraint(lessThanOrEqualTo: blanking.trailingAnchor, constant: -20)
        ])

        window.addSubview(blanking)
        self.privacyBlankingView = blanking
    }

    private func hidePrivacyBlankingOverlay() {
        privacyBlankingView?.removeFromSuperview()
        privacyBlankingView = nil
    }
}
