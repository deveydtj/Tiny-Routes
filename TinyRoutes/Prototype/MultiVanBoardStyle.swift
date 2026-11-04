import Foundation
import Observation

/// Which board the multi-van game draws. Both boards play by the same rules.
enum MultiVanBoardStyle: String, Codable, CaseIterable {
    case diorama
    case flat

    /// Low Power Mode swaps 3D for 2D only when the player allows it. Reduce Motion
    /// never changes the board; each board quietens its own motion instead.
    static func resolve(
        preference: MultiVanBoardStyle, flatInLowPower: Bool, isLowPowerMode: Bool
    ) -> MultiVanBoardStyle {
        preference == .diorama && flatInLowPower && isLowPowerMode ? .flat : preference
    }

    static func resolve(settings: UserSettings, isLowPowerMode: Bool) -> MultiVanBoardStyle {
        resolve(
            preference: settings.boardStyle,
            flatInLowPower: settings.usesFlatBoardInLowPowerMode,
            isLowPowerMode: isLowPowerMode
        )
    }
}

/// The board on screen. The player's own choices apply at once. Automatic ones, such
/// as Low Power Mode, wait while vans are driving so the view never jumps mid-run.
struct MultiVanBoardSelection: Equatable {
    private(set) var shown: MultiVanBoardStyle

    init(showing style: MultiVanBoardStyle) {
        shown = style
    }

    mutating func update(to target: MultiVanBoardStyle, isAutomatic: Bool, phase: MultiVanEngine.Phase) {
        guard !isAutomatic || phase != .run else { return }
        shown = target
    }
}

/// Low Power Mode as an observable value, read back on the main actor for every change.
@MainActor
@Observable
final class MultiVanPowerMonitor {
    private(set) var isLowPowerModeEnabled: Bool
    private let readsLowPowerMode: () -> Bool

    init(readsLowPowerMode: @escaping () -> Bool = { ProcessInfo.processInfo.isLowPowerModeEnabled }) {
        self.readsLowPowerMode = readsLowPowerMode
        isLowPowerModeEnabled = readsLowPowerMode()
    }

    /// Listens until the calling task is cancelled. Power-state notifications can be
    /// posted on any thread; this loop resumes on the main actor before publishing.
    func monitor(center: NotificationCenter = .default) async {
        let changes = center.notifications(named: .NSProcessInfoPowerStateDidChange)
        // Catch a change made while nothing was listening.
        refresh()
        for await _ in changes {
            refresh()
        }
    }

    private func refresh() {
        let isEnabled = readsLowPowerMode()
        if isEnabled != isLowPowerModeEnabled {
            isLowPowerModeEnabled = isEnabled
        }
    }
}
