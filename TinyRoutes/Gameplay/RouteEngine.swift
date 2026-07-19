import Foundation

/// Errors produced when building a runtime graph from level data.
enum RouteEngineError: Error, LocalizedError {
    case missingPackageNode(id: String)
    case missingDestinationNode(id: String)
    case missingStartNode(id: String)
    case edgeReferencesUnknownNode(edgeID: String, nodeID: String)
    case switchHasTooManyOutgoingEdges(nodeID: String, outgoingEdgeCount: Int)
    case conditionalRoadsCreateDeadEnd(nodeID: String, hasCollectedPackage: Bool)

    var errorDescription: String? {
        switch self {
        case let .missingPackageNode(id):
            return "Package node '\(id)' does not exist in the level graph."
        case let .missingDestinationNode(id):
            return "Destination node '\(id)' does not exist in the level graph."
        case let .missingStartNode(id):
            return "Start node '\(id)' does not exist in the level graph."
        case let .edgeReferencesUnknownNode(edgeID, nodeID):
            return "Edge '\(edgeID)' references unknown node '\(nodeID)'."
        case let .switchHasTooManyOutgoingEdges(nodeID, outgoingEdgeCount):
            return "Node '\(nodeID)' has \(outgoingEdgeCount) valid outgoing edges; at most \(SwitchNodeKind.maximumSupportedOutgoingEdgeCount) are supported."
        case let .conditionalRoadsCreateDeadEnd(nodeID, hasCollectedPackage):
            let phase = hasCollectedPackage ? "after" : "before"
            return "Node '\(nodeID)' has authored outgoing roads but none are available \(phase) package collection."
        }
    }
}

enum LevelOutcome: Equatable {
    case completed
    case failed(reason: LevelFailureReason)
}

enum LevelFailureReason: Equatable {
    case deadEnd
    case timeExpired
    case reachedDestinationWithoutPackage

    var message: String {
        switch self {
        case .deadEnd:
            return "Dead end reached."
        case .timeExpired:
            return "Time expired."
        case .reachedDestinationWithoutPackage:
            return "Reached destination without package."
        }
    }
}

enum RouteObjectiveEventKind: String, Equatable {
    case revealed = "objective_revealed"
    case activated = "objective_activated"
    case completed = "objective_completed"
    case futureObjectiveVisited = "future_objective_visited"
}

/// A normalized objective-state transition emitted at a node-arrival boundary.
struct RouteObjectiveEvent: Equatable {
    let kind: RouteObjectiveEventKind
    let objectiveID: String
    let sequenceIndex: Int
    let nodeID: String
}

/// Drives dot movement and evaluates win/loss conditions for a running level.
final class RouteEngine {
    private let dotSpeed: Double
    private let nodeSwitchController = NodeSwitchController()
    private let switchEligibilityService = SwitchEligibilityService()
    private var loadedLevelData: LevelData?
    private var activeRules: LevelRules = .legacyDefaults
    private var lastAcceptedSwitchTapTime: TimeInterval?
    private(set) var packageNodeID: String?
    private(set) var destinationNodeID: String?
    private(set) var objectives: [RouteObjective] = []
    private(set) var activeObjectiveIndex: Int?
    private(set) var completedObjectiveIDs: Set<String> = []
    private(set) var revealedObjectiveIDs: Set<String> = []
    private(set) var objectiveEvents: [RouteObjectiveEvent] = []
    private var remainingTime: TimeInterval?
    private(set) var tapCount: Int = 0

    /// Indicates whether the most recent `updateDot(deltaTime:)` call halted at a dead end.
    private(set) var didHaltAtDeadEnd = false
    /// Indicates whether the most recent `updateDot(deltaTime:)` call hit its internal traversal guard.
    private(set) var didHitUpdateSafetyStepLimit = false
    /// Terminal gameplay state reached by the current level run.
    private(set) var levelOutcome: LevelOutcome?

