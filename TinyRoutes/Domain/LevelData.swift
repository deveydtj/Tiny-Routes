import Foundation

/// Describes the data needed to load and run a single puzzle level.
struct LevelData: Identifiable, Codable {
    let id: String
    var name: String
    var graph: RouteGraph
    var startNodeID: String
    var packageNodeID: String
    var destinationNodeID: String
    var timeLimitSeconds: Int
    var parTaps: Int
}
