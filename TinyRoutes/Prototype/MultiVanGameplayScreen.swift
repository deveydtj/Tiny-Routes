import SwiftUI
import Observation

struct MultiVanGameplayScreen: View {
    // The caller retains this engine across renders and supplies a fresh one for
    // each new level. No gameplay state is copied into the screen.
    let engine: MultiVanEngine
    @ObservedObject var settingsService: UserSettingsService
    var onNext: (() -> Void)? = nil
    /// Shows a back button in the HUD when set.
    var onBack: (() -> Void)? = nil
    var playtestLog: MultiVanPlaytestLog? = nil
    #if DEBUG || MULTIVAN_INTERNAL
    /// Plays the level on a loop for profiling; see `MultiVanAutoplay`.
    var autoplay: MultiVanAutoplay? = nil
    @State private var autoplayDriver: MultiVanAutoplayDriver?
    #endif

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
    /// Where the full-screen board, the HUD's bottom and the controls' top sit,
    /// in global points; the board frames its table between the two.
    @State private var boardFrame: CGRect?
    @State private var hudBottom: CGFloat = 0
    @State private var controlsTop: CGFloat = 0

    private static let backdrop = Color(red: 0.88, green: 0.94, blue: 0.97)

    private enum FocusTarget: Hashable { case levelTitle, failure, victory }

    /// Whether the game clock runs. An app `devicectl` launches over the network
    /// stays in an inactive scene until someone touches it, so autoplay also plays
    /// there; everyone else needs an active scene.
    private var isActive: Bool {
        #if DEBUG || MULTIVAN_INTERNAL
        if autoplay != nil { return scenePhase != .background }
        #endif
        return scenePhase == .active
    }

    private var reducesExtraAnimations: Bool {
        reduceMotion || settingsService.settings.reducesExtraAnimations
    }

