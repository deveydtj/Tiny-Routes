import Foundation

/// Errors produced when building a runtime graph from level data.
enum RouteEngineError: Error, LocalizedError {
    case missingPackageNode(id: String)
    case missingDestinationNode(id: String)
    case missingStartNode(id: String)
    case edgeReferencesUnknownNode(edgeID: String, nodeID: String)

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
    private var packageNodeID: String?
    private var destinationNodeID: String?
    private var timeRemaining: TimeInterval?

    /// Indicates whether the most recent `updateDot(deltaTime:)` call halted at a dead end.
    private(set) var didHaltAtDeadEnd = false
    /// Terminal gameplay state reached by the current level run.
    private(set) var levelOutcome: LevelOutcome?

    /// The runtime graph built from the loaded level, available after `buildGraph(from:)` succeeds.
    private(set) var runtimeGraph: RuntimeRouteGraph?
    /// Runtime state for the delivery dot, available after `buildGraph(from:)` succeeds.
    private(set) var deliveryDot: DeliveryDot?

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
        timeRemaining = nil
        levelOutcome = nil
        didHaltAtDeadEnd = false

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
                activeOutgoingEdgeID: node.outgoingEdgeIDs.first
            )
        }

        var edgesByID: [String: RuntimeRouteEdge] = [:]
        for edge in graph.edges {
            edgesByID[edge.id] = RuntimeRouteEdge(
                id: edge.id,
                fromNodeID: edge.fromNodeID,
                toNodeID: edge.toNodeID
            )
        }

        let runtimeGraph = RuntimeRouteGraph(nodesByID: nodesByID, edgesByID: edgesByID)
        var deliveryDot = DeliveryDot(currentNodeID: levelData.startNodeID)
        packageNodeID = levelData.packageNodeID
        destinationNodeID = levelData.destinationNodeID
        timeRemaining = max(TimeInterval(levelData.timeLimitSeconds), 0)
        collectPackageIfNeeded(dot: &deliveryDot)
        evaluateDestinationArrivalIfNeeded(dot: &deliveryDot)

        self.runtimeGraph = runtimeGraph
        self.deliveryDot = deliveryDot
    }

    /// Starts the delivery dot moving along the active edge for its current node, if one exists.
    @discardableResult
    func startDotMovement() -> Bool {
        guard let runtimeGraph, var deliveryDot else {
            return false
        }
        if levelOutcome == nil,
           let timeRemaining,
           timeRemaining <= 0 {
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
        guard deltaTime > 0,
              let runtimeGraph,
              var deliveryDot else {
            return
        }
        guard levelOutcome == nil else {
            self.deliveryDot = deliveryDot
            return
        }

        if let timeRemaining {
            let updatedTimeRemaining = max(0, timeRemaining - deltaTime)
            self.timeRemaining = updatedTimeRemaining
            if updatedTimeRemaining <= 0 {
                levelOutcome = .failed(reason: .timeExpired)
                self.deliveryDot = deliveryDot
                return
            }
        }

        guard deliveryDot.currentEdgeID != nil else {
            self.deliveryDot = deliveryDot
            return
        }

        var remainingDistance = dotSpeed * deltaTime
        var safetyStepCount = 0
        let maxSafetyStepCount = max(runtimeGraph.edgesByID.count, 1) * 4

        while remainingDistance > 0, safetyStepCount < maxSafetyStepCount {
            safetyStepCount += 1

            guard let currentEdgeID = deliveryDot.currentEdgeID,
                  let edge = runtimeGraph.edgesByID[currentEdgeID],
                  let fromNode = runtimeGraph.nodesByID[edge.fromNodeID],
                  let toNode = runtimeGraph.nodesByID[edge.toNodeID] else {
                break
            }

            let edgeLength = hypot(toNode.x - fromNode.x, toNode.y - fromNode.y)
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
            let distanceToEdgeEnd = (1 - clampedProgress) * edgeLength

            if remainingDistance < distanceToEdgeEnd {
                deliveryDot.progressAlongEdge = clampedProgress + (remainingDistance / edgeLength)
                remainingDistance = 0
            } else {
                remainingDistance -= distanceToEdgeEnd
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
            assertionFailure("RouteEngine.updateDot exceeded safety step limit with remaining distance \(remainingDistance).")
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
        let didRotate = nodeSwitchController.rotateSwitch(nodeID: nodeID, in: &runtimeGraph)
        self.runtimeGraph = runtimeGraph
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
        return true
    }

    private func snapDotToNode(_ nodeID: String, dot: inout DeliveryDot) {
        dot.currentNodeID = nodeID
        dot.currentEdgeID = nil
        dot.progressAlongEdge = 0
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
}
