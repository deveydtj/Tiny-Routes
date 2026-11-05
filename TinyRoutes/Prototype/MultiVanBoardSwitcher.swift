import os
import SwiftUI

/// How the diorama comes and goes when the boards swap. It arrives looking straight
/// down, where the flat board was, and tilts up into the table; before it leaves
/// for the flat board it lies back down.
enum MultiVanBoardMorph: Equatable {
    case none
    case fromFlat
    case toFlat
}

/// Builds one board for the selected style and crossfades when the style changes.
/// Both boards read the same engine, so a swap carries every switch and van over;
/// the board that isn't showing isn't built at all, which stops its rendering.
/// Between the two boards the diorama morphs to and from the flat board's view.
struct MultiVanBoardSwitcher<Board: View>: View {
    let engine: MultiVanEngine
    let settings: UserSettings
    var reducesMotion = false
    /// Told the board on screen when it first appears and after every swap.
    var onBoardShown: (MultiVanBoardStyle) -> Void = { _ in }
    @ViewBuilder let board: (MultiVanBoardStyle, MultiVanBoardMorph) -> Board

    @State private var powerMonitor = MultiVanPowerMonitor()
    @State private var selection: MultiVanBoardSelection?
    @State private var signposts = MultiVanBoardSignposts()
    @State private var morph = MultiVanBoardMorph.none
    /// The diorama lying down before the flat board takes over.
    @State private var folding: Task<Void, Never>?

    private var target: MultiVanBoardStyle {
        MultiVanBoardStyle.resolve(settings: settings, isLowPowerMode: powerMonitor.isLowPowerModeEnabled)
    }

    var body: some View {
        let shown = selection?.shown ?? target
        ZStack {
            board(shown, morph)
                .id(shown)
                .transition(reducesMotion ? .identity : .opacity)
        }
        .onAppear {
            selection = MultiVanBoardSelection(showing: target)
            onBoardShown(target)
            signposts.mark(target, phase: engine.phase)
        }
        .onDisappear {
            signposts.end()
            folding?.cancel()
        }
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
        guard var next = selection else { return }
        next.update(to: target, isAutomatic: isAutomatic, phase: engine.phase)
        folding?.cancel()
        folding = nil
        guard next != selection else {
            // Back to the diorama before it finished lying down: it stands up again.
            if morph == .toFlat, selection?.shown == .diorama { morph = .none }
            return
        }
        guard !reducesMotion, selection?.shown == .diorama, next.shown == .flat else {
            morph = next.shown == .diorama && !reducesMotion ? .fromFlat : .none
            swap(to: next)
            return
        }
        morph = .toFlat
        folding = Task {
            try? await Task.sleep(for: .seconds(MultiVanDioramaBoardView.foldDuration))
            guard !Task.isCancelled else { return }
            // The morph stays put, so the diorama stays down while it fades out.
            folding = nil
            swap(to: next)
        }
    }

    private func swap(to next: MultiVanBoardSelection) {
        withAnimation(reducesMotion ? nil : .easeInOut(duration: 0.25)) {
            selection = next
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