    var body: some View {
        Group {
            // Accessibility text makes the cards too tall to float over the board,
            // so they stack above and below it instead.
            if dynamicTypeSize.isAccessibilitySize {
                stackedLayout
            } else {
                fullScreenLayout
            }
        }
        .background {
            TimelineView(.animation(paused: engine.phase != .run || !isActive)) { frame in
                Color.clear
                    .onChange(of: frame.date) { _, date in
                        // onChange runs after view construction, never from the
                        // TimelineView builder or Canvas drawing closure.
                        frameDriver.advance(at: date, engine: engine, isActive: isActive)
                        processPendingEvents()
                        runAutoplay()
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
        #if DEBUG || MULTIVAN_INTERNAL
        // Planning and results run on the clock; live taps also run per frame.
        .task(id: ObjectIdentifier(engine)) {
            guard let autoplay else {
                MultiVanPerformanceMeter.shared?.autoplay("waiting: gameplay has no autoplay option")
                return
            }
            autoplayDriver = MultiVanAutoplayDriver(autoplay)
            MultiVanPerformanceMeter.shared?.autoplay("started")
            while !Task.isCancelled {
                runAutoplay()
                try? await Task.sleep(for: .milliseconds(50))
            }
        }
        #endif
    }

    /// The board fills the screen and the cards float over it. The table is framed
    /// in the band between the HUD and the controls, so they only cover scenery.
    private var fullScreenLayout: some View {
        ZStack {
            boardSwitcher(covered: coveredByCards, isFullScreen: true)
                .ignoresSafeArea()
                .onGeometryChange(for: CGRect.self) { $0.frame(in: .global) } action: { boardFrame = $0 }

            VStack(spacing: 12) {
                hud
                    .accessibilityHidden(presentedFailure != nil)
                    .onGeometryChange(for: CGFloat.self) { $0.frame(in: .global).maxY } action: { hudBottom = $0 }
                // Empty space here takes no touches, so drags reach the board.
                resultCards
                    .frame(maxHeight: .infinity)
                controlBar
                    .onGeometryChange(for: CGFloat.self) { $0.frame(in: .global).minY } action: { controlsTop = $0 }
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 8)
        }
        .background(Self.backdrop.ignoresSafeArea())
    }

    private var stackedLayout: some View {
        GeometryReader { geometry in
            ScrollView {
                VStack(spacing: 12) {
                    hud
                        .accessibilityHidden(presentedFailure != nil)

                    // Results sit over the board, so the board keeps one size from planning
                    // through the result.
                    ZStack {
                        boardSwitcher(covered: MultiVanDioramaCamera.Covered(), isFullScreen: false)
                            .frame(maxWidth: .infinity, maxHeight: .infinity)
                            .frame(minHeight: 320)
                        resultCards
                    }

                    controlBar
                }
                .frame(minHeight: geometry.size.height)
            }
            .scrollBounceBehavior(.basedOnSize)
        }
        .padding(16)
        .background(Self.backdrop)
    }

    /// The strips of the full-screen board under the HUD and the controls.
    private var coveredByCards: MultiVanDioramaCamera.Covered {
        guard let boardFrame, boardFrame.height > 0 else { return MultiVanDioramaCamera.Covered() }
        return MultiVanDioramaCamera.Covered(
            top: Double(max(0, hudBottom - boardFrame.minY)),
            bottom: Double(max(0, boardFrame.maxY - controlsTop))
        )
    }

    private func boardSwitcher(covered: MultiVanDioramaCamera.Covered, isFullScreen: Bool) -> some View {
        MultiVanBoardSwitcher(
            engine: engine, settings: boardSettings, reducesMotion: reducesExtraAnimations,
            onBoardShown: { playtestLog?.boardShown($0, engine: engine) }
        ) { style in
            board(style, covered: covered, isFullScreen: isFullScreen)
        }
        .accessibilityHidden(presentedFailure != nil || engine.outcome == .win)
    }

    private var resultCards: some View {
        ZStack {
            if let presentedFailure {
                failureCard(for: presentedFailure)
                    .padding(16)
                    .frame(maxHeight: .infinity, alignment: .top)
                    .transition(reducesExtraAnimations ? .identity : .opacity.combined(with: .scale(scale: 0.96)))
                    .zIndex(1)
            }

            if engine.outcome == .win {
                winCard
                    .padding(16)
                    .zIndex(1)
            }
        }
    }

    private static let idleConfettiID = UUID()

    @ViewBuilder
    private func board(_ style: MultiVanBoardStyle, covered: MultiVanDioramaCamera.Covered, isFullScreen: Bool) -> some View {
        let onSwitchTapped: (String, MultiVanTapResult) -> Void = switchTapped
        let shakesBoard = crashEffects.impact != nil && !reducesExtraAnimations
        switch style {
        case .flat:
            // The diorama shakes its own camera and throws its own paper confetti.
            MultiVanBoardView(
                engine: engine,
                onSwitchTapped: onSwitchTapped,
                onEventsProduced: processPendingEvents,
                celebration: celebration, reducesExtraAnimations: reducesExtraAnimations,
                personality: personality,
                onDeliveryEffectCompleted: { celebration.complete($0) },
                crashEffects: crashEffects,
                switchFeedback: switchFeedback,
                onCrashEffectCompleted: { crashEffects.complete($0) }
            )
            // The flat board stays a card, set in the band between the HUD and controls.
            .padding(.top, CGFloat(covered.top))
            .padding(.bottom, CGFloat(covered.bottom))
            .padding(.horizontal, isFullScreen ? 16 : 0)
            .keyframeAnimator(initialValue: 0.0, trigger: crashEffects.impact?.id) { content, progress in
                content.offset(x: shakesBoard ? MultiVanCrashEffects.shakeOffset(progress: progress) : 0)
            } keyframes: { _ in
                // Restart the progress track for every collision, including after Retry.
                MoveKeyframe(0.0)
                LinearKeyframe(1.0, duration: MultiVanCrashEffects.shakeDuration)
            }
            .overlay {
                // Idle from the start, so the win's burst doesn't stall a frame
                // setting SpriteKit up.
                if !reducesExtraAnimations {
                    TRConfettiEmitter(
                        mode: celebration.confettiID == nil ? .idle : .success,
                        playbackID: celebration.confettiID ?? Self.idleConfettiID
                    )
                }
            }
        case .diorama:
            MultiVanDioramaBoardView(
                engine: engine,
                onSwitchTapped: onSwitchTapped,
                onEventsProduced: processPendingEvents,
                celebration: celebration, reducesExtraAnimations: reducesExtraAnimations,
                personality: personality,
                onDeliveryEffectCompleted: { celebration.complete($0) },
                crashEffects: crashEffects,
                switchFeedback: switchFeedback,
                onCrashEffectCompleted: { crashEffects.complete($0) },
                covered: covered,
                cornerRadius: isFullScreen ? 0 : 20
            )
        }
    }

    private var hud: some View {
        HStack(alignment: .top, spacing: 10) {
            if let onBack {
                TRResultIconButton(systemImage: "chevron.left", label: "Levels", action: onBack)
                    .accessibilityHint("Return to the level map")
            }

            VStack(alignment: .leading, spacing: 10) {
                HStack(alignment: .center, spacing: 8) {
                    Text(engine.level.name)
                        .font(.system(.title3, design: .rounded, weight: .heavy))
                        .foregroundStyle(TRGameplayStyle.Colors.titleNavy)
                        .fixedSize(horizontal: false, vertical: true)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .accessibilityAddTraits(.isHeader)
                        .accessibilityFocused($accessibilityFocus, equals: .levelTitle)
                    changesBadge
                }

                LazyVGrid(columns: [GridItem(.adaptive(minimum: dynamicTypeSize.isAccessibilitySize ? 240 : 110), alignment: .leading)], alignment: .leading) {
                    ForEach(engine.level.vans, id: \.id) { van in
                        HStack(spacing: 5) {
                            Text("\(van.color.symbol) →")
                            if let house = engine.level.houses.first(where: { $0.color == van.color }) {
                                Image(systemName: "house.fill")
                                Text(house.color.symbol)
                            }
                        }
                        .font(.system(.subheadline, design: .rounded, weight: .heavy))
                        .foregroundStyle(van.color.boardColor)
                        .padding(.horizontal, 10)
                        .padding(.vertical, 6)
                        .background {
                            Capsule()
                                .fill(van.color.boardColor.opacity(0.12))
                                .overlay { Capsule().stroke(van.color.boardColor.opacity(0.22), lineWidth: 1) }
                        }
                        .accessibilityElement(children: .ignore)
                        .accessibilityLabel("\(van.color.displayName) \(van.color.accessibilitySymbolName) van to \(van.color.displayName.lowercased()) \(van.color.accessibilitySymbolName) house")
                    }
                }
                // Levels still carry their `hint`; the HUD leaves it out for now.
            }
            .padding(14)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background { TRGlassCardBackground(cornerRadius: 22) }
            .accessibilityElement(children: .contain)
        }
    }

    /// The switch changes so far against par; orange once over it.
    private var changesBadge: some View {
        let isOverPar = engine.changeCount > engine.level.parChanges
        let tint = isOverPar ? TRGameplayStyle.Colors.orangeAccent : TRGameplayStyle.Colors.primaryBlue
        return HStack(spacing: 5) {
            Image(systemName: "arrow.triangle.branch")
                .font(.system(.caption, design: .rounded, weight: .heavy))
            Text("\(engine.changeCount)")
                .monospacedDigit()
            Text("/ \(engine.level.parChanges)")
                .font(.system(.caption, design: .rounded, weight: .bold))
                .foregroundStyle(TRGameplayStyle.Colors.secondaryText)
                .monospacedDigit()
        }
        .font(.system(.headline, design: .rounded, weight: .heavy))
        .foregroundStyle(tint)
        .padding(.horizontal, 11)
        .padding(.vertical, 6)
        .background { Capsule().fill(tint.opacity(0.12)) }
        .animation(reducesExtraAnimations ? nil : .easeOut(duration: 0.18), value: isOverPar)
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("Changes \(engine.changeCount), par \(engine.level.parChanges)")
    }

    /// The controls in a card of their own, floating over the board.
    private var controlBar: some View {
        controls
            .padding(10)
            .background { TRGlassCardBackground(cornerRadius: 24) }
    }

    /// Every phase's buttons share one footprint and the same two places: going
    /// back on the left, going on on the right. So nothing moves under a finger
    /// when a press changes the phase, and the board never changes size.
    private var controls: some View {
        let isWin = engine.phase == .finished && engine.outcome == .win
        return ZStack {
            controlRow(isShown: engine.phase == .plan) {
                controlLayout {
                    secondaryButton("Reset switches", action: resetSwitches)
                        .accessibilityHint("Restore the level's initial switch selections")
                    primaryButton("GO", action: go)
                        .accessibilityLabel("Go")
                        .accessibilityHint("Start all vans on the selected routes")
                }
            }
            controlRow(isShown: engine.phase == .run) { runControls }
            controlRow(isShown: isWin && winPresentation.showsActions) {
                controlLayout {
                    secondaryButton("Replay", systemImage: "arrow.counterclockwise", action: retry)
                    primaryButton("Next", systemImage: "arrow.right") { onNext?() }
                        .disabled(onNext == nil)
                        .keyboardShortcut(.defaultAction)
                }
            }
            controlRow(isShown: engine.phase == .finished && presentedFailure != nil) {
                primaryButton("Try again", systemImage: "arrow.counterclockwise", action: retry)
            }
        }
    }

    /// One phase's buttons, kept in the layout when hidden so the footprint holds.
    private func controlRow<Content: View>(isShown: Bool, @ViewBuilder content: () -> Content) -> some View {
        content()
            .opacity(isShown ? 1 : 0)
            .disabled(!isShown)
            .allowsHitTesting(isShown)
            .accessibilityHidden(!isShown)
    }

    private var runControls: some View {
        controlLayout {
            secondaryButton("Stop") {
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
                controlLabel(frameDriver.isFastForwarding ? "2× active" : (voiceOverEnabled ? "2× speed" : "Hold 2×"), systemImage: "forward.fill")
            }
            .buttonStyle(MultiVanControlButtonStyle(
                isProminent: true,
                tint: frameDriver.isFastForwarding ? TRGameplayStyle.Colors.orangeAccent : TRGameplayStyle.Colors.primaryBlue
            ))
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

    /// What went wrong, over the top of the board; Try again waits below it.
    private func failureCard(for outcome: MultiVanEngine.Outcome) -> some View {
        Text(failureMessage(for: outcome))
            .font(.system(.title3, design: .rounded, weight: .bold))
            .multilineTextAlignment(.center)
            .foregroundStyle(TRGameplayStyle.Colors.titleNavy)
            .fixedSize(horizontal: false, vertical: true)
            .accessibilityAddTraits(.isHeader)
            .accessibilityFocused($accessibilityFocus, equals: .failure)
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

    /// Every control is at least this tall, whatever the phase.
    private static let controlHeight: CGFloat = 50

    private func primaryButton(_ title: String, systemImage: String? = nil, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            controlLabel(title, systemImage: systemImage)
        }
        .buttonStyle(MultiVanControlButtonStyle(isProminent: true))
    }

    private func secondaryButton(_ title: String, systemImage: String? = nil, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            controlLabel(title, systemImage: systemImage)
        }
        .buttonStyle(MultiVanControlButtonStyle(isProminent: false))
    }

    private func controlLabel(_ title: String, systemImage: String?) -> some View {
        Group {
            if let systemImage {
                Label(title, systemImage: systemImage)
            } else {
                Text(title)
            }
        }
        .font(.system(.headline, design: .rounded, weight: .bold))
        .multilineTextAlignment(.center)
        .fixedSize(horizontal: false, vertical: true)
        .frame(maxWidth: .infinity, minHeight: Self.controlHeight)
    }

    private var controlLayout: AnyLayout {
        dynamicTypeSize.isAccessibilitySize ? AnyLayout(VStackLayout(spacing: 12)) : AnyLayout(HStackLayout(spacing: 12))
    }

    private func setFastForwarding(_ enabled: Bool) {
        frameDriver.setFastForwarding(enabled, at: Date(), engine: engine, isActive: isActive)
        playtestLog?.speedChanged(frameDriver.isFastForwarding, engine: engine)
        processPendingEvents()
    }

    private func go() {
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

    private func resetSwitches() {
        engine.resetSwitches()
        playtestLog?.record(.reset, engine: engine)
    }

    private func switchTapped(_ nodeID: String, _ result: MultiVanTapResult) {
        playtestLog?.switchTapped(engine, nodeID: nodeID, result: result)
    }

    /// The settings the switcher picks a board from. Autoplay pins its board.
    private var boardSettings: UserSettings {
        #if DEBUG || MULTIVAN_INTERNAL
        if let autoplay { return autoplay.settings(from: settingsService.settings) }
        #endif
        return settingsService.settings
    }

    /// Carries out the autoplay's next press the way the player's own would be.
    private func runAutoplay() {
        #if DEBUG || MULTIVAN_INTERNAL
        let meter = MultiVanPerformanceMeter.shared
        guard let autoplayDriver else { return meter?.autoplay("waiting: no driver") ?? () }
        guard isActive else { return meter?.autoplay("waiting: scene \(scenePhase)") ?? () }
        let press = autoplayDriver.nextPress(engine: engine, now: ProcessInfo.processInfo.systemUptime)
        if let press { meter?.autoplay("\(press)", isPress: true) }
        switch press {
        case .resetSwitches: resetSwitches()
        case let .tap(nodeID):
            let result = engine.tapSwitch(nodeID: nodeID)
            switchTapped(nodeID, result)
            processPendingEvents()
        case .go: go()
        case .retry: retry()
        case nil: break
        }
        #endif
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

/// The menus' glossy buttons, at the gameplay controls' size: a tinted gradient
/// for going on, white for going back.
private struct MultiVanControlButtonStyle: ButtonStyle {
    let isProminent: Bool
    var tint = TRGameplayStyle.Colors.primaryBlue
    @Environment(\.isEnabled) private var isEnabled

    func makeBody(configuration: Configuration) -> some View {
        let shape = RoundedRectangle(cornerRadius: 16, style: .continuous)
        return configuration.label
            .padding(.horizontal, 12)
            .foregroundStyle(isProminent ? Color.white : TRGameplayStyle.Colors.titleNavy)
            .background {
                shape
                    .fill(isProminent
                        ? AnyShapeStyle(tint)
                        : AnyShapeStyle(LinearGradient(colors: [.white, Color(red: 0.94, green: 0.97, blue: 1.00)], startPoint: .top, endPoint: .bottom)))
                    .overlay(alignment: .top) {
                        shape
                            .fill(.white.opacity(isProminent ? 0.28 : 0.6))
                            .frame(height: 22)
                            .blur(radius: 8)
                            .offset(y: -11)
                            .clipShape(shape)
                    }
                    .overlay { shape.stroke(.white.opacity(isProminent ? 0.38 : 0.8), lineWidth: 1) }
                    .overlay {
                        if !isProminent { shape.stroke(TRGameplayStyle.Colors.markerStroke.opacity(0.5), lineWidth: 1).padding(1) }
                    }
                    .shadow(
                        color: (isProminent ? tint : Color(red: 0.50, green: 0.62, blue: 0.74)).opacity(isProminent ? 0.30 : 0.18),
                        radius: configuration.isPressed ? 4 : 8, x: 0, y: configuration.isPressed ? 2 : 5
                    )
            }
            .contentShape(shape)
            .opacity(isEnabled ? 1 : 0.55)
            .scaleEffect(configuration.isPressed ? 0.97 : 1)
            .animation(.spring(response: 0.2, dampingFraction: 0.72), value: configuration.isPressed)
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
