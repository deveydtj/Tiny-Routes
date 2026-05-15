import Foundation

/// The runtime position of the delivery dot on the route board.
struct DeliveryDotPosition: Equatable {
    let x: Double
    let y: Double
}

/// Mutable runtime state for the moving delivery dot.
struct DeliveryDot {
    /// The node currently occupied by the dot when not traversing an edge.
    var currentNodeID: String
    /// The edge currently being traversed, or `nil` while idle on a node.
    var currentEdgeID: String?
    /// Edge traversal progress in the closed range [0, 1].
    var progressAlongEdge: Double
    /// Whether the package objective has been collected.
    var hasCollectedPackage: Bool

    init(
        currentNodeID: String,
        currentEdgeID: String? = nil,
        progressAlongEdge: Double = 0,
        hasCollectedPackage: Bool = false
    ) {
        self.currentNodeID = currentNodeID
        self.currentEdgeID = currentEdgeID
        self.progressAlongEdge = progressAlongEdge
        self.hasCollectedPackage = hasCollectedPackage
    }

    /// Returns the dot's current board-space position using node or edge interpolation state.
    func runtimePosition(in runtimeGraph: RuntimeRouteGraph) -> DeliveryDotPosition? {
        if let currentEdgeID,
           let edge = runtimeGraph.edgesByID[currentEdgeID],
           let fromNode = runtimeGraph.nodesByID[edge.fromNodeID],
           let toNode = runtimeGraph.nodesByID[edge.toNodeID] {
            let clampedProgress = max(0, min(progressAlongEdge, 1))
            return DeliveryDotPosition(
                x: fromNode.x + ((toNode.x - fromNode.x) * clampedProgress),
                y: fromNode.y + ((toNode.y - fromNode.y) * clampedProgress)
            )
        }

        guard let node = runtimeGraph.nodesByID[currentNodeID] else {
            return nil
        }
        return DeliveryDotPosition(x: node.x, y: node.y)
    }
}
