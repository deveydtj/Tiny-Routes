import Foundation

/// Represents a directed connection from one route node to another.
struct RouteEdge: Identifiable, Codable {
    let id: String
    let fromNodeID: String
    let toNodeID: String
}
