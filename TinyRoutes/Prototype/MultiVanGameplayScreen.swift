import SwiftUI
import Observation

struct MultiVanGameplayScreen: View {
    // The caller retains this engine across renders and supplies a fresh one for
    // each new level. No gameplay state is copied into the screen.
    let engine: MultiVanEngine
    @ObservedObject var settingsService: UserSettingsService
    var onNext: (() -> Void)? = nil
    var playtestLog: MultiVanPlaytestLog? = nil

    @Environment(\.scenePhase) private var scenePhase
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @Environment(\.accessibilityVoiceOverEnabled) private var voiceOverEnabled
    @Environment(\.dynamicTypeSize) private var dynamicTypeSize
    @AccessibilityFocusState private var accessibilityFocus: FocusTarget?
    @State private var frameDriver = MultiVanFrameDriver()
    @StateObject private var soundPlayer = MultiVanSoundPlayer()
    @State private var presentedFailure: MultiVanEngine.Outcome?
    @State private var winPresentation = MultiVanWinPresentation()
    @State private var celebration = MultiVanCelebration()
    @State private var personality = MultiVanPersonality()
    @State private var crashEffects = MultiVanCrashEffects()
    @State private var switchFeedback = MultiVanSwitchFeedback()

    private enum FocusTarget: Hashable { case levelTitle, failure, victory }

    private var reducesExtraAnimations: Bool {
        reduceMotion || settingsService.settings.reducesExtraAnimations
    }

    var body: some View {
        GeometryReader { geometry in
            ScrollView {
                gameplayContent
                    .frame(minHeight: geometry.size.height)
            }
            .scrollBounceBehavior(.basedOnSize)
        }
        .padding(16)
        .background(Color(red: 0.88, green: 0.94, blue: 0.97))
        .background {
            TimelineView(.animation(paused: engine.phase != .run || scenePhase != .active)) { frame in
                Color.clear
                    .onChange(of: frame.date) { _, date in
                        // onChange runs after view construction, never from the
                        // TimelineView builder or Canvas drawing closure.
                        frameDriver.advance(at: date, engine: engine, isActive: scenePhase == .active)
                        processPendingEvents()
                    }
            }
            .accessibilityHidden(true)
        }
        .onChange(of: scenePhase) { _, phase in
            frameDriver.reset()
            if phase != .active {
                playtestLog?.speedChanged(false, engine: engine)
                crashEffects.reset()
                switchFeedback.reset()
            }
        }
        .onChange(of: engine.phase) { _, _ in frameDriver.reset() }
        .onChange(of: voiceOverEnabled) { _, _ in
            frameDriver.reset()
            playtestLog?.speedChanged(false, engine: engine)
        }
        .onChange(of: ObjectIdentifier(engine)) { _, _ in
            soundPlayer.stop()
            frameDriver.reset(clearUsage: true)
            accessibilityFocus = nil
            presentedFailure = nil
            winPresentation.reset()
            celebration.reset()
            personality.reset()
            crashEffects.reset()
            switchFeedback.reset()
        }
        .onChange(of: engine.outcome) { _, _ in presentedFailure = nil }
        .onChange(of: settingsService.settings) { _, settings in soundPlayer.update(settings: settings) }
        .onChange(of: reducesExtraAnimations) { _, reduced in
            if reduced {
                winPresentation.finishImmediately()
                celebration.suppressMotion()
                personality.reset()
                crashEffects.reset()
                switchFeedback.reset()
            }
        }
        .onAppear {
            frameDriver.reset()
            soundPlayer.update(settings: settingsService.settings)
        }
        .onDisappear {
            soundPlayer.stop()
            frameDriver.reset()
            playtestLog?.speedChanged(false, engine: engine)
            accessibilityFocus = nil
            presentedFailure = nil
            winPresentation.reset()
            celebration.reset()
            personality.reset()
            crashEffects.reset()
            switchFeedback.reset()
        }
        .task(id: FailureDelayKey(engine: ObjectIdentifier(engine), outcome: engine.outcome, phase: engine.phase)) {
            guard let token = winPresentation.begin(engine: engine, reduceMotion: reducesExtraAnimations) else { return }
            guard !winPresentation.showsActions else { return }
            // Presentation time is independent of the frame driver's simulation multiplier.
            do {
                for _ in 0..<winPresentation.rating {
                    try await Task.sleep(for: .seconds(MultiVanWinPresentation.starInterval))
                    guard !Task.isCancelled else { return }
                    winPresentation.revealNext(for: token)
                }
                try await Task.sleep(for: .seconds(MultiVanWinPresentation.settleDuration))
            } catch { return }
            guard !Task.isCancelled else { return }
            withAnimation(reducesExtraAnimations ? nil : .easeOut(duration: 0.18)) {
                winPresentation.complete(for: token)
            }
        }
        .task(id: FailureDelayKey(engine: ObjectIdentifier(engine), outcome: engine.outcome, phase: engine.phase)) {
            guard engine.phase == .finished, let outcome = engine.outcome, isFailure(outcome) else { return }
            let duration = max(0, engine.tuning.failFreezeDuration)
            do {
                try await Task.sleep(for: .seconds(duration))
            } catch {
                return
            }
            guard !Task.isCancelled, engine.phase == .finished, engine.outcome == outcome else { return }
            withAnimation(reducesExtraAnimations ? nil : .easeOut(duration: 0.18)) {
                presentedFailure = outcome
            }
        }
        .onChange(of: presentedFailure) { _, failure in
            if failure != nil { accessibilityFocus = .failure }
        }
    }

