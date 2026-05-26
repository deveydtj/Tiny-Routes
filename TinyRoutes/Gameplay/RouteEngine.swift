import Foundation

/// Errors produced when building a runtime graph from level data.
enum RouteEngineError: Error, LocalizedError {
    case missingPackageNode(id: String)
    case missingDestinationNode(id: String)
    case missingStartNode(id: String)
    case edgeReferencesUnknownNode(edgeID: String, nodeID: String)
    case switchHasTooManyOutgoingEdges(nodeID: String, outgoingEdgeCount: Int)

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

/// Drives dot movement and evaluates win/loss conditions for a running level.
final class RouteEngine {
    private let dotSpeed: Double
    private let nodeSwitchController = NodeSwitchController()
    private var loadedLevelData: LevelData?
    private(set) var packageNodeID: String?
    private(set) var destinationNodeID: String?
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

    init(dotSpeed: Double = 1) {
        self.dotSpeed = max(0, dotSpeed)
    }

    /// Converts a `LevelData` into a `RuntimeRouteGraph` and stores it in `runtimeGraph`.
    ///
    /// Switch nodes (those with more than one outgoing edge) are initialized with their first
    /// outgoing edge as the active direction. Leaf nodes have no active edge.
    ///
    /// - Parameter levelData: The decoded level to build the graph from.
    /// - Throws: `RouteEngineError` if the graph data is invalid.
    func buildGraph(from levelData: LevelData) throws {
        runtimeGraph = nil
        deliveryDot = nil
        packageNodeID = nil
        destinationNodeID = nil
        remainingTime = nil
        tapCount = 0
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
                )
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
            node.activeOutgoingEdgeID = validOutgoingEdgeIDs.first
            runtimeGraph.nodesByID[nodeID] = node
        }

        var deliveryDot = DeliveryDot(currentNodeID: levelData.startNodeID)
        packageNodeID = levelData.packageNodeID
        destinationNodeID = levelData.destinationNodeID
        remainingTime = max(TimeInterval(levelData.timeLimitSeconds), 0)
        collectPackageIfNeeded(dot: &deliveryDot)
        evaluateDestinationArrivalIfNeeded(dot: &deliveryDot)

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
        guard let runtimeGraph, var deliveryDot else {
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
        let didStart = beginMovementFromCurrentNode(in: runtimeGraph, dot: &deliveryDot)
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
              let runtimeGraph,
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
                    snapDotToNode(transition.nodeID, dot: &deliveryDot)
                    if levelOutcome != nil {
                        break
                    }
                    guard beginMovementFromCurrentNode(in: runtimeGraph, dot: &deliveryDot) else {
                        didHaltAtDeadEnd = isDeadEnd(nodeID: deliveryDot.currentNodeID, in: runtimeGraph)
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
                snapDotToNode(edge.toNodeID, dot: &deliveryDot)
                if levelOutcome != nil {
                    break
                }
                guard beginMovementFromCurrentNode(in: runtimeGraph, dot: &deliveryDot) else {
                    didHaltAtDeadEnd = isDeadEnd(nodeID: deliveryDot.currentNodeID, in: runtimeGraph)
                    if didHaltAtDeadEnd {
                        levelOutcome = .failed(reason: .deadEnd)
                    }
                    break
                }
                continue
            }

            let clampedProgress = max(0, min(deliveryDot.progressAlongEdge, 1))
            let transition = smoothTransition(from: edge, in: runtimeGraph)
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
                collectPackageIfNeeded(dot: &deliveryDot)
                evaluateDestinationArrivalIfNeeded(dot: &deliveryDot)
                if levelOutcome != nil {
                    break
                }
            } else {
                remainingDistance -= distanceToEdgeTarget
                snapDotToNode(edge.toNodeID, dot: &deliveryDot)
                if levelOutcome != nil {
                    break
                }
                guard beginMovementFromCurrentNode(in: runtimeGraph, dot: &deliveryDot) else {
                    didHaltAtDeadEnd = isDeadEnd(nodeID: deliveryDot.currentNodeID, in: runtimeGraph)
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

        self.deliveryDot = deliveryDot
    }

    /// Rotates the active outgoing edge for a tapped switch node.
    /// For nodes with zero or one valid outgoing edge, this may normalize
    /// `activeOutgoingEdgeID` without rotating.
    ///
    /// - Parameter nodeID: The tapped node id.
    /// - Returns: `true` when a switch node rotated; `false` otherwise, including normalization-only updates.
    @discardableResult
    func rotateSwitchNode(nodeID: String) -> Bool {
        guard var runtimeGraph else {
            return false
        }
        if deliveryDot?.transition?.nodeID == nodeID {
            return false
        }
        if let currentEdgeID = deliveryDot?.currentEdgeID,
           runtimeGraph.edgesByID[currentEdgeID]?.fromNodeID == nodeID {
            return false
        }
        let didRotate = nodeSwitchController.rotateSwitch(nodeID: nodeID, in: &runtimeGraph)
        self.runtimeGraph = runtimeGraph
        if didRotate {
            tapCount += 1
        }
        return didRotate
    }

    @discardableResult
    private func beginMovementFromCurrentNode(in runtimeGraph: RuntimeRouteGraph, dot: inout DeliveryDot) -> Bool {
        guard dot.currentEdgeID == nil,
              let currentNode = runtimeGraph.nodesByID[dot.currentNodeID],
              let edgeID = currentNode.activeOutgoingEdgeID,
              let edge = runtimeGraph.edgesByID[edgeID],
              edge.fromNodeID == dot.currentNodeID else {
            return false
        }

        dot.currentEdgeID = edgeID
        dot.progressAlongEdge = 0
        dot.transition = nil
        return true
    }

    private func snapDotToNode(_ nodeID: String, dot: inout DeliveryDot) {
        dot.currentNodeID = nodeID
        dot.currentEdgeID = nil
        dot.progressAlongEdge = 0
        dot.transition = nil
        collectPackageIfNeeded(dot: &dot)
        evaluateDestinationArrivalIfNeeded(dot: &dot)
    }

    private func collectPackageIfNeeded(dot: inout DeliveryDot) {
        guard let packageNodeID,
              !dot.hasCollectedPackage,
              dot.currentNodeID == packageNodeID else {
            return
        }
        dot.hasCollectedPackage = true
    }

    private func evaluateDestinationArrivalIfNeeded(dot: inout DeliveryDot) {
        guard levelOutcome == nil,
              let destinationNodeID,
              dot.currentNodeID == destinationNodeID else {
            return
        }

        levelOutcome = dot.hasCollectedPackage
            ? .completed
            : .failed(reason: .reachedDestinationWithoutPackage)
    }

    private func isDeadEnd(nodeID: String, in runtimeGraph: RuntimeRouteGraph) -> Bool {
        guard let node = runtimeGraph.nodesByID[nodeID] else {
            return false
        }

        return node.outgoingEdgeIDs.isEmpty || node.activeOutgoingEdgeID == nil
    }

    private struct SmoothTransition {
        let exitDistanceFromCurrentEdge: Double
        let dotTransition: DeliveryDotTransition
    }

    private func smoothTransition(from edge: RuntimeRouteEdge, in runtimeGraph: RuntimeRouteGraph) -> SmoothTransition? {
        guard let node = runtimeGraph.nodesByID[edge.toNodeID] else {
            return nil
        }

        let validOutgoingEdgeIDs = runtimeGraph.validOutgoingEdgeIDs(for: node)
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
