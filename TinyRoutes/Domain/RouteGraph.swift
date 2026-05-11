import Foundation

/// Represents the node and edge collections that define a level route board.
struct RouteGraph: Codable {
    var nodes: [RouteNode]
    var edges: [RouteEdge]

    init(nodes: [RouteNode] = [], edges: [RouteEdge] = []) {
        self.nodes = nodes
        self.edges = edges
    }
}
