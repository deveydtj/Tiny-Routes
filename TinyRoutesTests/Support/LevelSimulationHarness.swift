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
            executedActions: []
        )
    }
}
