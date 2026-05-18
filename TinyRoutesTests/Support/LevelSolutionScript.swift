import Foundation

struct LevelSolutionScript: Codable {
    let levelID: String
    var description: String?
    var expectedOutcome: ExpectedOutcome
    var maxTaps: Int
    var requiresWithinTimeLimit: Bool
    /// `true` for scripts that are not yet real solutions (e.g. Task 018 placeholders).
    /// Solvability tests skip placeholder scripts until Task 019 supplies real solutions.
    var isPlaceholder: Bool
    var actions: [LevelSolutionAction]

    init(
        levelID: String,
        description: String? = nil,
        expectedOutcome: ExpectedOutcome,
        maxTaps: Int,
        requiresWithinTimeLimit: Bool,
        isPlaceholder: Bool = false,
        actions: [LevelSolutionAction]
    ) {
        self.levelID = levelID
        self.description = description
        self.expectedOutcome = expectedOutcome
        self.maxTaps = maxTaps
        self.requiresWithinTimeLimit = requiresWithinTimeLimit
        self.isPlaceholder = isPlaceholder
        self.actions = actions
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        levelID = try container.decode(String.self, forKey: .levelID)
        description = try container.decodeIfPresent(String.self, forKey: .description)
        expectedOutcome = try container.decode(ExpectedOutcome.self, forKey: .expectedOutcome)
        maxTaps = try container.decode(Int.self, forKey: .maxTaps)
        requiresWithinTimeLimit = try container.decode(Bool.self, forKey: .requiresWithinTimeLimit)
        isPlaceholder = try container.decodeIfPresent(Bool.self, forKey: .isPlaceholder) ?? false
        actions = try container.decode([LevelSolutionAction].self, forKey: .actions)
    }
}

struct LevelSolutionAction: Codable {
    var timeSeconds: TimeInterval
    var tapNodeID: String
}

enum ExpectedOutcome: String, Codable {
    case completed
}