    /// The runtime graph built from the loaded level, available after `buildGraph(from:)` succeeds.
    private(set) var runtimeGraph: RuntimeRouteGraph?
    /// Runtime state for the delivery dot, available after `buildGraph(from:)` succeeds.
    private(set) var deliveryDot: DeliveryDot?
    /// Countdown timer state for the current run, or `nil` before a level is loaded.
    var timeRemaining: TimeInterval? { remainingTime }
    /// Configured time limit for the current run, or `nil` before a level is loaded.
    var timeLimit: TimeInterval? {
        loadedLevelData.map { max(TimeInterval($0.timeLimitSeconds), 0) }
    }
    /// Elapsed attempt time derived from the level time limit and remaining countdown.
    var elapsedTime: TimeInterval? {
        guard let timeLimit,
              let remainingTime else {
            return nil
        }

        return max(timeLimit - remainingTime, 0)
    }

    var switchEligibilitySnapshot: SwitchEligibilitySnapshot {
        guard activeRules.switchInteractionMode == .liveLookahead,
              let runtimeGraph,
              let deliveryDot else {
            return .noUpcomingSwitch
        }
        return switchEligibilityService.snapshot(
            graph: runtimeGraph,
            dot: deliveryDot,
            speed: dotSpeed,
            hasCollectedPackage: deliveryDot.hasCollectedPackage,
            rules: activeRules
        )
    }

    var eligibleSwitchNodeID: String? { switchEligibilitySnapshot.eligibleNodeID }
    var upcomingSwitchTravelTime: TimeInterval? { switchEligibilitySnapshot.travelTimeSeconds }
    var activeObjective: RouteObjective? {
        guard let activeObjectiveIndex,
              objectives.indices.contains(activeObjectiveIndex) else {
            return nil
        }
        return objectives[activeObjectiveIndex]
    }

    init(dotSpeed: Double = 1) {
        self.dotSpeed = max(0, dotSpeed)
    }

