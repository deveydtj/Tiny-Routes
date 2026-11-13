import SwiftUI
import Observation

/// Which tips the player has completed, so each one appears unprompted once.
/// Reset with the rest of the player's progress.
struct MultiVanTutorialProgress {
    static let storageKey = "multiVanTutorial.seenTips"

    let defaults: UserDefaults

    init(defaults: UserDefaults = .standard) { self.defaults = defaults }

    func hasSeen(_ trigger: MultiVanTutorialTip.Trigger, levelID: String) -> Bool {
        seen.contains(Self.key(trigger, levelID: levelID))
    }

    func markSeen(_ trigger: MultiVanTutorialTip.Trigger, levelID: String) {
        var seen = seen
        guard seen.insert(Self.key(trigger, levelID: levelID)).inserted else { return }
        defaults.set(seen.sorted(), forKey: Self.storageKey)
    }

    func reset() { defaults.removeObject(forKey: Self.storageKey) }

    private var seen: Set<String> { Set(defaults.stringArray(forKey: Self.storageKey) ?? []) }

    private static func key(_ trigger: MultiVanTutorialTip.Trigger, levelID: String) -> String {
        "\(levelID):\(trigger.rawValue)"
    }
}

/// Guides the player through actions on the real board.
@Observable
final class MultiVanTutorialPresentation {
    struct Cue: Equatable {
        enum Target: Equatable { case go, stop, switches, watch, hint, pause }

        let text: String
        let target: Target

        var symbol: String {
            switch target {
            case .go: "play.fill"
            case .stop: "stop.fill"
            case .switches: "hand.tap.fill"
            case .watch: "eye.fill"
            case .hint: "lightbulb.fill"
            case .pause: "pause.fill"
            }
        }
    }

    static let failuresBeforeHint = MultiVanAssistance.failuresBeforeHint
    static let secondsBeforeReminder = 20
    static let missedTapsBeforeReminder = 3

    private(set) var activeTip: MultiVanTutorialTip?
    private(set) var failureTip: MultiVanTutorialTip?
    private(set) var failureHint: String?
    private(set) var failureCount = 0
    private(set) var isReminding = false
    private var hasShownReminder = false
    private var playedSeconds = 0
    private var missedTaps = 0
    private var retrySpotlightNodeIDs: [String] = []
    private var reachedPracticeEdge = false
    private var practicedStop = false
    /// One step of the recorded solution, ringed and spelled out while planning.
    private(set) var nudge: MultiVanAssistance.Nudge?
    private var wantsNudge = false
    /// The furthest this visit has gone up the help ladder. Help never costs stars.
    private(set) var highestStep = MultiVanAssistance.Step.none

    var observesPracticeEdge: Bool { !reachedPracticeEdge && activeTip?.practiceEdgeID != nil }

    /// Any level with something to say can remind: a hint, or a tip to practice.
    static func supportsReminders(level: MultiVanLevel) -> Bool {
        level.hint != nil || level.tutorialTip(for: .start) != nil
    }

    /// The teaching levels bring their reminder back with the hint, after two
    /// failures. Later boards keep it for the ladder's next step.
    static func remindsEarly(level: MultiVanLevel) -> Bool {
        guard level.id.hasPrefix("level_"), let number = Int(level.id.split(separator: "_").last ?? "") else { return false }
        return (1...9).contains(number)
    }

    static func failuresBeforeReminder(level: MultiVanLevel) -> Int {
        remindsEarly(level: level) ? failuresBeforeHint : MultiVanAssistance.failuresBeforeSpotlight
    }

    /// The switches a reminder rings: the hint's own, or the crash tip's.
    static func hintFocusNodeIDs(level: MultiVanLevel) -> [String] {
        level.hintFocusNodeIDs.isEmpty ? level.tutorialTip(for: .crash)?.focusNodeIDs ?? [] : level.hintFocusNodeIDs
    }

    /// The failure card can offer one step once the hint has been shown.
    var canOfferNudge: Bool { failureCount >= Self.failuresBeforeHint }

    /// A deliberate ask for one step, or the ladder reaching it. The step itself
    /// is worked out by `prepareNudge` once the board is back in planning.
    func requestNudge() { wantsNudge = true }

    /// Pins one step of `solution` for the player to make. Nothing is shown
    /// without a recorded solution: help never guesses.
    func prepareNudge(engine: MultiVanEngine, solution: MultiVanSolution?) {
        guard wantsNudge, engine.phase == .plan, let solution else { return }
        wantsNudge = false
        nudge = MultiVanAssistance.nudge(engine: engine, solution: solution)
        highestStep = max(highestStep, .nudge)
    }

    /// The nudge has done its work once its switch is set: one step, not the answer.
    func switchChanged(engine: MultiVanEngine) {
        guard let nudge, let nodeID = nudge.nodeID, let edgeID = nudge.edgeID else { return }
        if engine.runtimeGraph.nodesByID[nodeID]?.activeOutgoingEdgeID == edgeID { self.nudge = nil }
    }

