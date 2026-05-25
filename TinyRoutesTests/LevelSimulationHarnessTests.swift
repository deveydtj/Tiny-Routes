import XCTest
@testable import TinyRoutes

final class LevelSimulationHarnessTests: XCTestCase {
    private func makeSwitchLevel() -> LevelData {
        let nodes = [
            RouteNode(id: "start", x: 0, y: 0, outgoingEdgeIDs: ["e_start_switch"]),
            RouteNode(id: "switch", x: 1, y: 0, outgoingEdgeIDs: ["e_switch_package", "e_switch_dead_end", "e_switch_destination"]),
            RouteNode(id: "package", x: 2, y: 1, outgoingEdgeIDs: ["e_package_return"]),
            RouteNode(id: "dead_end", x: 2, y: -1, outgoingEdgeIDs: []),
            RouteNode(id: "destination", x: 3, y: 0, outgoingEdgeIDs: [])
        ]
        let edges = [
            RouteEdge(id: "e_start_switch", fromNodeID: "start", toNodeID: "switch"),
            RouteEdge(id: "e_switch_package", fromNodeID: "switch", toNodeID: "package"),
            RouteEdge(id: "e_package_return", fromNodeID: "package", toNodeID: "switch"),
            RouteEdge(id: "e_switch_destination", fromNodeID: "switch", toNodeID: "destination"),
            RouteEdge(id: "e_switch_dead_end", fromNodeID: "switch", toNodeID: "dead_end")
        ]

        return LevelData(
            id: "level_simulation_harness_switch",
            name: "Switch Harness Test",
            graph: RouteGraph(nodes: nodes, edges: edges),
            startNodeID: "start",
            packageNodeID: "package",
            destinationNodeID: "destination",
            timeLimitSeconds: 45,
            parTaps: 6
        )
    }

    func testRunCompletesLevel001WithProductionScript() throws {
        let level = try XCTUnwrap(
            TestLevelCatalog().loadAllProductionLevels().first(where: { $0.id == "level_001" })
        )
        let script = try LevelSolutionRepository().loadScript(levelID: "level_001")
        let harness = LevelSimulationHarness(limits: .productionSolvability)

        let result = try harness.run(level: level, script: script)

        XCTAssertEqual(result.levelID, "level_001")
        XCTAssertEqual(result.outcome, .completed)
        XCTAssertLessThanOrEqual(result.tapCount, script.maxTaps)
        XCTAssertEqual(result.finalNodeID, level.destinationNodeID)
        XCTAssertTrue(result.didCollectPackage)
        XCTAssertEqual(result.executedActions.count, script.actions.count)
        XCTAssertGreaterThan(result.stepCount, 0)
        XCTAssertEqual(result.noProgressStepCount, 0)
        XCTAssertLessThanOrEqual(result.elapsedTime, TimeInterval(level.timeLimitSeconds))
    }

    func testRunThrowsWhenMaxStepCountIsExceeded() throws {
        let level = try XCTUnwrap(
            TestLevelCatalog().loadAllProductionLevels().first(where: { $0.id == "level_001" })
        )
        let script = try LevelSolutionRepository().loadScript(levelID: "level_001")
        let harness = LevelSimulationHarness(
            engineFactory: { RouteEngine(dotSpeed: 1) },
            frameStep: 1.0 / 60.0,
            limits: LevelSimulationLimits(
                maxStepCount: 1,
                maxSimulatedTimeSeconds: nil,
                maxNoProgressStepCount: 10
            )
        )

        XCTAssertThrowsError(try harness.run(level: level, script: script)) { error in
            guard case let LevelSimulationHarnessError.exceededMaxStepCount(diagnostics) = error else {
                XCTFail("Expected exceededMaxStepCount, got \(error)")
                return
            }
            XCTAssertEqual(diagnostics.levelID, "level_001")
            XCTAssertEqual(diagnostics.stepCount, 1)
            XCTAssertFalse(diagnostics.phase.isEmpty)
        }
    }

    func testRunThrowsWhenActionTimeIsNegative() {
        let level = makeSwitchLevel()
        let script = LevelSolutionScript(
            levelID: level.id,
            description: "Invalid negative time.",
            expectedOutcome: .completed,
            maxTaps: 1,
            requiresWithinTimeLimit: true,
            actions: [
                LevelSolutionAction(timeSeconds: -0.1, tapNodeID: "switch")
            ]
        )
        let harness = LevelSimulationHarness(limits: .fastTest)

        XCTAssertThrowsError(try harness.run(level: level, script: script)) { error in
            guard case let LevelSimulationHarnessError.invalidActionTime(levelID, nodeID, timeSeconds) = error else {
                XCTFail("Expected invalidActionTime, got \(error)")
                return
            }
            XCTAssertEqual(levelID, level.id)
            XCTAssertEqual(nodeID, "switch")
            XCTAssertEqual(timeSeconds, -0.1)
        }
    }

