import Foundation
@testable import TinyRoutes

final class LevelSimulationHarness {
    private let engineFactory: () -> RouteEngine
    private let frameStep: TimeInterval

    init(
        engineFactory: @escaping () -> RouteEngine = { RouteEngine() },
        frameStep: TimeInterval = 1.0 / 60.0
    ) {
        self.engineFactory = engineFactory
        self.frameStep = frameStep > 0 ? frameStep : 1.0 / 60.0
    }

    func run(level: LevelData, script: LevelSolutionScript) throws -> LevelSolvabilityResult {
        let engine = engineFactory()
        try engine.buildGraph(from: level)
        _ = engine.startDotMovement()
        var executedActions: [ExecutedLevelSolutionAction] = []

        for action in script.actions.sorted(by: { $0.timeSeconds < $1.timeSeconds }) {
            advance(engine: engine, toElapsedTime: action.timeSeconds)
            guard engine.levelOutcome == nil else {
                break
            }

            let didRotate = engine.rotateSwitchNode(nodeID: action.tapNodeID)
            executedActions.append(
                ExecutedLevelSolutionAction(
                    requestedTime: action.timeSeconds,
                    nodeID: action.tapNodeID,
                    didRotate: didRotate,
                    actualTapCountAfterAction: engine.tapCount
                )
            )
        }

        while engine.levelOutcome == nil, let timeRemaining = engine.timeRemaining, timeRemaining > 0 {
            engine.updateDot(deltaTime: min(frameStep, timeRemaining))
        }

        return LevelSolvabilityResult(
            levelID: level.id,
            outcome: engine.levelOutcome,
            elapsedTime: engine.elapsedTime ?? 0,
            timeRemaining: engine.timeRemaining,
            tapCount: engine.tapCount,
            finalNodeID: engine.deliveryDot?.currentNodeID,
            didCollectPackage: engine.deliveryDot?.hasCollectedPackage ?? false,
            executedActions: executedActions
        )
    }

    private func advance(engine: RouteEngine, toElapsedTime targetElapsedTime: TimeInterval) {
        let clampedTarget = max(targetElapsedTime, 0)
        while engine.levelOutcome == nil {
            let elapsedTime = engine.elapsedTime ?? 0
            let remainingToTarget = clampedTarget - elapsedTime
            guard remainingToTarget > 0,
                  let timeRemaining = engine.timeRemaining,
                  timeRemaining > 0 else {
                return
            }

            engine.updateDot(deltaTime: min(frameStep, remainingToTarget, timeRemaining))
        }
    }
}
