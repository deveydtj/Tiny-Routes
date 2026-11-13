import Foundation

/// A level's recorded solution: the script the tests prove wins at par, shipped
/// with the app so help can show a step that is known to be right. The packaging
/// check holds the bundled copies to the tested ones, byte for byte.
struct MultiVanSolution: Decodable, Equatable {
    struct LiveTap: Decodable, Equatable {
        let atTime: TimeInterval
        let nodeID: String
    }

    let planTaps: [String]
    let liveTaps: [LiveTap]

    private enum CodingKeys: String, CodingKey {
        case planTaps, liveTaps
    }

    init(planTaps: [String] = [], liveTaps: [LiveTap] = []) {
        self.planTaps = planTaps
        self.liveTaps = liveTaps
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        planTaps = try container.decodeIfPresent([String].self, forKey: .planTaps) ?? []
        liveTaps = try container.decodeIfPresent([LiveTap].self, forKey: .liveTaps) ?? []
    }

    /// Nil when the level has no recorded solution in `bundle`: help then stops
    /// at the hint rather than guess a step.
    static func load(levelID: String, bundle: Bundle = .main) -> Self? {
        guard let url = bundle.url(forResource: "\(levelID).solution", withExtension: "json", subdirectory: "PrototypeSolutions"),
              let data = try? Data(contentsOf: url) else { return nil }
        return try? JSONDecoder().decode(Self.self, from: data)
    }
}

/// Help for a player who is stuck, in steps that each give a little more.
/// None of it costs stars or progress.
enum MultiVanAssistance {
    /// How far up the ladder an attempt went.
    enum Step: Int, Comparable {
        case none, hint, spotlight, nudge

        static func < (lhs: Self, rhs: Self) -> Bool { lhs.rawValue < rhs.rawValue }
    }

    /// Failures on a level before each step. Provisional until playtests.
    static let failuresBeforeHint = 2
    static let failuresBeforeSpotlight = 4
    static let failuresBeforeNudge = 6

    /// One step of the recorded solution: a switch and what to do with it.
    struct Nudge: Equatable {
        /// The switch to ring; nil when the plan already matches the solution.
        let nodeID: String?
        /// The exit that switch should take; nil for a tap made during the run.
        let edgeID: String?
        let text: String
    }

    /// Every switch's exit once the solution's planning taps are made from the
    /// authored settings.
    static func plannedSelections(level: MultiVanLevel, solution: MultiVanSolution) -> [String: String] {
        var selections: [String: String] = [:]
        for node in level.graph.nodes where (2...4).contains(node.outgoingEdgeIDs.count) {
            let initial = level.initialSwitchEdges[node.id].flatMap { node.outgoingEdgeIDs.firstIndex(of: $0) } ?? 0
            let taps = solution.planTaps.filter { $0 == node.id }.count
            selections[node.id] = node.outgoingEdgeIDs[(initial + taps) % node.outgoingEdgeIDs.count]
        }
        return selections
    }

    /// The next step of `solution` the player has not made yet. Planning steps
    /// come in the script's order; then the first tap made during the run.
    static func nudge(engine: MultiVanEngine, solution: MultiVanSolution) -> Nudge {
        let level = engine.level
        let graph = engine.runtimeGraph
        let target = plannedSelections(level: level, solution: solution)
        var order: [String] = []
        for nodeID in solution.planTaps + target.keys.sorted() where !order.contains(nodeID) { order.append(nodeID) }
        for nodeID in order {
            guard let node = graph.nodesByID[nodeID], let edgeID = target[nodeID],
                  node.activeOutgoingEdgeID != edgeID,
                  let wanted = node.outgoingEdgeIDs.firstIndex(of: edgeID) else { continue }
            // Counted in taps, so the step reads the same on the flat map and
            // from any side of the 3D table.
            let current = node.activeOutgoingEdgeID.flatMap { node.outgoingEdgeIDs.firstIndex(of: $0) } ?? 0
            let taps = (wanted - current + node.outgoingEdgeIDs.count) % node.outgoingEdgeIDs.count
            let times = taps == 1 ? "once" : taps == 2 ? "twice" : "\(taps) times"
            return Nudge(nodeID: nodeID, edgeID: edgeID, text: "Tap the glowing switch \(times).")
        }
        if let tap = solution.liveTaps.min(by: { $0.atTime < $1.atTime }) {
            let seconds = max(1, Int(tap.atTime.rounded()))
            return Nudge(
                nodeID: tap.nodeID, edgeID: nil,
                text: "Your routes are set. Press Go, then tap the glowing ⚡ switch about \(seconds) second\(seconds == 1 ? "" : "s") in."
            )
        }
        return Nudge(nodeID: nil, edgeID: nil, text: "Your switches match a working plan. Press Go.")
    }
}