    /// Converts a `LevelData` into a `RuntimeRouteGraph` and stores it in `runtimeGraph`.
    ///
    /// Switch nodes are initialized with their first pre-package usable outgoing edge as the
    /// active direction. Leaf nodes have no active edge.
    ///
    /// - Parameter levelData: The decoded level to build the graph from.
    /// - Throws: `RouteEngineError` if the graph data is invalid.
    func buildGraph(from levelData: LevelData) throws {
        runtimeGraph = nil
        deliveryDot = nil
        packageNodeID = nil
        destinationNodeID = nil
        objectives = []
        activeObjectiveIndex = nil
        completedObjectiveIDs = []
        revealedObjectiveIDs = []
        objectiveEvents = []
        remainingTime = nil
        tapCount = 0
        activeRules = levelData.effectiveRules
        lastAcceptedSwitchTapTime = nil
        levelOutcome = nil
        didHaltAtDeadEnd = false
        didHitUpdateSafetyStepLimit = false

        let graph = levelData.graph
        let nodeIDs = Set(graph.nodes.map(\.id))

        for edge in graph.edges {
            guard nodeIDs.contains(edge.fromNodeID) else {
                throw RouteEngineError.edgeReferencesUnknownNode(edgeID: edge.id, nodeID: edge.fromNodeID)
            }
            guard nodeIDs.contains(edge.toNodeID) else {
                throw RouteEngineError.edgeReferencesUnknownNode(edgeID: edge.id, nodeID: edge.toNodeID)
            }
        }

        guard nodeIDs.contains(levelData.packageNodeID) else {
            throw RouteEngineError.missingPackageNode(id: levelData.packageNodeID)
        }
        guard nodeIDs.contains(levelData.destinationNodeID) else {
            throw RouteEngineError.missingDestinationNode(id: levelData.destinationNodeID)
        }
        guard nodeIDs.contains(levelData.startNodeID) else {
            throw RouteEngineError.missingStartNode(id: levelData.startNodeID)
        }

        var nodesByID: [String: RuntimeRouteNode] = [:]
        for node in graph.nodes {
            nodesByID[node.id] = RuntimeRouteNode(
                id: node.id,
                x: node.x,
                y: node.y,
                outgoingEdgeIDs: node.outgoingEdgeIDs,
                activeOutgoingEdgeID: nil
            )
        }

        var edgesByID: [String: RuntimeRouteEdge] = [:]
        for edge in graph.edges {
            guard let fromNode = nodesByID[edge.fromNodeID] else {
                throw RouteEngineError.edgeReferencesUnknownNode(edgeID: edge.id, nodeID: edge.fromNodeID)
            }
            guard let toNode = nodesByID[edge.toNodeID] else {
                throw RouteEngineError.edgeReferencesUnknownNode(edgeID: edge.id, nodeID: edge.toNodeID)
            }

            edgesByID[edge.id] = RuntimeRouteEdge(
                id: edge.id,
                fromNodeID: edge.fromNodeID,
                toNodeID: edge.toNodeID,
                roadPath: RoadPath.make(
                    from: RoadPoint(x: fromNode.x, y: fromNode.y),
                    to: RoadPoint(x: toNode.x, y: toNode.y),
                    shape: edge.roadShape
                ),
                availability: edge.availability
            )
        }

        var runtimeGraph = RuntimeRouteGraph(nodesByID: nodesByID, edgesByID: edgesByID)
        for nodeID in runtimeGraph.nodesByID.keys {
            guard var node = runtimeGraph.nodesByID[nodeID] else {
                continue
            }
            let validOutgoingEdgeIDs = runtimeGraph.validOutgoingEdgeIDs(for: node)
            if validOutgoingEdgeIDs.count > SwitchNodeKind.maximumSupportedOutgoingEdgeCount {
                throw RouteEngineError.switchHasTooManyOutgoingEdges(
                    nodeID: node.id,
                    outgoingEdgeCount: validOutgoingEdgeIDs.count
                )
            }
            for hasCollectedPackage in [false, true]
            where !validOutgoingEdgeIDs.isEmpty
                && runtimeGraph.usableOutgoingEdgeIDs(
                    for: node,
                    hasCollectedPackage: hasCollectedPackage
                ).isEmpty {
                throw RouteEngineError.conditionalRoadsCreateDeadEnd(
                    nodeID: node.id,
                    hasCollectedPackage: hasCollectedPackage
                )
            }
            node.activeOutgoingEdgeID = runtimeGraph.usableOutgoingEdgeIDs(
                for: node,
                hasCollectedPackage: false
            ).first
            runtimeGraph.nodesByID[nodeID] = node
        }

        initializeObjectiveProgression(from: levelData)
        var deliveryDot = DeliveryDot(currentNodeID: levelData.startNodeID)
        packageNodeID = levelData.packageNodeID
        destinationNodeID = levelData.destinationNodeID
        remainingTime = max(TimeInterval(levelData.timeLimitSeconds), 0)
        processObjectiveArrival(
            at: levelData.startNodeID,
            dot: &deliveryDot,
            runtimeGraph: &runtimeGraph,
            preserveLegacyBehavior: (levelData.schemaVersion ?? 1) < 3
        )

        self.runtimeGraph = runtimeGraph
        self.deliveryDot = deliveryDot
        loadedLevelData = levelData
    }

    /// Rebuilds the last loaded level so the current run restarts from a clean state.
    ///
    /// - Returns: `true` when a previously loaded level was restored; `false` when no level is loaded.
    @discardableResult
    func restartLevel() -> Bool {
        guard let loadedLevelData else {
            return false
        }

        do {
            try buildGraph(from: loadedLevelData)
            _ = startDotMovement()
            return true
        } catch {
            assertionFailure("RouteEngine failed to restart previously loaded level: \(error)")
            return false
        }
    }

    /// Starts the delivery dot moving along the active edge for its current node, if one exists.
    @discardableResult
    func startDotMovement() -> Bool {
        guard var runtimeGraph, var deliveryDot else {
            return false
        }
        if levelOutcome == nil,
           let remainingTime,
           remainingTime <= 0 {
            levelOutcome = .failed(reason: .timeExpired)
        }
        guard levelOutcome == nil else {
            self.deliveryDot = deliveryDot
            return false
        }
        let didStart = beginMovementFromCurrentNode(in: &runtimeGraph, dot: &deliveryDot)
        self.runtimeGraph = runtimeGraph
        self.deliveryDot = deliveryDot
        return didStart
    }

