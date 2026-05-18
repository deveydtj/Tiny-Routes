import Foundation

struct LevelSolutionScript: Codable {
    let levelID: String
    var description: String?
    var expectedOutcome: ExpectedOutcome
    var maxTaps: Int
    var requiresWithinTimeLimit: Bool
    var actions: [LevelSolutionAction]
}

struct LevelSolutionAction: Codable {
    var timeSeconds: TimeInterval
    var tapNodeID: String
}

enum ExpectedOutcome: String, Codable {
    case completed
}
