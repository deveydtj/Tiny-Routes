import Foundation

/// Represents a route-map intersection with a stable position and outgoing links.
struct RouteNode: Identifiable, Codable {
    let id: String
    var x: Double
    var y: Double
    var outgoingEdgeIDs: [String]
}
