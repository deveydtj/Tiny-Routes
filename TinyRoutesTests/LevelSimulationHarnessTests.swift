import XCTest
@testable import TinyRoutes

final class LevelSimulationHarnessTests: XCTestCase {
    func testRunCompletesLevel001WithoutActions() throws {
        let level = try XCTUnwrap(
            TestLevelCatalog().loadAllProductionLevels().first(where: { $0.id == "level_001" })
        )
        let script = try LevelSolutionRepository().loadScript(levelID: "level_001")
        let harness = LevelSimulationHarness(
            engineFactory: { RouteEngine(dotSpeed: 100) },
            frameStep: 0.1
        )

        let result = try harness.run(level: level, script: script)

        XCTAssertEqual(result.levelID, "level_001")
        XCTAssertEqual(result.outcome, .completed)
        XCTAssertEqual(result.tapCount, 0)
        XCTAssertEqual(result.finalNodeID, "destination")
        XCTAssertTrue(result.didCollectPackage)
        XCTAssertTrue(result.executedActions.isEmpty)
        XCTAssertLessThanOrEqual(result.elapsedTime, TimeInterval(level.timeLimitSeconds))
    }
}
