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

/// Drives dot movement and evaluates win/loss conditions for a running level.
final class RouteEngine {
    private let dotSpeed: Double


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
        let deliveryDot = DeliveryDot(currentNodeID: levelData.startNodeID)

        self.runtimeGraph = runtimeGraph
        self.deliveryDot = deliveryDot
    }

    /// Starts the delivery dot moving along the active edge for its current node, if one exists.
    @discardableResult
    func startDotMovement() -> Bool {
        guard let runtimeGraph, var deliveryDot, deliveryDot.currentEdgeID == nil else {
            return false
        }
        guard let currentNode = runtimeGraph.nodesByID[deliveryDot.currentNodeID],
              let edgeID = currentNode.activeOutgoingEdgeID,
              runtimeGraph.edgesByID[edgeID] != nil else {
            return false
        }

        deliveryDot.currentEdgeID = edgeID
        deliveryDot.progressAlongEdge = 0
        self.deliveryDot = deliveryDot
        return true
    }

    /// Advances the delivery dot along its current edge using frame-rate independent timing.
    func updateDot(deltaTime: TimeInterval) {
        guard deltaTime > 0,
              let runtimeGraph,
              var deliveryDot,
              let currentEdgeID = deliveryDot.currentEdgeID,
              let edge = runtimeGraph.edgesByID[currentEdgeID],
              let fromNode = runtimeGraph.nodesByID[edge.fromNodeID],
              let toNode = runtimeGraph.nodesByID[edge.toNodeID] else {
            return
        }

        let edgeLength = hypot(toNode.x - fromNode.x, toNode.y - fromNode.y)
        guard edgeLength > 0 else {
            snapDotToNode(edge.toNodeID, dot: &deliveryDot)
            self.deliveryDot = deliveryDot
            return
        }

        let progressDelta = (dotSpeed * deltaTime) / edgeLength
        let nextProgress = min(deliveryDot.progressAlongEdge + progressDelta, 1)

        if nextProgress >= 1 {
            snapDotToNode(edge.toNodeID, dot: &deliveryDot)
        } else {
            deliveryDot.progressAlongEdge = nextProgress
        }

        self.deliveryDot = deliveryDot
    }

    private func snapDotToNode(_ nodeID: String, dot: inout DeliveryDot) {
        dot.currentNodeID = nodeID
        dot.currentEdgeID = nil
        dot.progressAlongEdge = 0
    }
}
