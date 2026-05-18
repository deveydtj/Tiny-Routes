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
    /// Edge traversal progress where 0 is edge-start and 1 is edge-end.
    /// Values outside [0, 1] are clamped when computing runtime position.
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
    /// Returns `nil` when the dot references a node/edge that does not exist in the provided graph.
    func runtimePosition(in runtimeGraph: RuntimeRouteGraph) -> DeliveryDotPosition? {
        if let currentEdgeID,
           let edge = runtimeGraph.edgesByID[currentEdgeID] {
            let clampedProgress = max(0, min(progressAlongEdge, 1))
            let roadPoint = edge.roadPath.point(atProgress: clampedProgress)
            return DeliveryDotPosition(
                x: roadPoint.x,
                y: roadPoint.y
            )
        }

        guard let node = runtimeGraph.nodesByID[currentNodeID] else {
            return nil
        }
        return DeliveryDotPosition(x: node.x, y: node.y)
    }
}
