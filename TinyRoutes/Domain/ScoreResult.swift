import Foundation

/// The outcome of a completed level attempt.
/// Placeholder — fields populated in scoring stories.
struct ScoreResult {
    var levelID: String
    var stars: Int = 0
    var timeTaken: TimeInterval = 0
    var tapCount: Int = 0
}
