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
    }
}