    /// Advances the delivery dot using frame-rate independent timing, continuing across connected
    /// nodes while movement distance remains by following each node's active outgoing edge.
    ///
    /// This method does not auto-start movement from an idle node; call `startDotMovement()` first.
    /// If traversal reaches a dead end, the dot snaps to that node and remaining movement distance
    /// is discarded for the current update.
    func updateDot(deltaTime: TimeInterval) {
        didHaltAtDeadEnd = false
        didHitUpdateSafetyStepLimit = false
        guard deltaTime > 0,
              var runtimeGraph,
              var deliveryDot else {
            return
        }
        guard levelOutcome == nil else {
            self.deliveryDot = deliveryDot
            return
        }

        let movementDeltaTime: TimeInterval
        var didConsumeRemainingTime = false
        if let remainingTime {
            let clampedTimeRemaining = max(remainingTime, 0)
            if clampedTimeRemaining <= 0 {
                levelOutcome = .failed(reason: .timeExpired)
                self.deliveryDot = deliveryDot
                return
            }

            movementDeltaTime = min(deltaTime, clampedTimeRemaining)
            let updatedTimeRemaining = clampedTimeRemaining - movementDeltaTime
            self.remainingTime = updatedTimeRemaining
            didConsumeRemainingTime = updatedTimeRemaining <= 0
        } else {
            movementDeltaTime = deltaTime
        }

        guard deliveryDot.currentEdgeID != nil || deliveryDot.transition != nil else {
            if didConsumeRemainingTime, levelOutcome == nil {
                levelOutcome = .failed(reason: .timeExpired)
            }
            self.deliveryDot = deliveryDot
            return
        }

        var remainingDistance = dotSpeed * movementDeltaTime
        var safetyStepCount = 0
        let maxSafetyStepCount = max(runtimeGraph.edgesByID.count, 1) * 4

        while remainingDistance > 0, safetyStepCount < maxSafetyStepCount {
            safetyStepCount += 1

            if var transition = deliveryDot.transition {
                let transitionLength = transition.roadPath.totalLength
                guard transitionLength > 0,
                      let toEdge = runtimeGraph.edgesByID[transition.toEdgeID],
                      toEdge.roadPath.totalLength > 0 else {
                    snapDotToNode(
                        transition.nodeID,
                        runtimeGraph: &runtimeGraph,
                        dot: &deliveryDot
                    )
                    if levelOutcome != nil {
                        break
                    }
                    guard beginMovementFromCurrentNode(in: &runtimeGraph, dot: &deliveryDot) else {
                        didHaltAtDeadEnd = isDeadEnd(
                            nodeID: deliveryDot.currentNodeID,
                            in: runtimeGraph,
                            hasCollectedPackage: deliveryDot.hasCollectedPackage
                        )
                        if didHaltAtDeadEnd {
                            levelOutcome = .failed(reason: .deadEnd)
                        }
                        break
                    }
                    continue
                }

                let clampedProgress = max(0, min(transition.progressAlongTransition, 1))
                let distanceToTransitionEnd = (1 - clampedProgress) * transitionLength
                if remainingDistance < distanceToTransitionEnd {
                    transition.progressAlongTransition = clampedProgress + (remainingDistance / transitionLength)
                    deliveryDot.transition = transition
                    remainingDistance = 0
                } else {
                    remainingDistance -= distanceToTransitionEnd
                    deliveryDot.currentNodeID = transition.nodeID
                    deliveryDot.currentEdgeID = transition.toEdgeID
                    deliveryDot.progressAlongEdge = max(
                        0,
                        min(transition.exitDistanceAlongToEdge / toEdge.roadPath.totalLength, 1)
                    )
                    deliveryDot.transition = nil
                }
                continue
            }

            guard let currentEdgeID = deliveryDot.currentEdgeID,
                  let edge = runtimeGraph.edgesByID[currentEdgeID] else {
                break
            }

            let edgeLength = edge.roadPath.totalLength
            guard edgeLength > 0 else {
                snapDotToNode(
                    edge.toNodeID,
                    runtimeGraph: &runtimeGraph,
                    dot: &deliveryDot
                )
                if levelOutcome != nil {
                    break
                }
                guard beginMovementFromCurrentNode(in: &runtimeGraph, dot: &deliveryDot) else {
                    didHaltAtDeadEnd = isDeadEnd(
                        nodeID: deliveryDot.currentNodeID,
                        in: runtimeGraph,
                        hasCollectedPackage: deliveryDot.hasCollectedPackage
                    )
                    if didHaltAtDeadEnd {
                        levelOutcome = .failed(reason: .deadEnd)
                    }
                    break
                }
                continue
            }

            let clampedProgress = max(0, min(deliveryDot.progressAlongEdge, 1))
            let transition = smoothTransition(
                from: edge,
                in: runtimeGraph,
                hasCollectedPackage: deliveryDot.hasCollectedPackage
            )
            let exitDistanceFromCurrentEdge = transition?.exitDistanceFromCurrentEdge ?? edgeLength
            let targetProgress = max(0, min(exitDistanceFromCurrentEdge / edgeLength, 1))
            let distanceToEdgeTarget = max(0, (targetProgress - clampedProgress) * edgeLength)

            if remainingDistance < distanceToEdgeTarget {
                deliveryDot.progressAlongEdge = clampedProgress + (remainingDistance / edgeLength)
                remainingDistance = 0
            } else if let transition {
                remainingDistance -= distanceToEdgeTarget
                deliveryDot.currentNodeID = edge.toNodeID
                deliveryDot.currentEdgeID = nil
                deliveryDot.progressAlongEdge = 0
                deliveryDot.transition = transition.dotTransition
                processObjectiveArrival(
                    at: deliveryDot.currentNodeID,
                    dot: &deliveryDot,
                    runtimeGraph: &runtimeGraph,
                    preserveLegacyBehavior: (loadedLevelData?.schemaVersion ?? 1) < 3
                )
                if levelOutcome != nil {
                    break
                }
            } else {
                remainingDistance -= distanceToEdgeTarget
                snapDotToNode(
                    edge.toNodeID,
                    runtimeGraph: &runtimeGraph,
                    dot: &deliveryDot
                )
                if levelOutcome != nil {
                    break
                }
                guard beginMovementFromCurrentNode(in: &runtimeGraph, dot: &deliveryDot) else {
                    didHaltAtDeadEnd = isDeadEnd(
                        nodeID: deliveryDot.currentNodeID,
                        in: runtimeGraph,
                        hasCollectedPackage: deliveryDot.hasCollectedPackage
                    )
                    if didHaltAtDeadEnd {
                        levelOutcome = .failed(reason: .deadEnd)
                    }
                    break
                }
            }
        }

        if safetyStepCount >= maxSafetyStepCount, remainingDistance > 0 {
            didHitUpdateSafetyStepLimit = true
            assertionFailure("RouteEngine.updateDot exceeded safety step limit with remaining distance \(remainingDistance).")
        }

        if didConsumeRemainingTime, levelOutcome == nil {
            levelOutcome = .failed(reason: .timeExpired)
        }

        self.runtimeGraph = runtimeGraph
        self.deliveryDot = deliveryDot
    }

