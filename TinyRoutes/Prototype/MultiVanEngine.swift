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
        /// Reached its own house without a parcel it needed. Never counts as delivered.
        case missingCargo
    }

    /// Past a signal's stop line and not yet clear of the area it protects.
    fileprivate struct Passage: Equatable {
        let signalID: String
        let group: Int
        var hasEntered = false
    }

    let id: String
    let color: VanColor
    fileprivate(set) var distanceAlongEdge = 0.0
    fileprivate(set) var status: Status = .waiting
    fileprivate(set) var previousEdgeID: String?
    fileprivate var edge: RuntimeRouteEdge?
    fileprivate let startPosition: RoadPoint
    /// The signal holding this van at its stop line. A held van is still on the
    /// road: it can be hit, and it locks a live switch it stands near.
    fileprivate(set) var heldAtSignalID: String?
    fileprivate var passage: Passage?

    var isHeld: Bool { heldAtSignalID != nil }

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
        /// The van reached its own house without `packageID`, which waits at `pickupNodeID`.
        case failMissingPackage(vanID: String, packageID: String, pickupNodeID: String)
    }

    let level: MultiVanLevel
    let tuning: MultiVanTuning
    private(set) var runtimeGraph: RuntimeRouteGraph
    private(set) var phase: Phase = .plan
    private(set) var outcome: Outcome?
    private(set) var lastFailPoint: RoadPoint?
    private(set) var vans: [MultiVanVanState] = []
    private(set) var previewRoutes: [MultiVanPreviewRoute] = []
    /// The one record of where every parcel is, keyed by package ID.
    private(set) var packageStates: [String: MultiVanPackageState] = [:]
    /// The run is frozen for the player to look and plan. Still a run: switches
    /// keep their run-time locks, and no clock moves until `resume()`.
    private(set) var isPaused = false
    private var remainder: TimeInterval = 0
    private var completedSteps = 0

    @ObservationIgnored private let packagesByOwner: [String: [MultiVanPackage]]
    @ObservationIgnored private let approachesByEdgeID: [String: (signal: MultiVanSignal, approach: MultiVanSignal.Approach)]
    @ObservationIgnored private let iceEdgeIDs: Set<String>

    @ObservationIgnored private var pendingEvents: [MultiVanEvent] = []
    @ObservationIgnored private var deliveryCombo = 0

    func drainEvents() -> [MultiVanEvent] {
        let events = pendingEvents
        pendingEvents.removeAll(keepingCapacity: true)
        return events
    }

    var runTime: TimeInterval { Double(completedSteps) * tuning.stepDuration }

    /// Simulation steps completed this run. Events carry the step they happened on.
    var tick: Int { completedSteps }

    func cargoStatus(forVanID vanID: String) -> MultiVanCargoStatus {
        MultiVanCargoStatus.make(packages: packagesByOwner[vanID] ?? [], states: packageStates)
    }

    /// What each signal really lets in now. While planning, the schedule's first step.
    var signalStates: [MultiVanSignalState] {
        let tick = phase == .plan ? 0 : completedSteps
        return level.signals.map { signal in
            let occupants = Self.occupants(of: signal, in: vans)
            let open = signal.nominalGroup(atTick: tick).flatMap {
                signal.admits(group: $0, atTick: tick, occupiedBy: occupants) ? $0 : nil
            }
            return MultiVanSignalState(signalID: signal.id, openGroup: open, isOccupied: !occupants.isEmpty)
        }
    }

    /// The driving vans keeping a live switch locked, for explaining a refused tap.
    func vansLocking(switchNodeID nodeID: String) -> [String] {
        guard phase == .run, level.liveSwitchNodeIDs.contains(nodeID),
              let node = runtimeGraph.nodesByID[nodeID] else { return [] }
        return vans.filter { locks($0, node: node) }.map(\.id)
    }

    private func locks(_ van: MultiVanVanState, node: RuntimeRouteNode) -> Bool {
        guard van.status == .driving else { return false }
        // On ice the van is committed from the moment it drives onto the road.
        if let edge = van.edge, edge.toNodeID == node.id, iceEdgeIDs.contains(edge.id) { return true }
        let point = van.position
        return hypot(point.x - node.x, point.y - node.y) <= tuning.liveSwitchLockRadius
    }

    /// Derived from current physical positions, including immediately after phase changes.
    var lockedSwitchNodeIDs: Set<String> {
        guard phase == .run else { return [] }
        return Set(runtimeGraph.nodesByID.values.compactMap { node in
            guard (2...4).contains(node.outgoingEdgeIDs.count) else { return nil }
            if !level.liveSwitchNodeIDs.contains(node.id) { return node.id }
            return vans.contains { locks($0, node: node) } ? node.id : nil
        })
    }

    init(level: MultiVanLevel, tuning: MultiVanTuning = .default) throws {
        self.level = level
        self.tuning = tuning
        let graph = try RuntimeRouteGraph.make(from: level.graph) { $0.availabilityRule }
        try MultiVanLevelRules.check(level, graph: graph)
        runtimeGraph = graph
        packagesByOwner = Dictionary(grouping: level.packages, by: \.ownerVanID)
        var approaches: [String: (signal: MultiVanSignal, approach: MultiVanSignal.Approach)] = [:]
        for signal in level.signals {
            for approach in signal.approaches { approaches[approach.edgeID] = (signal, approach) }
        }
        approachesByEdgeID = approaches
        iceEdgeIDs = Set(level.roadZones.filter { $0.kind == .ice }.flatMap(\.edgeIDs))
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
        var vans = self.vans
        var cargo = packageStates
        for index in vans.indices where level.vans[index].departDelay <= 0 {
            if let outcome = depart(&vans[index], from: level.vans[index].startNodeID, cargo: &cargo, tick: 0),
               failure == nil {
                failure = (outcome, vans[index].position)
            }
        }
        self.vans = vans
        packageStates = cargo
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

    /// Freezes the run where it stands. Nothing moves and no delay or signal
    /// clock counts until `resume()`; switches keep their run-time locks.
    func pause() {
        guard phase == .run, !isPaused else { return }
        isPaused = true
        pendingEvents.append(.paused(tick: completedSteps))
    }

    func resume() {
        guard phase == .run, isPaused else { return }
        isPaused = false
        pendingEvents.append(.resumed(tick: completedSteps))
    }

    private func resetRun() {
        resetVans()
        remainder = 0
        completedSteps = 0
        phase = .plan
        updatePreviewRoutes()
    }

    func advance(by realTime: TimeInterval) {
        guard phase == .run, !isPaused, realTime.isFinite, realTime > 0,
              tuning.stepDuration.isFinite, tuning.stepDuration > 0,
              tuning.vanSpeed.isFinite, tuning.vanSpeed >= 0,
              (remainder + realTime).isFinite else { return }

        // Step on local copies and publish once per call: observed-property
        // access on every step dominated simulation cost.
        var vans = self.vans
        // Parcels step with the vans: every pickup in this call reads and writes
        // this copy, never the table published by an earlier call.
        var cargo = packageStates
        var completedSteps = self.completedSteps
        // Preserve all elapsed time; frame-delta clamping belongs to the UI.
        var remainder = self.remainder + realTime
        defer {
            if completedSteps != self.completedSteps {
                // Previews only change when a van reaches a new road, leaves the
                // board or collects a parcel: a full lap can end on the same road.
                let routeChanged = cargo != packageStates || !zip(self.vans, vans).allSatisfy {
                    $0.currentEdgeID == $1.currentEdgeID && $0.status == $1.status
                }
                self.vans = vans
                if cargo != packageStates { packageStates = cargo }
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
            // Every signal decides from who was inside as the step began, so no
            // van is let in ahead of another because it comes first in the list.
            let admitted = admittedGroups(vans: vans, tick: completedSteps)
            for index in vans.indices {
                var arrivalFailure: Outcome?
                if vans[index].status == .waiting,
                   runTime >= level.vans[index].departDelay {
                    arrivalFailure = depart(
                        &vans[index], from: level.vans[index].startNodeID, cargo: &cargo, tick: completedSteps
                    )
                }
                // Arrivals land at the end of the step they happen in.
                if let outcome = move(
                    &vans[index], by: tuning.vanSpeed * tuning.stepDuration,
                    cargo: &cargo, tick: completedSteps + 1, admitted: admitted
                ) {
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
            updatePassages(&vans)
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
        case let .failMissingPackage(vanID, packageID, _):
            pendingEvents.append(.missingPackage(vanID: vanID, packageID: packageID))
        case .failStuck:
            break
        }
        self.outcome = outcome
        lastFailPoint = failPoint
        isPaused = false
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
        // Every reset puts every parcel back: nothing carries between attempts.
        packageStates = Dictionary(uniqueKeysWithValues: level.packages.map { ($0.id, .atPickup) })
        isPaused = false
    }

    private static func occupants(of signal: MultiVanSignal, in vans: [MultiVanVanState]) -> Set<Int> {
        Set(vans.compactMap { $0.passage?.signalID == signal.id ? $0.passage?.group : nil })
    }

    /// Per signal, the groups that may cross their stop line this step.
    private func admittedGroups(vans: [MultiVanVanState], tick: Int) -> [String: Set<Int>] {
        guard !level.signals.isEmpty else { return [:] }
        var admitted: [String: Set<Int>] = [:]
        for signal in level.signals {
            let occupants = Self.occupants(of: signal, in: vans)
            admitted[signal.id] = Set(signal.approaches.map(\.group).filter {
                signal.admits(group: $0, atTick: tick, occupiedBy: occupants)
            })
        }
        return admitted
    }

    /// A van occupies a signal from its stop line until it has been inside the
    /// marked area and left it; one that stops driving frees it at once.
    private func updatePassages(_ vans: inout [MultiVanVanState]) {
        guard !level.signals.isEmpty else { return }
        for index in vans.indices {
            guard let passage = vans[index].passage else { continue }
            guard vans[index].status == .driving,
                  let area = level.signals.first(where: { $0.id == passage.signalID })?.area else {
                vans[index].passage = nil
                continue
            }
            let point = vans[index].position
            if hypot(point.x - area.x, point.y - area.y) <= area.radius {
                vans[index].passage?.hasEntered = true
            } else if passage.hasEntered {
                vans[index].passage = nil
            }
        }
    }

    /// Arriving at `nodeID`: collect, then deliver at a house or take the selected exit.
    private func depart(
        _ van: inout MultiVanVanState, from nodeID: String,
        cargo: inout [String: MultiVanPackageState], tick: Int
    ) -> Outcome? {
        let owned = packagesByOwner[van.id] ?? []
        // Collecting is instant and happens once: only the owner, only on arrival.
        for package in owned where package.nodeID == nodeID && cargo[package.id] == .atPickup {
            cargo[package.id] = .carried
            pendingEvents.append(.pickedUp(vanID: van.id, packageID: package.id, tick: tick))
        }
        if let house = level.houses.first(where: { $0.nodeID == nodeID }) {
            // The wrong house comes first: it is wrong whatever the van carries.
            if house.color != van.color {
                van.status = .parked
                return .failWrongHouse(vanID: van.id, houseNodeID: nodeID)
            }
            if let missing = owned.first(where: { cargo[$0.id] == .atPickup }) {
                // Not parked, so no board shows the house as delivered.
                van.status = .missingCargo
                return .failMissingPackage(vanID: van.id, packageID: missing.id, pickupNodeID: missing.nodeID)
            }
            for package in owned { cargo[package.id] = .delivered }
            van.status = .parked
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

    private func move(
        _ van: inout MultiVanVanState, by distance: Double,
        cargo: inout [String: MultiVanPackageState], tick: Int, admitted: [String: Set<Int>]
    ) -> Outcome? {
        var distance = distance
        var edgesWithoutProgress = Set<String>()
        while van.status == .driving, let edge = van.edge {
            let length = edge.roadPath.totalLength
            guard length.isFinite, length >= 0 else {
                van.status = .stuck
                return nil
            }
            // A stop line ahead on this road, not already passed on green.
            if let (signal, approach) = approachesByEdgeID[edge.id],
               van.passage?.signalID != signal.id,
               van.distanceAlongEdge <= approach.stopDistance,
               van.distanceAlongEdge + distance > approach.stopDistance {
                if admitted[signal.id]?.contains(approach.group) == true {
                    if van.heldAtSignalID != nil {
                        pendingEvents.append(.released(vanID: van.id, signalID: signal.id, tick: tick))
                    }
                    van.heldAtSignalID = nil
                    van.passage = .init(signalID: signal.id, group: approach.group)
                } else {
                    // Drive up to the line and no further. Time spent held buys
                    // no distance: on green the van pulls away from the line.
                    if van.heldAtSignalID == nil {
                        pendingEvents.append(.held(vanID: van.id, signalID: signal.id, tick: tick))
                    }
                    van.distanceAlongEdge = approach.stopDistance
                    van.heldAtSignalID = signal.id
                    return nil
                }
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
            if let failure = depart(&van, from: edge.toNodeID, cargo: &cargo, tick: tick) { return failure }
            distance = leftover
        }
        return nil
    }

    /// Every accepted switch tap since the last switch reset, so flipping a
    /// switch back still counts. A retry keeps the tally: attempts cost too.
    private(set) var changeCount = 0

    /// The next selection in the authored cycle, shared by the press preview and tap.
    static func nextExit(in node: RuntimeRouteNode) -> String? {
        guard (2...4).contains(node.outgoingEdgeIDs.count) else { return nil }
        let currentIndex = node.activeOutgoingEdgeID.flatMap {
            node.outgoingEdgeIDs.firstIndex(of: $0)
        } ?? 0
        return node.outgoingEdgeIDs[(currentIndex + 1) % node.outgoingEdgeIDs.count]
    }

    @discardableResult
    func tapSwitch(nodeID: String) -> MultiVanTapResult {
        // Non-switch nodes are not feedback interactions.
        guard let node = runtimeGraph.nodesByID[nodeID],
              let nextExit = Self.nextExit(in: node) else {
            return .notASwitch
        }
        var result = MultiVanTapResult.accepted
        defer {
            pendingEvents.append(result == .accepted ? .switchTapped : .tapRejected(nodeID: nodeID))
        }
        // A paused run is still a run: pausing never unlocks a switch.
        if phase == .run {
            guard level.liveSwitchNodeIDs.contains(nodeID) else { result = .rejectedFrozen; return result }
            guard !lockedSwitchNodeIDs.contains(nodeID) else { result = .rejectedLocked; return result }
        } else if phase != .plan {
            result = .rejectedFrozen
            return result
        }
        runtimeGraph.nodesByID[nodeID]?.activeOutgoingEdgeID = nextExit
        changeCount += 1
        updatePreviewRoutes()
        return .accepted
    }

    func resetSwitches() {
        changeCount = 0
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
            let owned = packagesByOwner[van.id] ?? []
            switch state.status {
            case .driving:
                guard let edge = state.edge else { return .init(edgeIDs: [], ending: .offRoad) }
                // A running trace starts from what the van really holds, and
                // follows the road it is committed to before any later choice.
                let collected = Set(owned.filter { packageStates[$0.id] ?? .atPickup != .atPickup }.map(\.id))
                return MultiVanRoutePreview.trace(
                    from: edge.toNodeID, color: van.color, after: [edge.id],
                    graph: runtimeGraph, houses: level.houses,
                    packages: owned, collected: collected, signals: level.signals,
                    edgeLimit: tuning.previewEdgeLimit
                )
            case .waiting:
                // A planned trace imagines an empty van; it never touches a real parcel.
                return MultiVanRoutePreview.trace(
                    from: van.startNodeID, color: van.color,
                    graph: runtimeGraph, houses: level.houses,
                    packages: owned, signals: level.signals,
                    edgeLimit: tuning.previewEdgeLimit
                )
            case .parked, .crashed, .stuck, .missingCargo:
                return MultiVanPreviewRoute(edgeIDs: [], ending: .offRoad)
            }
        }
    }
}
