import Foundation

/// A runtime snapshot of a route-map node, including the currently active outgoing edge for switch nodes.
struct RuntimeRouteNode {
    let id: String
    let x: Double
    let y: Double
    let outgoingEdgeIDs: [String]
    /// The edge ID the dot will follow when leaving this node.
    /// `nil` for leaf nodes (no outgoing edges); set to the first outgoing edge for all other nodes.
    var activeOutgoingEdgeID: String?
}

/// A runtime snapshot of a directed connection between two route-map nodes.
struct RuntimeRouteEdge {
    let id: String
    let fromNodeID: String
    let toNodeID: String
}

/// The live, mutable graph used during a running level.
/// Nodes and edges are keyed by their IDs for O(1) lookup.
struct RuntimeRouteGraph {
    var nodesByID: [String: RuntimeRouteNode]
    let edgesByID: [String: RuntimeRouteEdge]
}