    private var gameplayContent: some View {
        let shakesBoard = crashEffects.impact != nil && !reducesExtraAnimations
        return VStack(spacing: 12) {
            hud
                .accessibilityHidden(presentedFailure != nil)

            ZStack {
                MultiVanBoardView(
                    engine: engine,
                    onSwitchTapped: { nodeID, result in
                        playtestLog?.switchTapped(engine, nodeID: nodeID, result: result)
                    },
                    onEventsProduced: processPendingEvents,
                    celebration: celebration, reducesExtraAnimations: reducesExtraAnimations,
                    personality: personality,
                    onDeliveryEffectCompleted: { celebration.complete($0) },
                    crashEffects: crashEffects,
                    switchFeedback: switchFeedback,
                    onCrashEffectCompleted: { crashEffects.complete($0) }
                )
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                    .frame(minHeight: engine.outcome == .win ? 140 : 320)
                    .accessibilityHidden(presentedFailure != nil || engine.outcome == .win)
                    .keyframeAnimator(initialValue: 0.0, trigger: crashEffects.impact?.id) { content, progress in
                        content.offset(x: shakesBoard ? MultiVanCrashEffects.shakeOffset(progress: progress) : 0)
                    } keyframes: { _ in
                        // Restart the progress track for every collision, including after Retry.
                        MoveKeyframe(0.0)
                        LinearKeyframe(1.0, duration: MultiVanCrashEffects.shakeDuration)
                    }

                if let playbackID = celebration.confettiID, !reducesExtraAnimations {
                    TRConfettiEmitter(mode: .success, playbackID: playbackID)
                }

                if let presentedFailure {
                    failureCard(for: presentedFailure)
                        .padding(16)
                        .transition(reducesExtraAnimations ? .identity : .opacity.combined(with: .scale(scale: 0.96)))
                        .zIndex(1)
                }
            }

            controls
        }
    }

    private var hud: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(engine.level.name)
                .font(.system(.title2, design: .rounded, weight: .heavy))
                .accessibilityAddTraits(.isHeader)
                .accessibilityFocused($accessibilityFocus, equals: .levelTitle)