    /// Rotates the active outgoing edge for a tapped switch node.
    /// For nodes with zero or one currently usable outgoing edge, this may normalize
    /// `activeOutgoingEdgeID` without rotating.
    ///
    /// - Parameter nodeID: The tapped node id.
    /// - Returns: A structured acceptance or rejection result.
    @discardableResult
    func rotateSwitchNode(nodeID: String) -> SwitchTapResult {
        guard var runtimeGraph else {
            return .rejectedNoLevel
        }
        guard levelOutcome == nil else {
            return .rejectedLevelFinished
        }
        if deliveryDot?.transition?.nodeID == nodeID {
            return .rejectedCommitted
        }
        if let currentEdgeID = deliveryDot?.currentEdgeID,
           runtimeGraph.edgesByID[currentEdgeID]?.fromNodeID == nodeID {
            return .rejectedCommitted
        }
        let hasCollectedPackage = deliveryDot?.hasCollectedPackage ?? false
        guard let node = runtimeGraph.nodesByID[nodeID],
              runtimeGraph.switchKind(
                  for: node,
                  hasCollectedPackage: hasCollectedPackage
              ).isSwitchable else {
            // Preserve the controller's normalization behavior for malformed or
            // partially valid nodes during the caller migration.
            _ = nodeSwitchController.rotateSwitch(
                nodeID: nodeID,
                in: &runtimeGraph,
                hasCollectedPackage: hasCollectedPackage
            )
            self.runtimeGraph = runtimeGraph
            return .rejectedNotSwitchable
        }
        if activeRules.switchInteractionMode == .liveLookahead {
            let eligibility = switchEligibilitySnapshot
            guard eligibility.eligibleNodeID == nodeID else {
                return .rejectedNotEligible(expectedNodeID: eligibility.eligibleNodeID)
            }
            if let lastAcceptedSwitchTapTime,
               let elapsedTime,
               elapsedTime - lastAcceptedSwitchTapTime < max(activeRules.switchTapCooldownSeconds, 0) {
                return .rejectedCooldown
            }
        }
        let didRotate = nodeSwitchController.rotateSwitch(
            nodeID: nodeID,
            in: &runtimeGraph,
            hasCollectedPackage: hasCollectedPackage
        )
        self.runtimeGraph = runtimeGraph
        guard didRotate,
              let activeEdgeID = runtimeGraph.nodesByID[nodeID]?.activeOutgoingEdgeID else {
            return .rejectedNotSwitchable
        }
        tapCount += 1
        if activeRules.switchInteractionMode == .liveLookahead {
            lastAcceptedSwitchTapTime = elapsedTime
        }
        return .accepted(nodeID: nodeID, activeEdgeID: activeEdgeID)
    }

