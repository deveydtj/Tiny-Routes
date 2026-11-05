import UIKit

enum MultiVanEvent: Equatable {
    case switchTapped
    case tapRejected(nodeID: String)
    case go
    case delivered(vanID: String, comboIndex: Int)
    case allDelivered
    case crashed(point: RoadPoint)
    case wrongHouse(vanID: String)
}

@MainActor
enum MultiVanFeedback {
    static func process(
        drainEvents: () -> [MultiVanEvent],
        settings: UserSettings,
        soundPlayer: MultiVanSoundPlayer,
        playHaptic: @MainActor (MultiVanHaptic) -> Void = { $0.play() },
        reactVisually: @MainActor (MultiVanEvent) -> Void = { _ in }
    ) {
        soundPlayer.update(settings: settings)
        for event in drainEvents() {
            MultiVanHaptic.feedback(for: event, hapticsEnabled: settings.areHapticsEnabled).map(playHaptic)
            soundPlayer.play(event)
            reactVisually(event)
        }
    }
}

/// UI-owned, bounded reveal state. Tokens reject completions from an earlier run.
struct MultiVanWinPresentation {
    static let starInterval = 0.22
    static let settleDuration = 0.24
    /// The card waits for the win's confetti to land, so it doesn't hide the
    /// shower: the diorama's burst starts 0.45 s in and its highest-thrown paper
    /// is down about 1.37 s later.
    static let confettiHold = 1.85

    private(set) var id: UUID?
    private(set) var rating = 0
    private(set) var revealedStars = 0
    private(set) var showsActions = false

    mutating func begin(engine: MultiVanEngine, reduceMotion: Bool) -> UUID? {
        guard id == nil, engine.phase == .finished, engine.outcome == .win else { return nil }
        id = UUID()
        rating = MultiVanStars.rating(changes: engine.changeCount, par: engine.level.parChanges)
        if reduceMotion { finishImmediately() }
        return id
    }

    mutating func revealNext(for token: UUID) {
        guard id == token, !showsActions else { return }
        revealedStars = min(revealedStars + 1, rating)
    }

    mutating func complete(for token: UUID) {
        guard id == token, revealedStars == rating else { return }
        showsActions = true
    }

    mutating func finishImmediately() {
        guard id != nil else { return }
        revealedStars = rating
        showsActions = true
    }

    mutating func reset() { self = Self() }

    var accessibilityRating: String {
        switch rating {
        case 3: "Three out of three stars"
        case 2: "Two out of three stars"
        case 1: "One out of three stars"
        default: ""
        }
    }
}

/// Presentation reads authoritative engine state; it never measures van proximity.
struct MultiVanSwitchAppearance {
    let isLive: Bool
    let isAvailable: Bool
    let pulses: Bool
    let accessibilityValue: String
    let accessibilityHint: String

    init(engine: MultiVanEngine, nodeID: String, systemReduceMotion: Bool = false, reducesExtraAnimations: Bool = false) {
        isLive = engine.level.liveSwitchNodeIDs.contains(nodeID)
        isAvailable = engine.phase == .plan || (engine.phase == .run && !engine.lockedSwitchNodeIDs.contains(nodeID))
        pulses = engine.phase == .run && isLive && isAvailable && !systemReduceMotion && !reducesExtraAnimations
        if engine.phase == .finished {
            accessibilityValue = "Locked; run finished"
            accessibilityHint = "Replay or try again to plan a new route"
        } else if isAvailable {
            accessibilityValue = isLive ? "Live switch, available to change" : "Available to change"
            accessibilityHint = "Activate to select the next exit"
        } else if isLive {
            accessibilityValue = "Live switch, temporarily locked while a van is nearby"
            accessibilityHint = "Activate to test availability, or use Stop to return to planning"
        } else {
            accessibilityValue = "Locked during the run"
            accessibilityHint = "Use Stop to return to planning and change this switch"
        }
    }

    var showsLock: Bool { !isAvailable }
    var opacity: Double { !isLive && !isAvailable ? 0.5 : 1 }
    var dialTint: MultiVanSwitchDialView.Tint { isLive ? .live : isAvailable ? .ready : .locked }
    static func accessibilityLabel(node: RuntimeRouteNode, gridRows: Int) -> String {
        // Authored nodes have grid coordinates, but no user-facing names.
        // Rows read from the top, matching the board's inverted Y projection.
        "Switch at column \(Int(node.x) + 1), row \(gridRows - Int(node.y))"
    }

    func routeAccessibilityValue(direction: String, exitCount: Int) -> String {
        "Route selected: \(direction). \(exitCount) exits. \(accessibilityValue)"
    }
}

/// Tokens arrive through the shared single-drain dispatcher, never from a second drain.
struct MultiVanSwitchFeedback {
    private(set) var rejectionTokens: [String: UUID] = [:]

    mutating func process(_ event: MultiVanEvent, reduceMotion: Bool) {
        switch event {
        case .go: reset()
        case let .tapRejected(nodeID) where !reduceMotion:
            rejectionTokens[nodeID] = UUID()
        default: break
        }
    }

    mutating func reset() { rejectionTokens.removeAll() }
}

/// One presentation token per crash event; no simulation state or particle queue.
struct MultiVanCrashEffects {
    struct Impact: Identifiable {
        let id = UUID()
        let point: RoadPoint
    }