            LazyVGrid(columns: [GridItem(.adaptive(minimum: dynamicTypeSize.isAccessibilitySize ? 240 : 110), alignment: .leading)], alignment: .leading) {
                ForEach(engine.level.vans, id: \.id) { van in
                    HStack(spacing: 5) {
                        Text("\(van.color.symbol) →")
                        if let house = engine.level.houses.first(where: { $0.color == van.color }) {
                            Image(systemName: "house.fill")
                            Text(house.color.symbol)
                        }
                    }
                    .font(.subheadline.bold())
                    .foregroundStyle(van.color.boardColor)
                    .padding(.horizontal, 10)
                    .padding(.vertical, 6)
                    .background(van.color.boardColor.opacity(0.12), in: Capsule())
                    .accessibilityElement(children: .ignore)
                    .accessibilityLabel("\(van.color.displayName) \(van.color.accessibilitySymbolName) van to \(van.color.displayName.lowercased()) \(van.color.accessibilitySymbolName) house")
                }
            }

            Text("Changes \(engine.changeCount) · Par \(engine.level.parChanges)")
                .font(.subheadline.bold())

            if let hint = engine.level.hint {
                Text(hint)
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    @ViewBuilder
    private var controls: some View {
        switch engine.phase {
        case .plan:
            VStack(spacing: 4) {
                primaryButton("GO") {
                    winPresentation.reset()
                    celebration.reset()
                    personality.reset()
                    crashEffects.reset()
                    switchFeedback.reset()
                    frameDriver.reset()
                    playtestLog?.go(engine)
                    engine.go()
                    processPendingEvents()
                }
                .accessibilityLabel("Go")
                .accessibilityHint("Start all vans on the selected routes")
                Button {
                    engine.resetSwitches()
                    playtestLog?.record(.reset, engine: engine)
                } label: {
                    Text("Reset switches")
                        .frame(maxWidth: .infinity, minHeight: 44)
                }
                    .accessibilityHint("Restore the level's initial switch selections")
            }
        case .run:
            controlLayout {
                primaryButton("Stop") {
                    winPresentation.reset()
                    celebration.reset()
                    personality.reset()
                    crashEffects.reset()
                    switchFeedback.reset()
                    soundPlayer.stop()
                    playtestLog?.stop(engine)
                    frameDriver.reset()
                    engine.stop()
                    playtestLog?.begin(engine, action: .planningStarted)
                    processPendingEvents()
                }
                .accessibilityHint("Return to planning with your switch selections kept")
                Button {} label: {
                    Label(frameDriver.isFastForwarding ? "2× active" : (voiceOverEnabled ? "2× speed" : "Hold 2×"), systemImage: "forward.fill")
                        .font(.system(.title3, design: .rounded, weight: .bold))
                        .frame(maxWidth: .infinity, minHeight: 44)
                }
                .buttonStyle(.borderedProminent)
                .tint(frameDriver.isFastForwarding ? .orange : .blue)
                .onLongPressGesture(minimumDuration: .infinity, maximumDistance: 44) {} onPressingChanged: { pressed in
                    guard !voiceOverEnabled else { return }
                    setFastForwarding(pressed)
                }
                .accessibilityLabel("Fast-forward")
                .accessibilityValue(frameDriver.isFastForwarding ? "2× speed, active" : "Normal speed")
                .accessibilityHint("Activate to toggle between normal and twice normal speed")
                .accessibilityAddTraits(frameDriver.isFastForwarding ? [.isSelected] : [])
                .accessibilityAction { setFastForwarding(!frameDriver.isFastForwarding) }
            }
        case .finished:
            if engine.outcome == .win {
                winCard
            } else {
                EmptyView()
            }
        }
    }

    private var winCard: some View {
        VStack(spacing: 12) {
            Text("All delivered!")
                .font(.system(.title2, design: .rounded, weight: .heavy))
                .foregroundStyle(TRGameplayStyle.Colors.titleNavy)
                .accessibilityAddTraits(.isHeader)
                .accessibilityLabel("All delivered! \(winPresentation.accessibilityRating)")
                .accessibilityFocused($accessibilityFocus, equals: .victory)
                .onChange(of: winPresentation.id) { _, id in
                    if id != nil { accessibilityFocus = .victory }
                }

            Text("Every van reached its matching house.")
                .font(.subheadline)
                .foregroundStyle(.secondary)

            HStack {
                TRResultStarRatingView(
                    stars: winPresentation.revealedStars,
                    animatesReveal: !reducesExtraAnimations,
                    size: 42
                )
            }
            .accessibilityHidden(true)

            Text("Changes \(engine.changeCount) · Par \(engine.level.parChanges)")
                .font(.system(.subheadline, design: .rounded, weight: .semibold))
                .foregroundStyle(TRGameplayStyle.Colors.titleNavy)

            controlLayout {
                TRResultActionButton(title: "Next", systemImage: "arrow.right", variant: .primary, supportsDynamicType: true) { onNext?() }
                    .disabled(onNext == nil)
                    .keyboardShortcut(.defaultAction)
                TRResultActionButton(title: "Replay", systemImage: "arrow.counterclockwise", variant: .secondary, supportsDynamicType: true, action: retry)
            }
            .opacity(winPresentation.showsActions ? 1 : 0)
            .disabled(!winPresentation.showsActions)
            .allowsHitTesting(winPresentation.showsActions)
            .accessibilityHidden(!winPresentation.showsActions)
        }
        .multilineTextAlignment(.center)
        .fixedSize(horizontal: false, vertical: true)
        .padding(18)
        .frame(maxWidth: 380)
        .frame(maxWidth: .infinity)
        .background { TRGlassCardBackground() }
        .accessibilityElement(children: .contain)
        .opacity(winPresentation.id == nil ? 0 : 1)
        .animation(reducesExtraAnimations ? nil : .easeOut(duration: 0.18), value: winPresentation.id)
    }

    @ViewBuilder
    private func failureCard(for outcome: MultiVanEngine.Outcome) -> some View {
        VStack(spacing: 12) {
            Text(failureMessage(for: outcome))
                .font(.system(.title3, design: .rounded, weight: .bold))
                .multilineTextAlignment(.center)
                .foregroundStyle(.primary)
                .fixedSize(horizontal: false, vertical: true)
                .accessibilityAddTraits(.isHeader)
                .accessibilityFocused($accessibilityFocus, equals: .failure)
            primaryButton("Try again", action: retry)
        }
        .padding(16)
        .frame(maxWidth: 340)
        .background { TRGlassCardBackground(cornerRadius: 20) }
        .accessibilityElement(children: .contain)
    }

    private func failureMessage(for outcome: MultiVanEngine.Outcome) -> String {
        MultiVanFailureCopy.message(for: outcome, level: engine.level)
    }

    private func isFailure(_ outcome: MultiVanEngine.Outcome?) -> Bool {
        switch outcome {
        case .failWrongHouse, .failCrash, .failStuck: true
        case .win, nil: false
        }
    }

    private struct FailureDelayKey: Equatable {
        let engine: ObjectIdentifier
        let outcome: MultiVanEngine.Outcome?
        let phase: MultiVanEngine.Phase
    }

    private func primaryButton(_ title: String, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Text(title)
                .font(.system(.title3, design: .rounded, weight: .bold))
                .fixedSize(horizontal: false, vertical: true)
                .frame(maxWidth: .infinity, minHeight: 44)
        }
        .buttonStyle(.borderedProminent)
        .tint(.blue)
    }

