import Foundation

/// Stores beginner-safe player progression values and unlocked content state.
struct PlayerProfile {
    var unlockedLevelIDs: [String] = ["level_001"]
    var completedLevelIDs: [String] = []
    var bestStarsByLevelID: [String: Int] = [:]
    var coinTotal: Int = 0
}