    @discardableResult
    private func beginMovementFromCurrentNode(
        in runtimeGraph: inout RuntimeRouteGraph,
        dot: inout DeliveryDot
    ) -> Bool {
        guard dot.currentEdgeID == nil,
              var currentNode = runtimeGraph.nodesByID[dot.currentNodeID] else {
            return false
        }
        let usableEdgeIDs = runtimeGraph.usableOutgoingEdgeIDs(
            for: currentNode,
            hasCollectedPackage: dot.hasCollectedPackage
        )
        let edgeID = currentNode.activeOutgoingEdgeID.flatMap {
            usableEdgeIDs.contains($0) ? $0 : nil
        } ?? usableEdgeIDs.first
        guard let edgeID,
              let edge = runtimeGraph.edgesByID[edgeID],
              edge.fromNodeID == dot.currentNodeID else {
            return false
        }

        if currentNode.activeOutgoingEdgeID != edgeID {
            currentNode.activeOutgoingEdgeID = edgeID
            runtimeGraph.nodesByID[currentNode.id] = currentNode
        }

        dot.currentEdgeID = edgeID
        dot.progressAlongEdge = 0
        dot.transition = nil
        return true
    }

    private func snapDotToNode(
        _ nodeID: String,
        runtimeGraph: inout RuntimeRouteGraph,
        dot: inout DeliveryDot
    ) {
        dot.currentNodeID = nodeID
        dot.currentEdgeID = nil
        dot.progressAlongEdge = 0
        dot.transition = nil
        processObjectiveArrival(
            at: nodeID,
            dot: &dot,
            runtimeGraph: &runtimeGraph,
            preserveLegacyBehavior: (loadedLevelData?.schemaVersion ?? 1) < 3
        )
    }

    private func initializeObjectiveProgression(from levelData: LevelData) {
        objectives = levelData.effectiveObjectives.sorted {
            $0.sequenceIndex < $1.sequenceIndex
        }
        activeObjectiveIndex = objectives.isEmpty ? nil : 0
        for objective in objectives where objective.revealPolicy == "always" {
            revealObjectiveIfNeeded(objective)
        }
        if let activeObjective {
            revealObjectiveIfNeeded(activeObjective)
            recordObjectiveEvent(.activated, objective: activeObjective)
        }
    }

    private func processObjectiveArrival(
        at nodeID: String,
        dot: inout DeliveryDot,
        runtimeGraph: inout RuntimeRouteGraph,
        preserveLegacyBehavior: Bool
    ) {
        guard levelOutcome == nil,
              var objective = activeObjective,
              let currentIndex = activeObjectiveIndex else {
            return
        }

        guard nodeID == objective.nodeID else {
            let futureObjective = objectives
                .dropFirst(currentIndex + 1)
                .first { $0.nodeID == nodeID }
            guard let futureObjective else { return }
            if preserveLegacyBehavior, futureObjective.kind == .destination {
                levelOutcome = .failed(reason: .reachedDestinationWithoutPackage)
            } else {
                recordObjectiveEvent(.futureObjectiveVisited, objective: futureObjective)
            }
            return
        }

        var index = currentIndex
        while nodeID == objective.nodeID {
            completedObjectiveIDs.insert(objective.id)
            if objective.kind == .pickup {
                dot.hasCollectedPackage = true
            }
            recordObjectiveEvent(.completed, objective: objective)
            runtimeGraph.normalizeActiveOutgoingEdges(
                hasCollectedPackage: dot.hasCollectedPackage
            )

            let nextIndex = index + 1
            guard objectives.indices.contains(nextIndex) else {
                activeObjectiveIndex = nil
                if objective.kind == .destination {
                    levelOutcome = .completed
                }
                return
            }

            activeObjectiveIndex = nextIndex
            index = nextIndex
            objective = objectives[nextIndex]
            revealObjectiveIfNeeded(objective)
            recordObjectiveEvent(.activated, objective: objective)
            if !preserveLegacyBehavior {
                return
            }
        }
    }

