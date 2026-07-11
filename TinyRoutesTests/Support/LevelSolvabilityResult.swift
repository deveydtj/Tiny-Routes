import Foundation
@testable import TinyRoutes

struct LevelSolvabilityResult: Equatable {
    let levelID: String
    let outcome: LevelOutcome?
    let elapsedTime: TimeInterval
    let timeRemaining: TimeInterval?
    let tapCount: Int
    let finalNodeID: String?
    let currentEdgeID: String?
    let progressAlongEdge: Double?
    let didCollectPackage: Bool
    let executedActions: [ExecutedLevelSolutionAction]
    let stepCount: Int
    let noProgressStepCount: Int
}

struct ExecutedLevelSolutionAction: Equatable {
    let requestedTime: TimeInterval
    let nodeID: String
    let tapResult: SwitchTapResult
    let actualTapCountAfterAction: Int

    var didRotate: Bool { tapResult.didRotate }
}
