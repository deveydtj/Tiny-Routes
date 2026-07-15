import Foundation

/// Describes the data needed to load and run a single puzzle level.
struct LevelData: Identifiable, Codable {
    var schemaVersion: Int?
    var rules: LevelRules?
    let id: String
    var name: String
    var graph: RouteGraph
    var startNodeID: String
    var packageNodeID: String
    var destinationNodeID: String
    var timeLimitSeconds: Int
    var parTaps: Int
    var tutorialMessage: String?

    /// Rules used by runtime callers. Missing rules retain legacy behavior while
    /// the production level corpus is migrated to schema version 2.
    var effectiveRules: LevelRules {
        rules ?? .legacyDefaults
    }

    init(
        schemaVersion: Int? = nil,
        rules: LevelRules? = nil,
        id: String,
        name: String,
        graph: RouteGraph,
        startNodeID: String,
        packageNodeID: String,
        destinationNodeID: String,
        timeLimitSeconds: Int,
        parTaps: Int,
        tutorialMessage: String? = nil
    ) {
        self.schemaVersion = schemaVersion
        self.rules = rules
        self.id = id
        self.name = name
        self.graph = graph
        self.startNodeID = startNodeID
        self.packageNodeID = packageNodeID
        self.destinationNodeID = destinationNodeID
        self.timeLimitSeconds = timeLimitSeconds
        self.parTaps = parTaps
        self.tutorialMessage = tutorialMessage
    }
}
