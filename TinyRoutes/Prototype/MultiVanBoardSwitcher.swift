import os
import SwiftUI

/// Builds one board for the selected style and crossfades when the style changes.
/// Both boards read the same engine, so a swap carries every switch and van over;
/// the board that isn't showing isn't built at all, which stops its rendering.
struct MultiVanBoardSwitcher<Board: View>: View {
    let engine: MultiVanEngine
    let settings: UserSettings
    var reducesMotion = false
    /// Told the board on screen when it first appears and after every swap.
    var onBoardShown: (MultiVanBoardStyle) -> Void = { _ in }
    @ViewBuilder let board: (MultiVanBoardStyle) -> Board

    @State private var powerMonitor = MultiVanPowerMonitor()
    @State private var selection: MultiVanBoardSelection?
    @State private var signposts = MultiVanBoardSignposts()

    private var target: MultiVanBoardStyle {
        MultiVanBoardStyle.resolve(settings: settings, isLowPowerMode: powerMonitor.isLowPowerModeEnabled)
    }

    var body: some View {
        let shown = selection?.shown ?? target
        ZStack {
            board(shown)
                .id(shown)
                .transition(reducesMotion ? .identity : .opacity)
        }
        .onAppear {
            selection = MultiVanBoardSelection(showing: target)
            onBoardShown(target)
            signposts.mark(target, phase: engine.phase)
        }
        .onDisappear { signposts.end() }
        .onChange(of: selection?.shown) { _, shown in
            guard let shown else { return }
            onBoardShown(shown)
            signposts.mark(shown, phase: engine.phase)
        }
        // Settings changes are the player's; Settings is never open over gameplay.
        .onChange(of: settings.boardStyle) { _, _ in select(isAutomatic: false) }
        .onChange(of: settings.usesFlatBoardInLowPowerMode) { _, _ in select(isAutomatic: false) }
        .onChange(of: powerMonitor.isLowPowerModeEnabled) { _, _ in select(isAutomatic: true) }
        // A run ending, or a new level, applies a change held back during the run.
        .onChange(of: engine.phase) { _, phase in
            select(isAutomatic: true)
            if let shown = selection?.shown { signposts.mark(shown, phase: phase) }
        }
        .onChange(of: ObjectIdentifier(engine)) { _, _ in select(isAutomatic: true) }
        .task { await powerMonitor.monitor() }
    }

    private func select(isAutomatic: Bool) {
        withAnimation(reducesMotion ? nil : .easeInOut(duration: 0.25)) {
            selection?.update(to: target, isAutomatic: isAutomatic, phase: engine.phase)
        }
    }
}

/// Marks which board is on screen, and in which phase, as signpost intervals, so an
/// Instruments trace of a play session splits its frames and energy by board.
/// Free when no trace is recording. Autoplay's performance meter takes the same labels.
@MainActor
final class MultiVanBoardSignposts {
    static let signposter = OSSignposter(subsystem: "com.tinyroutes.app", category: "MultiVanBoard")
    private var interval: (label: String, state: OSSignpostIntervalState)?

    func mark(_ style: MultiVanBoardStyle, phase: MultiVanEngine.Phase) {
        let label = "\(style.rawValue) \(phase)"
        guard label != interval?.label else { return }
        #if DEBUG || MULTIVAN_INTERNAL
        MultiVanPerformanceMeter.shared?.mark(label)
        #endif
        end()
        interval = (label, Self.signposter.beginInterval("Board", "\(label, privacy: .public)"))
    }

    func end() {
        guard let interval else { return }
        Self.signposter.endInterval("Board", interval.state)
        self.interval = nil
    }
}