    var needsPlayTime: Bool { !hasShownReminder && playedSeconds < Self.secondsBeforeReminder }

    func playedSecond(engine: MultiVanEngine) {
        guard needsPlayTime, engine.phase != .finished else { return }
        playedSeconds += 1
        remindIfStuck(engine: engine)
    }

    func missedTap(engine: MultiVanEngine) {
        guard !hasShownReminder, engine.phase != .finished else { return }
        missedTaps = min(missedTaps + 1, Self.missedTapsBeforeReminder)
        remindIfStuck(engine: engine)
    }

    func usedControl() { missedTaps = 0 }

    private func remindIfStuck(engine: MultiVanEngine) {
        guard playedSeconds >= Self.secondsBeforeReminder,
              missedTaps >= Self.missedTapsBeforeReminder else { return }
        showReminder(level: engine.level)
        observeRun(engine: engine)
    }

    private func showReminder(level: MultiVanLevel) {
        guard Self.supportsReminders(level: level), !hasShownReminder else { return }
        hasShownReminder = true
        isReminding = true
        highestStep = max(highestStep, .spotlight)
        if activeTip == nil { reopen(level: level) }
    }

    func begin(level: MultiVanLevel, progress: MultiVanTutorialProgress) {
        reset()
        guard !progress.hasSeen(.start, levelID: level.id) else { return }
        reopen(level: level)
    }

    func reopen(level: MultiVanLevel) {
        activeTip = level.tutorialTip(for: .start)
        reachedPracticeEdge = false
        practicedStop = false
    }

    func complete(level: MultiVanLevel, progress: MultiVanTutorialProgress) {
        if activeTip != nil { progress.markSeen(.start, levelID: level.id) }
        activeTip = nil
        isReminding = false
    }

    func cue(engine: MultiVanEngine) -> Cue? {
        if let nudge, engine.phase == .plan {
            return Cue(text: nudge.text, target: nudge.nodeID == nil ? .go : .hint)
        }
        guard let tip = activeTip else {
            guard isReminding, engine.phase != .finished, let hint = engine.level.hint else { return nil }
            // Merge still gets to teach by showing the first crash.
            if failureCount == 0, engine.level.tutorialTip(for: .crash) != nil {
                return engine.phase == .plan ? Cue(text: "Tap Go to try the routes.", target: .go) : nil
            }
            return Cue(text: hint, target: .hint)
        }
        switch engine.phase {
        case .plan:
            switch tip.practice {
            case .route:
                return routeCue(engine: engine, text: isReminding ? routeHint(for: tip) : tip.body)
            case .stop where practicedStop || !engine.previewRoutes.contains(where: { $0.ending == .loopLimit }):
                return routeCue(engine: engine, text: routeHint(for: tip))
            case .live:
                let needsReset = tip.focusNodeIDs.contains { id in
                    guard let initial = engine.level.initialSwitchEdges[id] else { return false }
                    return engine.runtimeGraph.nodesByID[id]?.activeOutgoingEdgeID != initial
                }
                if needsReset { return Cue(text: "Tap ⚡ to restore the starting route.", target: .switches) }
                return Cue(text: "Tap Go to try the ⚡ switch.", target: .go)
            case .deliver where isReminding:
                return Cue(text: "Tap the blue Go button.", target: .go)
            default:
                return Cue(text: tip.body, target: .go)
            }
        case .run:
            switch tip.practice {
            case .stop where !practicedStop:
                if reachedPracticeEdge || (isReminding && engine.previewRoutes.contains(where: { $0.ending == .loopLimit })) {
                    return Cue(text: "Tap Stop to plan again.", target: .stop)
                }
                if engine.previewRoutes.contains(where: { $0.ending == .loopLimit }) {
                    return Cue(text: "Watch the van take the loop.", target: .watch)
                }
            case .live:
                if engine.previewRoutes.allSatisfy({ $0.ending == .matchingHouse || $0.ending == .offRoad }) {
                    return Cue(text: "Watch the vans head home.", target: .watch)
                }
                if reachedPracticeEdge {
                    let locked = engine.lockedSwitchNodeIDs
                    if tip.focusNodeIDs.contains(where: { engine.level.liveSwitchNodeIDs.contains($0) && !locked.contains($0) }) {
                        return Cue(text: "Now tap the ⚡ switch!", target: .switches)
                    }
                }
                return Cue(text: isReminding ? engine.level.hint ?? tip.body : tip.body, target: .watch)
            default:
                if isReminding, engine.previewRoutes.contains(where: {
                    $0.ending != .matchingHouse && $0.ending != .offRoad
                }) {
                    return Cue(text: "Tap Stop to change the route.", target: .stop)
                }
            }
        case .finished:
            break
        }
        return nil
    }

    private func routeCue(engine: MultiVanEngine, text: String) -> Cue {
        if engine.previewRoutes.allSatisfy({ $0.ending == .matchingHouse }) {
            return Cue(text: "Routes ready! Tap Go.", target: .go)
        }
        return Cue(text: text, target: .switches)
    }