    private var controlLayout: AnyLayout {
        dynamicTypeSize.isAccessibilitySize ? AnyLayout(VStackLayout(spacing: 12)) : AnyLayout(HStackLayout(spacing: 12))
    }

    private func setFastForwarding(_ enabled: Bool) {
        frameDriver.setFastForwarding(enabled, at: Date(), engine: engine, isActive: scenePhase == .active)
        playtestLog?.speedChanged(frameDriver.isFastForwarding, engine: engine)
        processPendingEvents()
    }

    private func retry() {
        let isReplay = engine.outcome == .win
        winPresentation.reset()
        celebration.reset()
        personality.reset()
        crashEffects.reset()
        switchFeedback.reset()
        soundPlayer.stop()
        frameDriver.reset()
        presentedFailure = nil
        engine.retry()
        playtestLog?.begin(engine, action: isReplay ? .replay : .retry)
        accessibilityFocus = .levelTitle
        processPendingEvents()
    }

    private func processPendingEvents() {
        MultiVanFeedback.process(
            drainEvents: engine.drainEvents,
            settings: settingsService.settings,
            soundPlayer: soundPlayer,
            reactVisually: { event in
                playtestLog?.observe(event, engine: engine)
                celebration.process(event, engine: engine, reduceMotion: reducesExtraAnimations)
                personality.process(event, engine: engine, reduceMotion: reducesExtraAnimations)
                crashEffects.process(event, reduceMotion: reducesExtraAnimations)
                switchFeedback.process(event, reduceMotion: reducesExtraAnimations)
            }
        )
        // Includes stuck failures, which have no MV-31 terminal event.
        playtestLog?.completed(engine)
    }
}

