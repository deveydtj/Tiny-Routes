import Foundation
@testable import TinyRoutes

struct LevelSolvabilityResult {
    let levelID: String
    let outcome: LevelOutcome?
    let elapsedTime: TimeInterval
    let timeRemaining: TimeInterval?
    let tapCount: Int
    let finalNodeID: String?
    let didCollectPackage: Bool
    let executedActions: [ExecutedLevelSolutionAction]
}

struct ExecutedLevelSolutionAction {
    let requestedTime: TimeInterval
    let nodeID: String
    let didRotate: Bool
    let actualTapCountAfterAction: Int
}
