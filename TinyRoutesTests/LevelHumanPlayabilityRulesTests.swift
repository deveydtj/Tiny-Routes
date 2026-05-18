import XCTest
@testable import TinyRoutes

final class LevelHumanPlayabilityRulesTests: XCTestCase {
    func testTapSpacingViolationsReportsActionsThatAreTooCloseTogether() {
        let script = LevelSolutionScript(
            levelID: "level_spacing",
            description: "Spacing rule test",
            expectedOutcome: .completed,
            maxTaps: 2,
            requiresWithinTimeLimit: true,
            actions: [
                LevelSolutionAction(timeSeconds: 0.10, tapNodeID: "switch_a"),
                LevelSolutionAction(timeSeconds: 0.35, tapNodeID: "switch_b")
            ]
        )

        let violations = LevelHumanPlayabilityRules.tapSpacingViolations(for: script)

        XCTAssertEqual(violations.count, 1)
        XCTAssertEqual(
            violations.first,
            "level_spacing: action[0] at 0.10s and action[1] at 0.35s are only 0.25s apart (minimum 0.30s)"
        )
    }

    func testTapSpacingViolationsAllowsActionsAtMinimumSpacing() {
        let script = LevelSolutionScript(
            levelID: "level_spacing_ok",
            description: "Spacing rule boundary test",
            expectedOutcome: .completed,
            maxTaps: 2,
            requiresWithinTimeLimit: true,
            actions: [
                LevelSolutionAction(timeSeconds: 0.10, tapNodeID: "switch_a"),
                LevelSolutionAction(timeSeconds: 0.40, tapNodeID: "switch_b")
            ]
        )

        XCTAssertTrue(LevelHumanPlayabilityRules.tapSpacingViolations(for: script).isEmpty)
    }

    func testTapSpacingViolationsAllowsSpacingWithinFloatingPointToleranceOfMinimum() {
        let script = LevelSolutionScript(
            levelID: "level_spacing_tolerance",
            description: "Spacing rule tolerance test",
            expectedOutcome: .completed,
            maxTaps: 2,
            requiresWithinTimeLimit: true,
            actions: [
                LevelSolutionAction(timeSeconds: 0.40, tapNodeID: "switch_a"),
                LevelSolutionAction(timeSeconds: 0.70, tapNodeID: "switch_b")
            ]
        )

        XCTAssertTrue(LevelHumanPlayabilityRules.tapSpacingViolations(for: script).isEmpty)
    }

    func testCompletionBufferViolationFailsWhenRemainingTimeIsTooSmall() {
        let level = makeLevel(id: "level_buffer")
        let result = LevelSolvabilityResult(
            levelID: level.id,
            outcome: .completed,
            elapsedTime: 29.75,
            timeRemaining: 0.25,
            tapCount: 1,
            finalNodeID: "destination",
            didCollectPackage: true,
            executedActions: []
        )

        let violation = LevelHumanPlayabilityRules.completionBufferViolation(level: level, result: result)

        XCTAssertEqual(
            violation,
            "level_buffer: completed with only 0.25s remaining before the 30s time limit (minimum buffer 0.50s)"
        )
    }

    func testCompletionBufferViolationAllowsMinimumRemainingTime() {
        let level = makeLevel(id: "level_buffer_ok")
        let result = LevelSolvabilityResult(
            levelID: level.id,
            outcome: .completed,
            elapsedTime: 29.50,
            timeRemaining: 0.50,
            tapCount: 1,
            finalNodeID: "destination",
            didCollectPackage: true,
            executedActions: []
        )

        XCTAssertNil(LevelHumanPlayabilityRules.completionBufferViolation(level: level, result: result))
    }

    func testCompletionBufferViolationAllowsRemainingTimeWithinFloatingPointToleranceOfMinimum() {
        let level = makeLevel(id: "level_buffer_tolerance")
        let result = LevelSolvabilityResult(
            levelID: level.id,
            outcome: .completed,
            elapsedTime: 29.50,
            timeRemaining: 0.70 - 0.20,
            tapCount: 1,
            finalNodeID: "destination",
            didCollectPackage: true,
            executedActions: []
        )

        XCTAssertNil(LevelHumanPlayabilityRules.completionBufferViolation(level: level, result: result))
    }

    private func makeLevel(id: String) -> LevelData {
        LevelData(
            id: id,
            name: "Human Playability Rule Test",
            graph: RouteGraph(
                nodes: [
                    RouteNode(id: "start", x: 0, y: 0, outgoingEdgeIDs: ["e_start_destination"]),
                    RouteNode(id: "destination", x: 1, y: 0, outgoingEdgeIDs: [])
                ],
                edges: [
                    RouteEdge(id: "e_start_destination", fromNodeID: "start", toNodeID: "destination")
                ]
            ),
            startNodeID: "start",
            packageNodeID: "destination",
            destinationNodeID: "destination",
            timeLimitSeconds: 30,
            parTaps: 1
        )
    }
}
