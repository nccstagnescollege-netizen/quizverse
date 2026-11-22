import UIKit

/**
 * Manages iOS Guided Access and Autonomous Single App Mode (ASAM).
 *
 * In institutional / supervised school iPads or enterprise iPhones with an MDM profile
 * whitelisting the app's bundle identifier for ASAM (com.apple.developer.assessment-mode),
 * the app can programmatically enter and leave Guided Access without manual Triple-Click.
 */
final class GuidedAccessManager {

    /**
     * Checks if Guided Access / Single App Mode is currently active on this iOS device.
     */
    static var isGuidedAccessActive: Bool {
        return UIAccessibility.isGuidedAccessEnabled
    }

    /**
     * Programmatically requests entry into Autonomous Single App Mode (ASAM).
     * Requires MDM profile authorization or Supervised Device Mode.
     */
    static func requestEnterSingleAppMode(completion: @escaping (Bool) -> Void) {
        if #available(iOS 12.0, *) {
            UIAccessibility.requestGuidedAccessSession(enabled: true) { success in
                DispatchQueue.main.async {
                    completion(success)
                }
            }
        } else {
            completion(false)
        }
    }

    /**
     * Programmatically releases Single App Mode upon legitimate examination submission.
     */
    static func requestExitSingleAppMode(completion: @escaping (Bool) -> Void) {
        if #available(iOS 12.0, *) {
            UIAccessibility.requestGuidedAccessSession(enabled: false) { success in
                DispatchQueue.main.async {
                    completion(success)
                }
            }
        } else {
            completion(false)
        }
    }
}
