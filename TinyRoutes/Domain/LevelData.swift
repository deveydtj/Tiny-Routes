import Foundation

/// Describes the data needed to load and run a single puzzle level.
struct LevelData: Identifiable, Codable {
    let id: String
    var name: String
    var graph: RouteGraph
    var packageNodeID: String
    var destinationNodeID: String
    var timeLimitSeconds: Int
}
