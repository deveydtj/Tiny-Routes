import Foundation
import Observation

enum MultiVanTapResult: Equatable {
    case accepted
    case rejectedFrozen
    case rejectedLocked
    case notASwitch
}

struct MultiVanVanState {
    enum Status: Equatable {
        case waiting, driving, parked, crashed, stuck
    }

    let id: String
    let color: VanColor
    fileprivate(set) var distanceAlongEdge = 0.0
    fileprivate(set) var status: Status = .waiting
    fileprivate(set) var previousEdgeID: String?
    fileprivate var edge: RuntimeRouteEdge?
    fileprivate let startPosition: RoadPoint

    var currentEdgeID: String? { edge?.id }

    var position: RoadPoint {
        edge?.roadPath.point(atDistance: distanceAlongEdge) ?? startPosition
    }
}

@Observable
final class MultiVanEngine {
    enum Phase: Equatable {
        case plan
        case run
        case finished
    }

    enum Outcome: Equatable {
        case win
        case failWrongHouse(vanID: String, houseNodeID: String)
        case failStuck(vanID: String, nodeID: String)
        case failCrash(vanIDs: [String], point: RoadPoint)
    }

    let level: MultiVanLevel
    let tuning: MultiVanTuning
    private(set) var runtimeGraph: RuntimeRouteGraph
    private(set) var phase: Phase = .plan
    private(set) var outcome: Outcome?
    private(set) var lastFailPoint: RoadPoint?
    private(set) var vans: [MultiVanVanState] = []
    private(set) var previewRoutes: [MultiVanPreviewRoute] = []
    private var remainder: TimeInterval = 0
    private var completedSteps = 0

    @ObservationIgnored private var pendingEvents: [MultiVanEvent] = []
    @ObservationIgnored private var deliveryCombo = 0

    func drainEvents() -> [MultiVanEvent] {
        let events = pendingEvents
        pendingEvents.removeAll(keepingCapacity: true)
        return events
    }

    var runTime: TimeInterval { Double(completedSteps) * tuning.stepDuration }

    /// Derived from current physical positions, including immediately after phase changes.
    var lockedSwitchNodeIDs: Set<String> {
        guard phase == .run else { return [] }
        return Set(runtimeGraph.nodesByID.values.compactMap { node in
            guard (2...4).contains(node.outgoingEdgeIDs.count) else { return nil }
            if !level.liveSwitchNodeIDs.contains(node.id) { return node.id }
            return vans.contains { van in
                guard van.status == .driving else { return false }
                let point = van.position
                return hypot(point.x - node.x, point.y - node.y) <= tuning.liveSwitchLockRadius
            } ? node.id : nil
        })
    }

    init(level: MultiVanLevel, tuning: MultiVanTuning = .default) throws {
        self.level = level
        self.tuning = tuning
        runtimeGraph = try RuntimeRouteGraph.make(from: level.graph) { $0.availabilityRule }
        // Vans first: previews are traced from each van's state.
        resetVans()
        resetSwitches()
    }

    func go() {
        guard phase == .plan else { return }
        resetVans()
        remainder = 0
        completedSteps = 0
        lastFailPoint = nil
        phase = .run
        deliveryCombo = 0
        pendingEvents.append(.go)
        var failure: (Outcome, RoadPoint)?
        for index in vans.indices where level.vans[index].departDelay <= 0 {
            if let outcome = depart(&vans[index], from: level.vans[index].startNodeID), failure == nil {
                failure = (outcome, vans[index].position)
            }
        }
        if let failure { finish(with: failure.0, failPoint: failure.1) }
        checkForWin(vans)
        updatePreviewRoutes()
    }

    func stop() {
        guard phase == .run else { return }
        resetRun()
    }

    func retry() {
        guard phase == .finished else { return }
        resetRun()
        outcome = nil
    }

    private func resetRun() {
        resetVans()
        remainder = 0
        completedSteps = 0
        phase = .plan
        updatePreviewRoutes()
    }

