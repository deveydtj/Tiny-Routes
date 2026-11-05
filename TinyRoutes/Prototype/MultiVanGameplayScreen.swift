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
    /// The banner reaches down to the middle of the level card.
    @State private var levelCardHeight: CGFloat = 0
    /// The board the switcher has on screen, for the HUD's 2D/3D button.
    @State private var shownBoard: MultiVanBoardStyle?

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
            guard engine.phase == .finished, engine.outcome == .win else { return }
            if !reducesExtraAnimations {
                do { try await Task.sleep(for: .seconds(MultiVanWinPresentation.confettiHold)) } catch { return }
            }
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
                hud(isDecorated: true)
                    .accessibilityHidden(presentedFailure != nil)
                    .onGeometryChange(for: CGFloat.self) { $0.frame(in: .global).maxY } action: { hudBottom = $0 }
                // Empty space here takes no touches, so drags reach the board.
                resultCards
                    .frame(maxHeight: .infinity)
                controlBar
                    .background(alignment: .top) {
                        // Out past the screen's sides and bottom edge.
                        MultiVanHUDHills()
                            .padding(.top, -MultiVanHUDHills.rise)
                            .padding(.horizontal, -16)
                            .padding(.bottom, -200)
                    }
                    // The table stays clear of the hills too.
                    .onGeometryChange(for: CGFloat.self) { $0.frame(in: .global).minY - MultiVanHUDHills.rise } action: { controlsTop = $0 }
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
                    hud(isDecorated: false)
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
            onBoardShown: { style in
                shownBoard = style
                playtestLog?.boardShown(style, engine: engine)
            }
        ) { style, morph in
            board(style, morph: morph, covered: covered, isFullScreen: isFullScreen)
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
                // Up under the HUD, clear of the shower thrown from the middle of the board.
                winCard
                    .padding(16)
                    .frame(maxHeight: .infinity, alignment: .top)
                    .zIndex(1)
            }
        }
    }

    private static let idleConfettiID = UUID()

    @ViewBuilder
    private func board(
        _ style: MultiVanBoardStyle, morph: MultiVanBoardMorph, covered: MultiVanDioramaCamera.Covered, isFullScreen: Bool
    ) -> some View {
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
                cornerRadius: isFullScreen ? 0 : 20,
                morph: morph,
                // The flat board's own side padding, so the morph lands on it.
                flatSideInset: isFullScreen ? 16 : 0
            )
        }
    }

    /// The banner and the level card. Full screen, the banner paints the top of
    /// the screen and reaches halfway down the card.
    private func hud(isDecorated: Bool) -> some View {
        VStack(spacing: 10) {
            if isDecorated || showsTopBar {
                topBar(showsLogo: isDecorated)
            }
            levelCard
                .onGeometryChange(for: CGFloat.self) { $0.size.height } action: { levelCardHeight = $0 }
        }
        .background(alignment: .bottom) {
            if isDecorated {
                // Out past the screen's sides and up under the status bar.
                MultiVanHUDBanner()
                    .padding(.bottom, levelCardHeight / 2)
                    .padding(.horizontal, -16)
                    .padding(.top, -200)
            }
        }
    }

    private var showsTopBar: Bool {
        #if DEBUG || MULTIVAN_INTERNAL
        true
        #else
        onBack != nil
        #endif
    }

    /// Back on the left, the wordmark in the middle, and the internal 2D/3D
    /// button on the right; empty slots keep the wordmark centred.
    private func topBar(showsLogo: Bool) -> some View {
        HStack(spacing: 10) {
            if let onBack {
                Button(action: onBack) { circleIcon("chevron.left", tint: TRGameplayStyle.Colors.titleNavy) }
                    .buttonStyle(.multiVanHUDCircle)
                    .accessibilityLabel("Levels")
                    .accessibilityHint("Return to the level map")
            } else {
                Self.emptyCircleSlot
            }

            Spacer(minLength: 0)
            if showsLogo { MultiVanHUDLogo() }
            Spacer(minLength: 0)

            #if DEBUG || MULTIVAN_INTERNAL
            // Internal, like the Settings picker, until the MW-10 playtests pass.
            boardStyleButton
            #else
            Self.emptyCircleSlot
            #endif
        }
    }

    private static let circleSize: CGFloat = 46
    private static var emptyCircleSlot: some View {
        Color.clear
            .frame(width: circleSize, height: circleSize + MultiVanHUDButtonStyle.lipDepth)
            .accessibilityHidden(true)
    }

    private func circleIcon(_ systemImage: String, tint: Color = TRGameplayStyle.Colors.primaryBlue) -> some View {
        Image(systemName: systemImage)
            .font(.system(size: 19, weight: .black, design: .rounded))
            .foregroundStyle(tint)
            .frame(width: Self.circleSize, height: Self.circleSize)
    }

    /// The level's number and name, its deliveries and the changes so far. The
    /// banner's one-line layout when it fits, otherwise the name over the deliveries.
    private var levelCard: some View {
        ViewThatFits(in: .horizontal) {
            HStack(alignment: .center, spacing: 10) {
                levelTitle
                    .fixedSize()
                Capsule()
                    .fill(MultiVanHUDStyle.creamLip.opacity(0.7))
                    .frame(width: 2, height: 40)
                    .accessibilityHidden(true)
                // One column of deliveries for up to three vans, two above that.
                let columns = engine.level.vans.count <= 3 ? 1 : 2
                Grid(alignment: .leading, horizontalSpacing: 6, verticalSpacing: 6) {
                    ForEach(Array(stride(from: 0, to: engine.level.vans.count, by: columns)), id: \.self) { start in
                        GridRow {
                            ForEach(engine.level.vans[start..<min(start + columns, engine.level.vans.count)], id: \.id) { van in
                                vanChip(van, isCompact: true)
                            }
                        }
                    }
                }
                Spacer(minLength: 0)
                changesBadge
            }

            VStack(alignment: .leading, spacing: 10) {
                HStack(alignment: .center, spacing: 8) {
                    levelTitle
                        .frame(maxWidth: .infinity, alignment: .leading)
                    changesBadge
                }

                LazyVGrid(columns: [GridItem(.adaptive(minimum: dynamicTypeSize.isAccessibilitySize ? 240 : 110), alignment: .leading)], alignment: .leading) {
                    ForEach(engine.level.vans, id: \.id) { van in
                        vanChip(van)
                    }
                }
                // Levels still carry their `hint`; the HUD leaves it out for now.
            }
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 12)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background { MultiVanHUDCardBackground(cornerRadius: 26) }
        .accessibilityElement(children: .contain)
    }

    private var levelTitle: some View {
        VStack(alignment: .leading, spacing: 1) {
            if let levelNumber {
                Text("Level \(levelNumber)")
                    .font(.system(.footnote, design: .rounded, weight: .bold))
                    .foregroundStyle(TRGameplayStyle.Colors.secondaryText)
            }
            Text(engine.level.name)
                .font(.system(.title3, design: .rounded, weight: .heavy))
                .foregroundStyle(TRGameplayStyle.Colors.titleNavy)
                .fixedSize(horizontal: false, vertical: true)
                .accessibilityAddTraits(.isHeader)
                .accessibilityFocused($accessibilityFocus, equals: .levelTitle)
        }
    }

    /// The number the level map shows on this level's tile.
    private var levelNumber: Int? {
        engine.level.id.split(separator: "_").last.flatMap { Int($0) }
    }

    private func vanChip(_ van: MultiVanVan, isCompact: Bool = false) -> some View {
        HStack(spacing: isCompact ? 4 : 5) {
            Text("\(van.color.symbol) →")
            if let house = engine.level.houses.first(where: { $0.color == van.color }) {
                Image(systemName: "house.fill")
                Text(house.color.symbol)
            }
        }
        .font(.system(isCompact ? .footnote : .subheadline, design: .rounded, weight: .heavy))
        .foregroundStyle(van.color.boardColor)
        .padding(.horizontal, isCompact ? 8 : 10)
        .padding(.vertical, isCompact ? 5 : 6)
        .background {
            Capsule()
                .fill(van.color.boardColor.opacity(0.12))
                .overlay { Capsule().stroke(van.color.boardColor.opacity(0.22), lineWidth: 1) }
        }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("\(van.color.displayName) \(van.color.accessibilitySymbolName) van to \(van.color.displayName.lowercased()) \(van.color.accessibilitySymbolName) house")
    }

    #if DEBUG || MULTIVAN_INTERNAL
    /// Swaps between the flat map and the 3D table; the switcher animates one into
    /// the other. It sets the same preference as Settings, so the choice sticks.
    private var boardStyleButton: some View {
        let isDiorama = shownBoard == .diorama
        return Button(action: toggleBoardStyle) { circleIcon(isDiorama ? "map.fill" : "cube.fill") }
            .buttonStyle(.multiVanHUDCircle)
            .accessibilityLabel(isDiorama ? "Show 2D map" : "Show 3D diorama")
            .accessibilityHint(isDiorama ? "Lay the board flat" : "Tilt the board up into a 3D table")
            // Autoplay pins its own board.
            .disabled(autoplay != nil)
    }

    private func toggleBoardStyle() {
        let next: MultiVanBoardStyle = shownBoard == .diorama ? .flat : .diorama
        // Asking for 3D in Low Power Mode is the player's answer to the 2D fallback.
        if next == .diorama, ProcessInfo.processInfo.isLowPowerModeEnabled,
           settingsService.settings.usesFlatBoardInLowPowerMode {
            settingsService.setUsesFlatBoardInLowPowerMode(false)
        }
        settingsService.setBoardStyle(next)
    }
    #endif

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
        .padding(.horizontal, 12)
        .padding(.vertical, 7)
        .background {
            Capsule()
                .fill(tint.opacity(0.12))
                .overlay { Capsule().stroke(tint.opacity(0.20), lineWidth: 1) }
        }
        .animation(reducesExtraAnimations ? nil : .easeOut(duration: 0.18), value: isOverPar)
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("Changes \(engine.changeCount), par \(engine.level.parChanges)")
    }

    /// The controls in a cream tray of their own, floating over the board.
    private var controlBar: some View {
        controls
            .padding(12)
            .background { MultiVanHUDCardBackground(cornerRadius: 30) }
    }

    /// Every phase's buttons share one footprint and the same two places: going
    /// back on the left, going on on the right. So nothing moves under a finger
    /// when a press changes the phase, and the board never changes size.
    private var controls: some View {
        let isWin = engine.phase == .finished && engine.outcome == .win
        return ZStack {
            controlRow(isShown: engine.phase == .plan) {
                controlLayout {
                    secondaryButton("Reset switches", systemImage: "arrow.clockwise", action: resetSwitches)
                        .accessibilityHint("Restore the level's initial switch selections")
                    primaryButton("Go", systemImage: "play.fill", action: go)
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
            secondaryButton("Stop", systemImage: "stop.fill") {
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
            .buttonStyle(MultiVanHUDButtonStyle(
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
        .background { MultiVanHUDCardBackground() }
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
        .background { MultiVanHUDCardBackground(cornerRadius: 20) }
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
    private static let controlHeight: CGFloat = 60

    private func primaryButton(_ title: String, systemImage: String? = nil, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            controlLabel(title, systemImage: systemImage)
        }
        .buttonStyle(MultiVanHUDButtonStyle(isProminent: true))
    }

    /// Narrow beside the primary button, with its icon over its title.
    private func secondaryButton(_ title: String, systemImage: String? = nil, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            controlLabel(title, systemImage: systemImage, isStacked: true)
        }
        .buttonStyle(MultiVanHUDButtonStyle())
        .frame(maxWidth: dynamicTypeSize.isAccessibilitySize ? .infinity : 124)
    }

    private func controlLabel(_ title: String, systemImage: String?, isStacked: Bool = false) -> some View {
        Group {
            if let systemImage {
                Label(title, systemImage: systemImage)
                    .labelStyle(MultiVanControlLabelStyle(isStacked: isStacked))
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

/// The primary buttons' big icon and title side by side; the secondary ones'
/// blue icon over a smaller title.
private struct MultiVanControlLabelStyle: LabelStyle {
    let isStacked: Bool

    func makeBody(configuration: Configuration) -> some View {
        if isStacked {
            VStack(spacing: 2) {
                configuration.icon
                    .font(.system(.title3, design: .rounded, weight: .heavy))
                    .foregroundStyle(TRGameplayStyle.Colors.primaryBlue)
                configuration.title
                    .font(.system(.subheadline, design: .rounded, weight: .bold))
            }
            .padding(.vertical, 6)
        } else {
            HStack(spacing: 10) {
                configuration.icon
                configuration.title
            }
            .font(.system(.title2, design: .rounded, weight: .heavy))
        }
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