enum MultiVanFailureCopy {
    static func message(for outcome: MultiVanEngine.Outcome, level: MultiVanLevel) -> String {
        switch outcome {
        case let .failWrongHouse(vanID, houseNodeID):
            let van = level.vans.first(where: { $0.id == vanID })
            let house = level.houses.first(where: { $0.nodeID == houseNodeID })
            guard let van, let house else { return "Wrong house!" }
            return "\(van.color.displayName) went to the \(house.color.displayName.lowercased()) house!"
        case let .failCrash(vanIDs, _):
            let colors = vanIDs.compactMap { id in level.vans.first { $0.id == id }?.color.displayName }
            return colors.isEmpty ? "Crash!" : "Crash! \(colors.joined(separator: " and ")) vans collided."
        case let .failStuck(vanID, _):
            let color = level.vans.first(where: { $0.id == vanID })?.color.displayName ?? "A van"
            return "\(color) hit a dead end!"
        case .win:
            return ""
        }
    }
}

/// Timestamp bookkeeping is reference state, so each frame only publishes the
/// engine's changes. SwiftUI owns the single frame schedule and its lifetime.
@Observable
final class MultiVanFrameDriver {
    @ObservationIgnored private var previousDate: Date?
    private(set) var isFastForwarding = false
    private(set) var fastForwardUseCount = 0

    func reset(clearUsage: Bool = false) {
        previousDate = nil
        isFastForwarding = false
        if clearUsage { fastForwardUseCount = 0 }
    }

    func setFastForwarding(_ held: Bool, at date: Date, engine: MultiVanEngine, isActive: Bool) {
        guard held != isFastForwarding else { return }
        // Settle the old speed through the input timestamp; keep the accumulator
        // and frame timestamp intact so changing speed loses no simulation time.
        advance(at: date, engine: engine, isActive: isActive)
        let enabled = held && isActive && engine.phase == .run
        if enabled && !isFastForwarding { fastForwardUseCount += 1 }
        isFastForwarding = enabled
    }

    func advance(at date: Date, engine: MultiVanEngine, isActive: Bool) {
        guard isActive, engine.phase == .run else {
            reset()
            return
        }
        guard let previousDate else {
            self.previousDate = date
            return
        }
        let elapsed = date.timeIntervalSince(previousDate)
        // Repeated render callbacks for the same timestamp cannot double-step.
        guard elapsed > 0 else { return }
        self.previousDate = date
        // Discard UI stalls; the engine still preserves every interval it receives.
        let multiplier = isFastForwarding ? engine.tuning.fastForwardMultiplier : 1
        engine.advance(by: min(elapsed, 0.25) * multiplier)
        if engine.phase != .run { reset() }
    }
}