    func advance(by realTime: TimeInterval) {
        guard phase == .run, realTime.isFinite, realTime > 0,
              tuning.stepDuration.isFinite, tuning.stepDuration > 0,
              tuning.vanSpeed.isFinite, tuning.vanSpeed >= 0,
              (remainder + realTime).isFinite else { return }

        // Step on local copies and publish once per call: observed-property
        // access on every step dominated simulation cost.
        var vans = self.vans
        var completedSteps = self.completedSteps
        // Preserve all elapsed time; frame-delta clamping belongs to the UI.
        var remainder = self.remainder + realTime
        defer {
            if completedSteps != self.completedSteps {
                // Previews only change when a van reaches a new road or leaves the board.
                let routeChanged = !zip(self.vans, vans).allSatisfy {
                    $0.currentEdgeID == $1.currentEdgeID && $0.status == $1.status
                }
                self.vans = vans
                self.completedSteps = completedSteps
                if routeChanged { updatePreviewRoutes() }
            }
            self.remainder = remainder
        }
        let tolerance = min(1e-9, tuning.stepDuration * 1e-7)
        while phase == .run, remainder + tolerance >= tuning.stepDuration {
            let runTime = Double(completedSteps) * tuning.stepDuration
            // All vans share this step's start time. Non-grid delays round up to
            // the next step boundary; no van receives distance before departure.
            var failure: (Outcome, RoadPoint)?
            for index in vans.indices {
                var arrivalFailure: Outcome?
                if vans[index].status == .waiting,
                   runTime >= level.vans[index].departDelay {
                    arrivalFailure = depart(&vans[index], from: level.vans[index].startNodeID)
                }
                if let outcome = move(&vans[index], by: tuning.vanSpeed * tuning.stepDuration) {
                    arrivalFailure = outcome
                }
                if let arrivalFailure, failure == nil {
                    failure = (arrivalFailure, vans[index].position)
                }
            }
            // Arrival failures take precedence over crashes in the same step.
            // Authored van order selects arrivals and then the first crashing pair.
            if let failure {
                finish(with: failure.0, failPoint: failure.1)
            } else {
                checkForCrash(&vans)
                checkForWin(vans)
            }
            completedSteps += 1
            // A tiny negative remainder preserves timing debt from the tolerance.
            remainder -= tuning.stepDuration
        }
    }

    private func finish(with outcome: Outcome, failPoint: RoadPoint? = nil) {
        guard phase == .run else { return }
        switch outcome {
        case .win:
            pendingEvents.append(.allDelivered)
        case let .failCrash(_, point):
            pendingEvents.append(.crashed(point: point))
        case let .failWrongHouse(vanID, _):
            pendingEvents.append(.wrongHouse(vanID: vanID))
        case .failStuck:
            break
        }
        self.outcome = outcome
        lastFailPoint = failPoint
        phase = .finished
    }

    private func checkForWin(_ vans: [MultiVanVanState]) {
        if !vans.isEmpty, vans.allSatisfy({ $0.status == .parked }) {
            finish(with: .win)
        }
    }

    private func checkForCrash(_ vans: inout [MultiVanVanState]) {
        for first in vans.indices where vans[first].status == .driving {
            for second in (first + 1)..<vans.count where vans[second].status == .driving {
                let a = vans[first].position
                let b = vans[second].position
                guard hypot(a.x - b.x, a.y - b.y) < tuning.crashDistance else { continue }
                let point = RoadPoint(x: (a.x + b.x) / 2, y: (a.y + b.y) / 2)
                vans[first].status = .crashed
                vans[second].status = .crashed
                finish(with: .failCrash(vanIDs: [vans[first].id, vans[second].id], point: point), failPoint: point)
                return
            }
        }
    }

    private func resetVans() {
        vans = level.vans.map { van in
            let node = runtimeGraph.nodesByID[van.startNodeID]
            return MultiVanVanState(
                id: van.id,
                color: van.color,
                status: node == nil ? .stuck : .waiting,
                startPosition: RoadPoint(x: node?.x ?? 0, y: node?.y ?? 0)
            )
        }
    }

    private func depart(_ van: inout MultiVanVanState, from nodeID: String) -> Outcome? {
        if let house = level.houses.first(where: { $0.nodeID == nodeID }) {
            van.status = .parked
            if house.color != van.color {
                return .failWrongHouse(vanID: van.id, houseNodeID: nodeID)
            }
            deliveryCombo += 1
            pendingEvents.append(.delivered(vanID: van.id, comboIndex: deliveryCombo))
            return nil
        }
        guard let node = runtimeGraph.nodesByID[nodeID],
              let edgeID = node.activeOutgoingEdgeID,
              node.outgoingEdgeIDs.contains(edgeID),
              let edge = runtimeGraph.edgesByID[edgeID],
              edge.fromNodeID == nodeID else {
            van.status = .stuck
            return .failStuck(vanID: van.id, nodeID: nodeID)
        }
        van.previousEdgeID = van.currentEdgeID
        van.edge = edge
        van.distanceAlongEdge = 0
        van.status = .driving
        return nil
    }