    private func routeHint(for tip: MultiVanTutorialTip) -> String {
        let switches = tip.focusNodeIDs.count == 1 ? "switch" : "switches"
        return "Tap the glowing \(switches). Look for ✓."
    }

    func spotlightNodeIDs(engine: MultiVanEngine, cue: Cue?) -> [String] {
        if let nudge, engine.phase == .plan { return nudge.nodeID.map { [$0] } ?? [] }
        if cue?.target == .switches, let activeTip {
            return activeTip.focusNodeIDs.filter {
                engine.phase == .plan || engine.level.liveSwitchNodeIDs.contains($0)
            }
        }
        if engine.phase == .plan, activeTip?.practice == .deliver {
            return activeTip?.focusNodeIDs ?? []
        }
        if engine.phase == .plan, isReminding, failureCount > 0 {
            let focus = Self.hintFocusNodeIDs(level: engine.level)
            if !focus.isEmpty { return focus }
        }
        return engine.phase == .plan ? retrySpotlightNodeIDs : []
    }

    func go(engine: MultiVanEngine, progress: MultiVanTutorialProgress) {
        usedControl()
        if let tip = activeTip, tip.practice == nil || tip.practice == .deliver {
            complete(level: engine.level, progress: progress)
        }
        reachedPracticeEdge = false
        retrySpotlightNodeIDs = []
        failureTip = nil
        failureHint = nil
        // A nudge for the run itself stays up until Go; then the player is on their own.
        nudge = nil
    }

    func observeRun(engine: MultiVanEngine) {
        guard engine.phase == .run, observesPracticeEdge,
              let edgeID = activeTip?.practiceEdgeID else { return }
        reachedPracticeEdge = engine.vans.contains { $0.currentEdgeID == edgeID }
    }

    func stopped() {
        usedControl()
        if activeTip?.practice == .stop { practicedStop = true }
    }

    /// Called once per failure, as its card appears. A first crash explains
    /// timing; repeated failures earn the level's hint.
    func failed(_ outcome: MultiVanEngine.Outcome, level: MultiVanLevel, progress: MultiVanTutorialProgress) {
        failureCount += 1
        if failureCount >= Self.failuresBeforeReminder(level: level) { showReminder(level: level) }
        if failureCount >= MultiVanAssistance.failuresBeforeNudge { wantsNudge = true }
        failureTip = nil
        failureHint = nil
        if case .failCrash = outcome, let tip = level.tutorialTip(for: .crash),
           !progress.hasSeen(.crash, levelID: level.id) {
            progress.markSeen(.crash, levelID: level.id)
            failureTip = tip
            return
        }
        if failureCount >= Self.failuresBeforeHint {
            highestStep = max(highestStep, .hint)
            failureHint = level.hint
            if failureHint == nil, isReminding, let tip = activeTip {
                failureHint = tip.practice == .route || tip.practice == .stop ? "Try a different route. Look for ✓." : tip.body
            }
        }
    }

    /// Back to planning after a failure: the crash card's pieces stay ringed.
    func retried() {
        usedControl()
        retrySpotlightNodeIDs = failureTip?.focusNodeIDs ?? []
        failureTip = nil
        failureHint = nil
    }

    func reset() {
        activeTip = nil
        isReminding = false
        hasShownReminder = false
        playedSeconds = 0
        missedTaps = 0
        reachedPracticeEdge = false
        practicedStop = false
        retrySpotlightNodeIDs = []
        failureTip = nil
        failureHint = nil
        failureCount = 0
        nudge = nil
        wantsNudge = false
        highestStep = .none
    }
}

/// A soft ring that breathes around a board piece a tip is about. It never takes
/// taps, so the switch under it still works.
struct MultiVanTutorialSpotlight: View {
    let reduceMotion: Bool
    @State private var isPulsing = false

    static let diameter: CGFloat = 58

    var body: some View {
        ZStack {
            Circle()
                .fill(TRGameplayStyle.Colors.resultSoftYellow.opacity(0.28))
            Circle()
                .stroke(TRGameplayStyle.Colors.orangeAccent, style: StrokeStyle(lineWidth: 3, dash: [7, 5]))
        }
        .frame(width: Self.diameter, height: Self.diameter)
        .scaleEffect(reduceMotion || !isPulsing ? 1 : 1.18)
        .opacity(reduceMotion || !isPulsing ? 1 : 0.7)
        .allowsHitTesting(false)
        .accessibilityHidden(true)
        .onAppear { pulse(!reduceMotion) }
        .onChange(of: reduceMotion) { _, reduced in pulse(!reduced) }
    }

    private func pulse(_ enabled: Bool) {
        guard enabled else {
            isPulsing = false
            return
        }
        withAnimation(.easeInOut(duration: 0.7).repeatForever(autoreverses: true)) { isPulsing = true }
    }
}

