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
            currentEdgeID: nil,
            progressAlongEdge: nil,
            didCollectPackage: true,
            executedActions: [],
            stepCount: 150,
            noProgressStepCount: 0
        )

        XCTAssertEqual(result.levelID, "level_001")
        XCTAssertEqual(result.outcome, .completed)
        XCTAssertEqual(result.elapsedTime, 2.5)
        XCTAssertEqual(result.timeRemaining, 7.5)
        XCTAssertEqual(result.tapCount, 1)
        XCTAssertEqual(result.finalNodeID, "destination")
        XCTAssertNil(result.currentEdgeID)
        XCTAssertNil(result.progressAlongEdge)
        XCTAssertTrue(result.didCollectPackage)
        XCTAssertEqual(result.stepCount, 150)
        XCTAssertEqual(result.noProgressStepCount, 0)
    }

    func testResultExposesExecutedActionDetails() {
        let action = ExecutedLevelSolutionAction(
            requestedTime: 1.25,
            nodeID: "switch_a",
            tapResult: .accepted(nodeID: "switch_a", activeEdgeID: "edge_a"),
            actualTapCountAfterAction: 2
        )
        let result = LevelSolvabilityResult(
            levelID: "level_002",
            outcome: .failed(reason: .deadEnd),
            elapsedTime: 3,
            timeRemaining: nil,
            tapCount: 2,
            finalNodeID: "dead_end",
            currentEdgeID: nil,
            progressAlongEdge: nil,
            didCollectPackage: false,
            executedActions: [action],
            stepCount: 90,
            noProgressStepCount: 0
        )

        XCTAssertEqual(result.executedActions.count, 1)
        XCTAssertEqual(result.executedActions[0].requestedTime, 1.25)
        XCTAssertEqual(result.executedActions[0].nodeID, "switch_a")
        XCTAssertTrue(result.executedActions[0].didRotate)
        XCTAssertEqual(result.executedActions[0].actualTapCountAfterAction, 2)
    }
}