    func testRunThrowsWhenActionTimeIsNotFinite() {
        let level = makeSwitchLevel()
        let script = LevelSolutionScript(
            levelID: level.id,
            description: "Invalid infinite time.",
            expectedOutcome: .completed,
            maxTaps: 1,
            requiresWithinTimeLimit: true,
            actions: [
                LevelSolutionAction(timeSeconds: .infinity, tapNodeID: "switch")
            ]
        )
        let harness = LevelSimulationHarness(limits: .fastTest)

        XCTAssertThrowsError(try harness.run(level: level, script: script)) { error in
            guard case let LevelSimulationHarnessError.invalidActionTime(levelID, nodeID, timeSeconds) = error else {
                XCTFail("Expected invalidActionTime, got \(error)")
                return
            }
            XCTAssertEqual(levelID, level.id)
            XCTAssertEqual(nodeID, "switch")
            XCTAssertFalse(timeSeconds.isFinite)
        }
    }

    func testRunCanStillCompleteLevel001WithProductionLimits() throws {
        let level = try XCTUnwrap(
            TestLevelCatalog().loadAllProductionLevels().first(where: { $0.id == "level_001" })
        )
        let script = try LevelSolutionRepository().loadScript(levelID: "level_001")
        let harness = LevelSimulationHarness(limits: .productionSolvability)

        let result = try harness.run(level: level, script: script)

        XCTAssertEqual(result.outcome, .completed)
        XCTAssertEqual(result.finalNodeID, "destination")
        XCTAssertTrue(result.didCollectPackage)
        XCTAssertGreaterThan(result.stepCount, 0)
    }

    func testRunReturnsTimeExpiredForSmallCycleInsteadOfHanging() throws {
        let nodes = [
            RouteNode(id: "start", x: 0, y: 0, outgoingEdgeIDs: ["e_start_a"]),
            RouteNode(id: "a", x: 1, y: 0, outgoingEdgeIDs: ["e_a_b"]),
            RouteNode(id: "b", x: 2, y: 0, outgoingEdgeIDs: ["e_b_a"]),
            RouteNode(id: "destination", x: 3, y: 0, outgoingEdgeIDs: [])
        ]
        let edges = [
            RouteEdge(id: "e_start_a", fromNodeID: "start", toNodeID: "a"),
            RouteEdge(id: "e_a_b", fromNodeID: "a", toNodeID: "b"),
            RouteEdge(id: "e_b_a", fromNodeID: "b", toNodeID: "a")
        ]
        let level = LevelData(
            id: "small_cycle",
            name: "Small Cycle",
            graph: RouteGraph(nodes: nodes, edges: edges),
            startNodeID: "start",
            packageNodeID: "start",
            destinationNodeID: "destination",
            timeLimitSeconds: 1,
            parTaps: 1
        )
        let script = LevelSolutionScript(
            levelID: level.id,
            description: "Cycle should be bounded by the level timer.",
            expectedOutcome: .completed,
            maxTaps: 0,
            requiresWithinTimeLimit: false,
            actions: []
        )
        let harness = LevelSimulationHarness(limits: .fastTest)

        let result = try harness.run(level: level, script: script)

        XCTAssertEqual(result.outcome, .failed(reason: .timeExpired))
        XCTAssertTrue(result.didCollectPackage)
        XCTAssertLessThanOrEqual(result.elapsedTime, 1.0)
        XCTAssertLessThanOrEqual(result.stepCount, LevelSimulationLimits.fastTest.maxStepCount)
    }

    func testRunExecutesTimedActionsInChronologicalOrderAndRecordsResults() throws {
        let level = makeSwitchLevel()
        let script = LevelSolutionScript(
            levelID: level.id,
            description: "Harness test script with unsorted actions.",
            expectedOutcome: .completed,
            maxTaps: 2,
            requiresWithinTimeLimit: true,
            actions: [
                LevelSolutionAction(timeSeconds: 0.006, tapNodeID: "switch"),
                LevelSolutionAction(timeSeconds: 0.005, tapNodeID: "switch")
            ]
        )
        let harness = LevelSimulationHarness(
            engineFactory: { RouteEngine(dotSpeed: 100) },
            frameStep: 0.001
        )

        let result = try harness.run(level: level, script: script)

        XCTAssertEqual(result.tapCount, 2)
        XCTAssertEqual(result.executedActions.count, 2)
        XCTAssertEqual(result.executedActions[0].requestedTime, 0.005, accuracy: 0.000_001)
        XCTAssertEqual(result.executedActions[1].requestedTime, 0.006, accuracy: 0.000_001)
        XCTAssertEqual(result.executedActions[0].nodeID, "switch")
        XCTAssertEqual(result.executedActions[1].nodeID, "switch")
        XCTAssertTrue(result.executedActions[0].didRotate)
        XCTAssertTrue(result.executedActions[1].didRotate)
        XCTAssertEqual(result.executedActions[0].actualTapCountAfterAction, 1)
        XCTAssertEqual(result.executedActions[1].actualTapCountAfterAction, 2)
        XCTAssertEqual(result.outcome, .failed(reason: .reachedDestinationWithoutPackage))
        XCTAssertGreaterThan(result.stepCount, 0)
    }
}