    private func move(_ van: inout MultiVanVanState, by distance: Double) -> Outcome? {
        var distance = distance
        var edgesWithoutProgress = Set<String>()
        while van.status == .driving, let edge = van.edge {
            let length = edge.roadPath.totalLength
            guard length.isFinite, length >= 0 else {
                van.status = .stuck
                return nil
            }
            let remaining = max(0, length - van.distanceAlongEdge)
            // Absorb rounding at exact arrivals without losing positive leftovers.
            if remaining - distance > 1e-12 {
                van.distanceAlongEdge += distance
                return nil
            }
            let leftover = max(0, distance - remaining)
            if leftover == distance {
                // A repeated edge without consuming distance is a degenerate cycle.
                guard edgesWithoutProgress.insert(edge.id).inserted else {
                    van.status = .stuck
                    return nil
                }
            } else {
                edgesWithoutProgress.removeAll(keepingCapacity: true)
            }
            van.distanceAlongEdge = length
            if let failure = depart(&van, from: edge.toNodeID) { return failure }
            distance = leftover
        }
        return nil
    }

    /// The plan counts forward taps from the starting settings, not tap history.
    var changeCount: Int {
        level.graph.nodes.reduce(0) { count, authoredNode in
            guard let node = runtimeGraph.nodesByID[authoredNode.id],
                  (2...4).contains(node.outgoingEdgeIDs.count),
                  let activeEdgeID = node.activeOutgoingEdgeID,
                  let currentIndex = node.outgoingEdgeIDs.firstIndex(of: activeEdgeID) else {
                return count
            }
            let initialIndex = level.initialSwitchEdges[node.id].flatMap {
                node.outgoingEdgeIDs.firstIndex(of: $0)
            } ?? 0
            let exitCount = node.outgoingEdgeIDs.count
            return count + (currentIndex - initialIndex + exitCount) % exitCount
        }
    }

    @discardableResult
    func tapSwitch(nodeID: String) -> MultiVanTapResult {
        // Non-switch nodes are not feedback interactions.
        guard let node = runtimeGraph.nodesByID[nodeID],
              (2...4).contains(node.outgoingEdgeIDs.count) else {
            return .notASwitch
        }
        var result = MultiVanTapResult.accepted
        defer {
            pendingEvents.append(result == .accepted ? .switchTapped : .tapRejected(nodeID: nodeID))
        }
        if phase == .run {
            guard level.liveSwitchNodeIDs.contains(nodeID) else { result = .rejectedFrozen; return result }
            guard !lockedSwitchNodeIDs.contains(nodeID) else { result = .rejectedLocked; return result }
        } else if phase != .plan {
            result = .rejectedFrozen
            return result
        }
        let currentIndex = node.activeOutgoingEdgeID.flatMap {
            node.outgoingEdgeIDs.firstIndex(of: $0)
        } ?? 0
        runtimeGraph.nodesByID[nodeID]?.activeOutgoingEdgeID =
            node.outgoingEdgeIDs[(currentIndex + 1) % node.outgoingEdgeIDs.count]
        updatePreviewRoutes()
        return .accepted
    }

    func resetSwitches() {
        for node in level.graph.nodes {
            let initialEdgeID = level.initialSwitchEdges[node.id].flatMap {
                node.outgoingEdgeIDs.contains($0) ? $0 : nil
            } ?? node.outgoingEdgeIDs.first
            runtimeGraph.nodesByID[node.id]?.activeOutgoingEdgeID = initialEdgeID
        }
        updatePreviewRoutes()
    }

    /// Each preview starts where its van is now: road already driven drops away,
    /// and a parked, crashed or stuck van has no line at all.
    private func updatePreviewRoutes() {
        previewRoutes = zip(level.vans, vans).map { van, state in
            switch state.status {
            case .driving:
                guard let edge = state.edge else { return .init(edgeIDs: [], ending: .offRoad) }
                return MultiVanRoutePreview.trace(
                    from: edge.toNodeID, color: van.color, after: [edge.id],
                    graph: runtimeGraph, houses: level.houses,
                    edgeLimit: tuning.previewEdgeLimit
                )
            case .waiting:
                return MultiVanRoutePreview.trace(
                    van: van, graph: runtimeGraph, houses: level.houses,
                    edgeLimit: tuning.previewEdgeLimit
                )
            case .parked, .crashed, .stuck:
                return MultiVanPreviewRoute(edgeIDs: [], ending: .offRoad)
            }
        }
    }
}