    private func revealObjectiveIfNeeded(_ objective: RouteObjective) {
        guard revealedObjectiveIDs.insert(objective.id).inserted else { return }
        recordObjectiveEvent(.revealed, objective: objective)
    }

    private func recordObjectiveEvent(
        _ kind: RouteObjectiveEventKind,
        objective: RouteObjective
    ) {
        objectiveEvents.append(RouteObjectiveEvent(
            kind: kind,
            objectiveID: objective.id,
            sequenceIndex: objective.sequenceIndex,
            nodeID: objective.nodeID
        ))
    }

    private func isDeadEnd(
        nodeID: String,
        in runtimeGraph: RuntimeRouteGraph,
        hasCollectedPackage: Bool
    ) -> Bool {
        guard let node = runtimeGraph.nodesByID[nodeID] else {
            return false
        }

        return runtimeGraph.usableOutgoingEdgeIDs(
            for: node,
            hasCollectedPackage: hasCollectedPackage
        ).isEmpty
    }

    private struct SmoothTransition {
        let exitDistanceFromCurrentEdge: Double
        let dotTransition: DeliveryDotTransition
    }

    private func smoothTransition(
        from edge: RuntimeRouteEdge,
        in runtimeGraph: RuntimeRouteGraph,
        hasCollectedPackage: Bool
    ) -> SmoothTransition? {
        guard let node = runtimeGraph.nodesByID[edge.toNodeID] else {
            return nil
        }

        // Package collection can change the usable road at this node, so commit
        // to the node before choosing its outgoing road.
        if node.id == activeObjective?.nodeID,
           activeObjective?.kind == .pickup,
           !hasCollectedPackage {
            let beforePackageEdgeIDs = runtimeGraph.usableOutgoingEdgeIDs(
                for: node,
                hasCollectedPackage: false
            )
            let afterPackageEdgeIDs = runtimeGraph.usableOutgoingEdgeIDs(
                for: node,
                hasCollectedPackage: true
            )
            if beforePackageEdgeIDs != afterPackageEdgeIDs {
                return nil
            }
        }

        let validOutgoingEdgeIDs = runtimeGraph.usableOutgoingEdgeIDs(
            for: node,
            hasCollectedPackage: hasCollectedPackage
        )
        guard validOutgoingEdgeIDs.count == 1,
              let nextEdgeID = node.activeOutgoingEdgeID,
              validOutgoingEdgeIDs.contains(nextEdgeID),
              let nextEdge = runtimeGraph.edgesByID[nextEdgeID],
              nextEdge.fromNodeID == node.id else {
            return nil
        }

        let edgeLength = edge.roadPath.totalLength
        let nextEdgeLength = nextEdge.roadPath.totalLength
        guard edgeLength > 0, nextEdgeLength > 0 else {
            return nil
        }

        guard let connector = RoadPath.makePerpendicularConnector(
            at: RoadPoint(x: node.x, y: node.y),
            from: edge.roadPath,
            to: nextEdge.roadPath
        ) else {
            return nil
        }

        return SmoothTransition(
            exitDistanceFromCurrentEdge: connector.entryDistanceAlongIncomingPath,
            dotTransition: DeliveryDotTransition(
                nodeID: node.id,
                toEdgeID: nextEdgeID,
                roadPath: connector.roadPath,
                exitDistanceAlongToEdge: connector.exitDistanceAlongOutgoingPath,
                progressAlongTransition: 0
            )
        )
    }
}
