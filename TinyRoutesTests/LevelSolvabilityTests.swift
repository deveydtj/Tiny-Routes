import XCTest
@testable import TinyRoutes

final class LevelSolvabilityTests: XCTestCase {
    func testEveryProductionLevelCompletesWithItsSolutionScript() throws {
        let levels = try TestLevelCatalog().loadAllProductionLevels()
        XCTAssertFalse(levels.isEmpty, "Expected at least one production level")

        let repository = LevelSolutionRepository()
        let harness = LevelSimulationHarness(
            engineFactory: { RouteEngine(dotSpeed: 100) },
            frameStep: 0.001
        )

        for level in levels {
            let script = try repository.loadScript(levelID: level.id)
            let result = try harness.run(level: level, script: script)
            let prefix = "\(level.id):"

            switch script.expectedOutcome {
            case .completed:
                XCTAssertEqual(result.outcome, .completed, "\(prefix) expected completed outcome, got \(String(describing: result.outcome))")
            }

            if script.requiresWithinTimeLimit {
                XCTAssertLessThanOrEqual(
                    result.elapsedTime,
                    TimeInterval(level.timeLimitSeconds),
                    "\(prefix) expected completion within time limit \(level.timeLimitSeconds)s, got \(result.elapsedTime)s"
                )
            }

            XCTAssertLessThanOrEqual(
                result.tapCount,
                script.maxTaps,
                "\(prefix) expected tap count <= script maxTaps \(script.maxTaps), got \(result.tapCount)"
            )

            if script.maxTaps <= level.parTaps {
                XCTAssertLessThanOrEqual(
                    result.tapCount,
                    level.parTaps,
                    "\(prefix) expected par-level tap count <= \(level.parTaps), got \(result.tapCount)"
                )
            }
        }
    }
}
