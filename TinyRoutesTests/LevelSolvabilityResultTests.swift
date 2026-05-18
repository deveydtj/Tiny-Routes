import XCTest
@testable import TinyRoutes

final class LevelSolvabilityResultTests: XCTestCase {
    func testResultExposesOutcomeTimeTapsAndFinalNode() {
        let result = LevelSolvabilityResult(
            levelID: "level_001",
            outcome: .completed,
            elapsedTime: 2.5,
            timeRemaining: 7.5,
            tapCount: 1,
            finalNodeID: "destination",
            didCollectPackage: true,
            executedActions: []
        )

        XCTAssertEqual(result.levelID, "level_001")
        XCTAssertEqual(result.outcome, .completed)
        XCTAssertEqual(result.elapsedTime, 2.5)
        XCTAssertEqual(result.timeRemaining, 7.5)
        XCTAssertEqual(result.tapCount, 1)
        XCTAssertEqual(result.finalNodeID, "destination")
        XCTAssertTrue(result.didCollectPackage)
    }

    func testResultExposesExecutedActionDetails() {
        let action = ExecutedLevelSolutionAction(
            requestedTime: 1.25,
            nodeID: "switch_a",
            didRotate: true,
            actualTapCountAfterAction: 2
        )
        let result = LevelSolvabilityResult(
            levelID: "level_002",
            outcome: .failed(reason: .deadEnd),
            elapsedTime: 3,
            timeRemaining: nil,
            tapCount: 2,
            finalNodeID: "dead_end",
            didCollectPackage: false,
            executedActions: [action]
        )

        XCTAssertEqual(result.executedActions.count, 1)
        XCTAssertEqual(result.executedActions[0].requestedTime, 1.25)
        XCTAssertEqual(result.executedActions[0].nodeID, "switch_a")
        XCTAssertTrue(result.executedActions[0].didRotate)
        XCTAssertEqual(result.executedActions[0].actualTapCountAfterAction, 2)
    }
}