    static let shakeDuration = 0.32
    static let impactDuration = 0.48
    private(set) var impact: Impact?

    mutating func process(_ event: MultiVanEvent, reduceMotion: Bool) {
        switch event {
        case .go:
            reset()
        case let .crashed(point) where !reduceMotion:
            impact = Impact(point: point)
        default:
            break
        }
    }

    // A stale completion must never remove a newer run's impact.
    mutating func complete(_ id: UUID) {
        if impact?.id == id { reset() }
    }

    mutating func reset() { impact = nil }

    static func shakeOffset(progress: Double) -> Double {
        guard progress > 0, progress < 1 else { return 0 }
        // Three soft horizontal oscillations, shrinking from at most 4 points.
        return 4 * sin(progress * .pi * 6) * (1 - progress)
    }
}

/// UI playback tokens, bounded by the number of vans. Completed keyframes return
/// to rest; tokens stay stable until the next event/reset, just like houseTokens.
struct MultiVanPersonality {
    struct Reaction: Equatable {
        enum Kind { case departure, delivery, crash }
        let kind: Kind
        let token = UUID()
    }

    private(set) var reactions: [String: Reaction] = [:]

    mutating func process(_ event: MultiVanEvent, engine: MultiVanEngine, reduceMotion: Bool) {
        if event == .go { reset() }
        guard !reduceMotion else { return }
        switch event {
        case .go:
            // Delayed vans are armed now; their view waits for .driving to play.
            for van in engine.vans {
                reactions[van.id] = Reaction(kind: .departure)
            }
        case let .delivered(vanID, _):
            reactions[vanID] = Reaction(kind: .delivery)
        case .crashed:
            guard case let .failCrash(vanIDs, _) = engine.outcome else { return }
            for id in vanIDs where reactions[id]?.kind != .crash {
                reactions[id] = Reaction(kind: .crash)
            }
        default:
            break
        }
    }

    static func isIdle(status: MultiVanVanState.Status, reduceMotion: Bool) -> Bool {
        !reduceMotion && (status == .waiting || status == .parked)
    }

    static func activeReaction(
        _ reaction: Reaction?, status: MultiVanVanState.Status, reduceMotion: Bool
    ) -> Reaction? {
        guard !reduceMotion, let reaction else { return nil }
        if reaction.kind == .departure && status != .driving { return nil }
        return reaction
    }

    mutating func reset() {
        reactions.removeAll()
    }
}

/// Presentation only: destinations and combo values come from the engine.
struct MultiVanCelebration {
    struct Delivery: Identifiable {
        let id = UUID()
        let houseNodeID: String
        let comboIndex: Int

        var label: String { comboIndex > 1 ? "+1  ×\(comboIndex)" : "+1" }
    }

    private(set) var deliveries: [Delivery] = []
    private(set) var houseTokens: [String: UUID] = [:]
    private(set) var confettiID: UUID?
    private var hasCelebrated = false

    mutating func process(_ event: MultiVanEvent, engine: MultiVanEngine, reduceMotion: Bool) {
        switch event {
        case .go:
            reset()
        case let .delivered(vanID, comboIndex):
            guard !reduceMotion,
                  let van = engine.vans.first(where: { $0.id == vanID }),
                  let house = engine.level.houses.first(where: {
                      $0.color == van.color && MultiVanBoardRules.isDelivered(
                          $0, vans: [van], graph: engine.runtimeGraph
                      )
                  }) else { return }
            let delivery = Delivery(houseNodeID: house.nodeID, comboIndex: comboIndex)
            deliveries.append(delivery)
            houseTokens[house.nodeID] = delivery.id
        case .allDelivered:
            guard engine.outcome == .win, !hasCelebrated else { return }
            hasCelebrated = true
            if !reduceMotion { confettiID = UUID() }
        default:
            break
        }
    }

    mutating func complete(_ id: UUID) {
        deliveries.removeAll { $0.id == id }
    }

    mutating func reset() {
        self = Self()
    }

    mutating func suppressMotion() {
        deliveries.removeAll()
        houseTokens.removeAll()
        confettiID = nil
    }
}

enum MultiVanHaptic: Equatable {
    case selection
    case lightImpact
    case mediumImpact
    case success
    case error
    case warning

    static func feedback(for event: MultiVanEvent, hapticsEnabled: Bool = true) -> Self? {
        guard hapticsEnabled else { return nil }
        return switch event {
        case .switchTapped: .selection
        case .tapRejected: .lightImpact
        case .go: .mediumImpact
        case .delivered, .allDelivered: .success
        case .crashed: .error
        case .wrongHouse: .warning
        }
    }

    @MainActor
    func play() {
        switch self {
        case .selection:
            UISelectionFeedbackGenerator().selectionChanged()
        case .lightImpact:
            UIImpactFeedbackGenerator(style: .light).impactOccurred()
        case .mediumImpact:
            UIImpactFeedbackGenerator(style: .medium).impactOccurred()
        case .success:
            UINotificationFeedbackGenerator().notificationOccurred(.success)
        case .error:
            UINotificationFeedbackGenerator().notificationOccurred(.error)
        case .warning:
            UINotificationFeedbackGenerator().notificationOccurred(.warning)
        }
    }
}
