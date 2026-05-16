import XCTest
@testable import TinyRoutes

final class RouteEngineTests: XCTestCase {

    // MARK: - Helpers

    /// Returns a minimal LevelData that mirrors level_001.json.
    private func makeLevelData(
        startNodeID: String = "start",
        packageNodeID: String = "package",
        destinationNodeID: String = "destination"
    ) -> LevelData {
        let nodes = [
            RouteNode(id: "start",       x: 0, y: 0,  outgoingEdgeIDs: ["e_start_switch"]),
            RouteNode(id: "switch",      x: 1, y: 0,  outgoingEdgeIDs: ["e_switch_package", "e_switch_dead_end", "e_switch_destination"]),
            RouteNode(id: "package",     x: 2, y: 1,  outgoingEdgeIDs: ["e_package_return"]),
            RouteNode(id: "dead_end",    x: 2, y: -1, outgoingEdgeIDs: []),
            RouteNode(id: "destination", x: 3, y: 0,  outgoingEdgeIDs: [])
        ]
        let edges = [
            RouteEdge(id: "e_start_switch",       fromNodeID: "start",   toNodeID: "switch"),
            RouteEdge(id: "e_switch_package",      fromNodeID: "switch",  toNodeID: "package"),
            RouteEdge(id: "e_package_return",      fromNodeID: "package", toNodeID: "switch"),
            RouteEdge(id: "e_switch_destination",  fromNodeID: "switch",  toNodeID: "destination"),
            RouteEdge(id: "e_switch_dead_end",     fromNodeID: "switch",  toNodeID: "dead_end")
        ]
        return LevelData(
            id: "level_001",
            name: "First Dispatch",
            graph: RouteGraph(nodes: nodes, edges: edges),
            startNodeID: startNodeID,
            packageNodeID: packageNodeID,
            destinationNodeID: destinationNodeID,
            timeLimitSeconds: 45,
            parTaps: 6
        )
    }

    private func assertPosition(
        _ position: DeliveryDotPosition?,
        equals expected: DeliveryDotPosition,
        accuracy: Double = 0.0001,
        file: StaticString = #filePath,
        line: UInt = #line
    ) {
        guard let position else {
            return XCTFail("Expected a delivery dot position.", file: file, line: line)
        }

        XCTAssertEqual(position.x, expected.x, accuracy: accuracy, file: file, line: line)
        XCTAssertEqual(position.y, expected.y, accuracy: accuracy, file: file, line: line)
    }

    // MARK: - Successful build

    func testBuildGraphStoresRuntimeGraph() throws {
        let engine = RouteEngine()
        try engine.buildGraph(from: makeLevelData())

        XCTAssertNotNil(engine.runtimeGraph)
    }

    func testBuildGraphInitializesDeliveryDot() throws {
        let engine = RouteEngine()
        try engine.buildGraph(from: makeLevelData())

        let dot = try XCTUnwrap(engine.deliveryDot)
        XCTAssertEqual(dot.currentNodeID, "start")
        XCTAssertNil(dot.currentEdgeID)
        XCTAssertEqual(dot.progressAlongEdge, 0)
        XCTAssertFalse(dot.hasCollectedPackage)
    }

    func testDeliveryDotReportsCurrentRuntimePositionAtStartNode() throws {
        let engine = RouteEngine()
        try engine.buildGraph(from: makeLevelData())

        let graph = try XCTUnwrap(engine.runtimeGraph)
        let dot = try XCTUnwrap(engine.deliveryDot)
        XCTAssertEqual(dot.runtimePosition(in: graph), DeliveryDotPosition(x: 0, y: 0))
    }

    func testStartDotMovementBeginsTraversingActiveOutgoingEdge() throws {
        let engine = RouteEngine()
        try engine.buildGraph(from: makeLevelData())

        XCTAssertTrue(engine.startDotMovement())

        let dot = try XCTUnwrap(engine.deliveryDot)
        XCTAssertEqual(dot.currentNodeID, "start")
        XCTAssertEqual(dot.currentEdgeID, "e_start_switch")
        XCTAssertEqual(dot.progressAlongEdge, 0)
    }

    func testUpdateDotMovesAlongSingleEdgeUsingDeltaTime() throws {
        let engine = RouteEngine(dotSpeed: 2)
        try engine.buildGraph(from: makeLevelData())
        XCTAssertTrue(engine.startDotMovement())

        engine.updateDot(deltaTime: 0.25)

        let graph = try XCTUnwrap(engine.runtimeGraph)
        let dot = try XCTUnwrap(engine.deliveryDot)
        XCTAssertEqual(dot.currentEdgeID, "e_start_switch")
        XCTAssertEqual(dot.progressAlongEdge, 0.5, accuracy: 0.0001)
        assertPosition(dot.runtimePosition(in: graph), equals: DeliveryDotPosition(x: 0.5, y: 0))
    }

    func testUpdateDotDoesNotAutoStartMovementFromIdleNode() throws {
        let engine = RouteEngine(dotSpeed: 2)
        try engine.buildGraph(from: makeLevelData())

        engine.updateDot(deltaTime: 0.25)

        let dot = try XCTUnwrap(engine.deliveryDot)
        XCTAssertEqual(dot.currentNodeID, "start")
        XCTAssertNil(dot.currentEdgeID)
        XCTAssertEqual(dot.progressAlongEdge, 0)
    }

    func testUpdateDotSnapsToTargetNodeWithoutOvershootingAndContinuesFromNode() throws {
        let engine = RouteEngine(dotSpeed: 4)
        try engine.buildGraph(from: makeLevelData())
        XCTAssertTrue(engine.startDotMovement())

        engine.updateDot(deltaTime: 0.25)

        let graph = try XCTUnwrap(engine.runtimeGraph)
        let dot = try XCTUnwrap(engine.deliveryDot)
        XCTAssertEqual(dot.currentNodeID, "switch")
        XCTAssertEqual(dot.currentEdgeID, "e_switch_package")
        XCTAssertEqual(dot.progressAlongEdge, 0)
        assertPosition(dot.runtimePosition(in: graph), equals: DeliveryDotPosition(x: 1, y: 0))
    }

    func testUpdateDotContinuesThroughConnectedNodesUsingDefaultActiveDirections() throws {
        let engine = RouteEngine(dotSpeed: 1)
        try engine.buildGraph(from: makeLevelData())
        XCTAssertTrue(engine.startDotMovement())

        engine.updateDot(deltaTime: 2)

        let dot = try XCTUnwrap(engine.deliveryDot)
        XCTAssertEqual(dot.currentNodeID, "switch")
        XCTAssertEqual(dot.currentEdgeID, "e_switch_package")
        XCTAssertEqual(dot.progressAlongEdge, 0.70710678, accuracy: 0.0001)
    }

    func testStartDotMovementReturnsFalseAtLeafNode() throws {
        let engine = RouteEngine()
        try engine.buildGraph(from: makeLevelData(startNodeID: "destination"))

        XCTAssertFalse(engine.startDotMovement())

        let dot = try XCTUnwrap(engine.deliveryDot)
        XCTAssertEqual(dot.currentNodeID, "destination")
        XCTAssertNil(dot.currentEdgeID)
    }

    func testStartDotMovementReturnsFalseWhenActiveEdgeDoesNotLeaveCurrentNode() throws {
        let nodes = [
            RouteNode(id: "start", x: 0, y: 0, outgoingEdgeIDs: ["wrong_edge"]),
            RouteNode(id: "middle", x: 1, y: 0, outgoingEdgeIDs: ["middle_end"]),
            RouteNode(id: "end", x: 2, y: 0, outgoingEdgeIDs: [])
        ]
        let edges = [
            RouteEdge(id: "wrong_edge", fromNodeID: "middle", toNodeID: "end"),
            RouteEdge(id: "middle_end", fromNodeID: "middle", toNodeID: "end")
        ]
        let level = LevelData(
            id: "bad_outgoing_edge",
            name: "Bad Outgoing Edge",
            graph: RouteGraph(nodes: nodes, edges: edges),
            startNodeID: "start",
            packageNodeID: "start",
            destinationNodeID: "end",
            timeLimitSeconds: 10,
            parTaps: 1
        )
        let engine = RouteEngine()
        try engine.buildGraph(from: level)

        XCTAssertFalse(engine.startDotMovement())

        let dot = try XCTUnwrap(engine.deliveryDot)
        XCTAssertEqual(dot.currentNodeID, "start")
        XCTAssertNil(dot.currentEdgeID)
        XCTAssertEqual(dot.progressAlongEdge, 0)
    }

    func testUpdateDotImmediatelySnapsAcrossZeroLengthEdge() throws {
        let nodes = [
            RouteNode(id: "start", x: 0, y: 0, outgoingEdgeIDs: ["flat"]),
            RouteNode(id: "end", x: 0, y: 0, outgoingEdgeIDs: [])
        ]
        let edges = [RouteEdge(id: "flat", fromNodeID: "start", toNodeID: "end")]
        let level = LevelData(
            id: "flat",
            name: "Flat",
            graph: RouteGraph(nodes: nodes, edges: edges),
            startNodeID: "start",
            packageNodeID: "start",
            destinationNodeID: "end",
            timeLimitSeconds: 10,
            parTaps: 1
        )
        let engine = RouteEngine(dotSpeed: 1)
        try engine.buildGraph(from: level)
        XCTAssertTrue(engine.startDotMovement())

        engine.updateDot(deltaTime: 0.25)

        let dot = try XCTUnwrap(engine.deliveryDot)
        XCTAssertEqual(dot.currentNodeID, "end")
        XCTAssertNil(dot.currentEdgeID)
        XCTAssertEqual(dot.progressAlongEdge, 0)
    }

    func testUpdateDotStopsAtDeadEndWhenNoOutgoingEdgeIsAvailable() throws {
        let nodes = [
            RouteNode(id: "start", x: 0, y: 0, outgoingEdgeIDs: ["to_mid"]),
            RouteNode(id: "mid", x: 1, y: 0, outgoingEdgeIDs: ["to_dead"]),
            RouteNode(id: "dead", x: 2, y: 0, outgoingEdgeIDs: [])
        ]
        let edges = [
            RouteEdge(id: "to_mid", fromNodeID: "start", toNodeID: "mid"),
            RouteEdge(id: "to_dead", fromNodeID: "mid", toNodeID: "dead")
        ]
        let level = LevelData(
            id: "dead_end_stop",
            name: "Dead End Stop",
            graph: RouteGraph(nodes: nodes, edges: edges),
            startNodeID: "start",
            packageNodeID: "mid",
            destinationNodeID: "dead",
            timeLimitSeconds: 10,
            parTaps: 1
        )
        let engine = RouteEngine(dotSpeed: 3)
        try engine.buildGraph(from: level)
        XCTAssertTrue(engine.startDotMovement())

        engine.updateDot(deltaTime: 1)

        let dot = try XCTUnwrap(engine.deliveryDot)
        XCTAssertEqual(dot.currentNodeID, "dead")
        XCTAssertNil(dot.currentEdgeID)
        XCTAssertEqual(dot.progressAlongEdge, 0)
        XCTAssertTrue(engine.didHaltAtDeadEnd)
    }

    func testUpdateDotMarksDidHaltAtDeadEndFalseWhenStillMoving() throws {
        let engine = RouteEngine(dotSpeed: 1)
        try engine.buildGraph(from: makeLevelData())
        XCTAssertTrue(engine.startDotMovement())

        engine.updateDot(deltaTime: 0.25)

        XCTAssertFalse(engine.didHaltAtDeadEnd)
    }

    func testBuildGraphNodeAndEdgeCountsMatchLevelData() throws {
        let engine = RouteEngine()
        let level = makeLevelData()
        try engine.buildGraph(from: level)

        let graph = try XCTUnwrap(engine.runtimeGraph)
        XCTAssertEqual(graph.nodesByID.count, level.graph.nodes.count)
        XCTAssertEqual(graph.edgesByID.count, level.graph.edges.count)
    }

    func testBuildGraphAllNodeIDsArePresent() throws {
        let engine = RouteEngine()
        let level = makeLevelData()
        try engine.buildGraph(from: level)

        let graph = try XCTUnwrap(engine.runtimeGraph)
        for node in level.graph.nodes {
            XCTAssertNotNil(graph.nodesByID[node.id], "Expected runtime node for id '\(node.id)'")
        }
    }

    func testBuildGraphAllEdgeIDsArePresent() throws {
        let engine = RouteEngine()
        let level = makeLevelData()
        try engine.buildGraph(from: level)

        let graph = try XCTUnwrap(engine.runtimeGraph)
        for edge in level.graph.edges {
            XCTAssertNotNil(graph.edgesByID[edge.id], "Expected runtime edge for id '\(edge.id)'")
        }
    }

    // MARK: - Switch direction initialisation

    func testSwitchNodeInitializesWithFirstOutgoingEdge() throws {
        let engine = RouteEngine()
        try engine.buildGraph(from: makeLevelData())

        let graph = try XCTUnwrap(engine.runtimeGraph)
        let switchNode = try XCTUnwrap(graph.nodesByID["switch"])
        XCTAssertEqual(switchNode.activeOutgoingEdgeID, "e_switch_package")
    }

    func testNonSwitchNodeWithOneEdgeInitializesActiveEdge() throws {
        let engine = RouteEngine()
        try engine.buildGraph(from: makeLevelData())

        let graph = try XCTUnwrap(engine.runtimeGraph)
        let startNode = try XCTUnwrap(graph.nodesByID["start"])
        XCTAssertEqual(startNode.activeOutgoingEdgeID, "e_start_switch")
    }

    func testLeafNodeHasNilActiveEdge() throws {
        let engine = RouteEngine()
        try engine.buildGraph(from: makeLevelData())

        let graph = try XCTUnwrap(engine.runtimeGraph)
        let destinationNode = try XCTUnwrap(graph.nodesByID["destination"])
        XCTAssertNil(destinationNode.activeOutgoingEdgeID)
    }

    func testRotateSwitchNodeCyclesThroughValidOutgoingEdges() throws {
        let engine = RouteEngine()
        try engine.buildGraph(from: makeLevelData())

        XCTAssertTrue(engine.rotateSwitchNode(nodeID: "switch"))
        var graph = try XCTUnwrap(engine.runtimeGraph)
        var switchNode = try XCTUnwrap(graph.nodesByID["switch"])
        XCTAssertEqual(switchNode.activeOutgoingEdgeID, "e_switch_dead_end")

        XCTAssertTrue(engine.rotateSwitchNode(nodeID: "switch"))
        graph = try XCTUnwrap(engine.runtimeGraph)
        switchNode = try XCTUnwrap(graph.nodesByID["switch"])
        XCTAssertEqual(switchNode.activeOutgoingEdgeID, "e_switch_destination")

        XCTAssertTrue(engine.rotateSwitchNode(nodeID: "switch"))
        graph = try XCTUnwrap(engine.runtimeGraph)
        switchNode = try XCTUnwrap(graph.nodesByID["switch"])
        XCTAssertEqual(switchNode.activeOutgoingEdgeID, "e_switch_package")
    }

    func testRotateSwitchNodeReturnsFalseForNonSwitchNode() throws {
        let engine = RouteEngine()
        try engine.buildGraph(from: makeLevelData())

        XCTAssertFalse(engine.rotateSwitchNode(nodeID: "start"))
        XCTAssertFalse(engine.rotateSwitchNode(nodeID: "destination"))
    }

    func testRotateSwitchNodeReturnsFalseForUnknownNode() throws {
        let engine = RouteEngine()
        try engine.buildGraph(from: makeLevelData())

        XCTAssertFalse(engine.rotateSwitchNode(nodeID: "unknown"))
    }

    func testRotateSwitchNodeReturnsFalseWhenOnlyOneOutgoingEdgeIsValidAndNormalizesActiveEdge() throws {
        let nodes = [
            RouteNode(id: "start", x: 0, y: 0, outgoingEdgeIDs: ["invalid", "valid"]),
            RouteNode(id: "mid", x: 1, y: 0, outgoingEdgeIDs: []),
            RouteNode(id: "end", x: 2, y: 0, outgoingEdgeIDs: [])
        ]
        let edges = [
            RouteEdge(id: "valid", fromNodeID: "start", toNodeID: "mid"),
            RouteEdge(id: "invalid", fromNodeID: "mid", toNodeID: "end")
        ]
        let level = LevelData(
            id: "single_valid_outgoing",
            name: "Single Valid Outgoing",
            graph: RouteGraph(nodes: nodes, edges: edges),
            startNodeID: "start",
            packageNodeID: "start",
            destinationNodeID: "mid",
            timeLimitSeconds: 10,
            parTaps: 1
        )
        let engine = RouteEngine()
        try engine.buildGraph(from: level)

        var graph = try XCTUnwrap(engine.runtimeGraph)
        var startNode = try XCTUnwrap(graph.nodesByID["start"])
        XCTAssertEqual(startNode.activeOutgoingEdgeID, "invalid")

        XCTAssertFalse(engine.rotateSwitchNode(nodeID: "start"))

        graph = try XCTUnwrap(engine.runtimeGraph)
        startNode = try XCTUnwrap(graph.nodesByID["start"])
        XCTAssertEqual(startNode.activeOutgoingEdgeID, "valid")
    }

    func testRotateSwitchNodeReturnsFalseWhenNoOutgoingEdgeIsValidAndClearsActiveEdge() throws {
        let nodes = [
            RouteNode(id: "start", x: 0, y: 0, outgoingEdgeIDs: ["invalid"]),
            RouteNode(id: "mid", x: 1, y: 0, outgoingEdgeIDs: []),
            RouteNode(id: "end", x: 2, y: 0, outgoingEdgeIDs: [])
        ]
        let edges = [
            RouteEdge(id: "invalid", fromNodeID: "mid", toNodeID: "end")
        ]
        let level = LevelData(
            id: "no_valid_outgoing",
            name: "No Valid Outgoing",
            graph: RouteGraph(nodes: nodes, edges: edges),
            startNodeID: "start",
            packageNodeID: "start",
            destinationNodeID: "end",
            timeLimitSeconds: 10,
            parTaps: 1
        )
        let engine = RouteEngine()
        try engine.buildGraph(from: level)

        var graph = try XCTUnwrap(engine.runtimeGraph)
        var startNode = try XCTUnwrap(graph.nodesByID["start"])
        XCTAssertEqual(startNode.activeOutgoingEdgeID, "invalid")

        XCTAssertFalse(engine.rotateSwitchNode(nodeID: "start"))

        graph = try XCTUnwrap(engine.runtimeGraph)
        startNode = try XCTUnwrap(graph.nodesByID["start"])
        XCTAssertNil(startNode.activeOutgoingEdgeID)
    }

    // MARK: - Invalid graph data

    func testBuildGraphThrowsForMissingPackageNode() {
        let engine = RouteEngine()
        let level = makeLevelData(packageNodeID: "nonexistent")

        XCTAssertThrowsError(try engine.buildGraph(from: level)) { error in
            guard case RouteEngineError.missingPackageNode(let id) = error else {
                return XCTFail("Expected missingPackageNode, got \(error)")
            }
            XCTAssertEqual(id, "nonexistent")
        }
    }

    func testBuildGraphThrowsForMissingDestinationNode() {
        let engine = RouteEngine()
        let level = makeLevelData(destinationNodeID: "nonexistent")

        XCTAssertThrowsError(try engine.buildGraph(from: level)) { error in
            guard case RouteEngineError.missingDestinationNode(let id) = error else {
                return XCTFail("Expected missingDestinationNode, got \(error)")
            }
            XCTAssertEqual(id, "nonexistent")
        }
    }

    func testBuildGraphThrowsForEdgeWithUnknownFromNode() {
        let engine = RouteEngine()
        let nodes = [
            RouteNode(id: "a", x: 0, y: 0, outgoingEdgeIDs: ["e1"]),
            RouteNode(id: "b", x: 1, y: 0, outgoingEdgeIDs: [])
        ]
        let edges = [RouteEdge(id: "e1", fromNodeID: "unknown", toNodeID: "b")]
        let level = LevelData(
            id: "bad",
            name: "Bad",
            graph: RouteGraph(nodes: nodes, edges: edges),
            startNodeID: "a",
            packageNodeID: "a",
            destinationNodeID: "b",
            timeLimitSeconds: 10,
            parTaps: 1
        )

        XCTAssertThrowsError(try engine.buildGraph(from: level)) { error in
            guard case RouteEngineError.edgeReferencesUnknownNode(let edgeID, let nodeID) = error else {
                return XCTFail("Expected edgeReferencesUnknownNode, got \(error)")
            }
            XCTAssertEqual(edgeID, "e1")
            XCTAssertEqual(nodeID, "unknown")
        }
    }

    func testBuildGraphThrowsForEdgeWithUnknownToNode() {
        let engine = RouteEngine()
        let nodes = [
            RouteNode(id: "a", x: 0, y: 0, outgoingEdgeIDs: ["e1"]),
            RouteNode(id: "b", x: 1, y: 0, outgoingEdgeIDs: [])
        ]
        let edges = [RouteEdge(id: "e1", fromNodeID: "a", toNodeID: "unknown")]
        let level = LevelData(
            id: "bad",
            name: "Bad",
            graph: RouteGraph(nodes: nodes, edges: edges),
            startNodeID: "a",
            packageNodeID: "a",
            destinationNodeID: "b",
            timeLimitSeconds: 10,
            parTaps: 1
        )

        XCTAssertThrowsError(try engine.buildGraph(from: level)) { error in
            guard case RouteEngineError.edgeReferencesUnknownNode(let edgeID, let nodeID) = error else {
                return XCTFail("Expected edgeReferencesUnknownNode, got \(error)")
            }
            XCTAssertEqual(edgeID, "e1")
            XCTAssertEqual(nodeID, "unknown")
        }
    }

    func testRuntimeGraphIsNilBeforeBuild() {
        let engine = RouteEngine()
        XCTAssertNil(engine.runtimeGraph)
    }

    func testDeliveryDotIsNilBeforeBuild() {
        let engine = RouteEngine()
        XCTAssertNil(engine.deliveryDot)
    }

    func testBuildGraphThrowsForMissingStartNode() {
        let engine = RouteEngine()
        let nodes = [
            RouteNode(id: "a", x: 0, y: 0, outgoingEdgeIDs: ["e1"]),
            RouteNode(id: "b", x: 1, y: 0, outgoingEdgeIDs: [])
        ]
        let edges = [RouteEdge(id: "e1", fromNodeID: "a", toNodeID: "b")]
        let level = LevelData(
            id: "cyclic",
            name: "Cyclic",
            graph: RouteGraph(nodes: nodes, edges: edges),
            startNodeID: "missing",
            packageNodeID: "a",
            destinationNodeID: "b",
            timeLimitSeconds: 10,
            parTaps: 1
        )

        XCTAssertThrowsError(try engine.buildGraph(from: level)) { error in
            guard case RouteEngineError.missingStartNode(let id) = error else {
                return XCTFail("Expected missingStartNode, got \(error)")
            }
            XCTAssertEqual(id, "missing")
        }
    }

    func testBuildGraphClearsRuntimeStateWhenBuildFails() throws {
        let engine = RouteEngine()
        try engine.buildGraph(from: makeLevelData())
        XCTAssertNotNil(engine.runtimeGraph)
        XCTAssertNotNil(engine.deliveryDot)

        let invalidLevel = makeLevelData(startNodeID: "missing")

        XCTAssertThrowsError(try engine.buildGraph(from: invalidLevel))
        XCTAssertNil(engine.runtimeGraph)
        XCTAssertNil(engine.deliveryDot)
    }

    // MARK: - Switch direction routing (STORY-013)

    func testDotFollowsRotatedSwitchDirectionOnArrival() throws {
        let engine = RouteEngine(dotSpeed: 2)
        try engine.buildGraph(from: makeLevelData())

        // Rotate switch: default e_switch_package -> e_switch_dead_end
        engine.rotateSwitchNode(nodeID: "switch")
        XCTAssertTrue(engine.startDotMovement())

        // Distance = 2 * 0.6 = 1.2 units.
        // e_start_switch length = 1.0, so dot reaches switch with 0.2 units left.
        // At switch, active edge is now e_switch_dead_end.
        engine.updateDot(deltaTime: 0.6)

        let dot = try XCTUnwrap(engine.deliveryDot)
        XCTAssertEqual(dot.currentEdgeID, "e_switch_dead_end")

        let graph = try XCTUnwrap(engine.runtimeGraph)
        // e_switch_dead_end length = sqrt(2) ≈ 1.4142; progress = 0.2 / sqrt(2) ≈ 0.1414
        let expectedProgress = 0.2 / sqrt(2.0)
        XCTAssertEqual(dot.progressAlongEdge, expectedProgress, accuracy: 0.0001)
        let expectedX = 1.0 + (1.0 * expectedProgress)  // switch.x + (dead_end.x - switch.x) * progress
        let expectedY = 0.0 + (-1.0 * expectedProgress) // switch.y + (dead_end.y - switch.y) * progress
        assertPosition(
            dot.runtimePosition(in: graph),
            equals: DeliveryDotPosition(x: expectedX, y: expectedY)
        )
    }

    func testDotDoesNotChangeCourseWhenSwitchIsRotatedMidEdge() throws {
        let engine = RouteEngine(dotSpeed: 1)
        try engine.buildGraph(from: makeLevelData())
        XCTAssertTrue(engine.startDotMovement())

        // Move dot halfway along e_start_switch (length 1.0).
        engine.updateDot(deltaTime: 0.5)

        let dotBefore = try XCTUnwrap(engine.deliveryDot)
        XCTAssertEqual(dotBefore.currentEdgeID, "e_start_switch")
        XCTAssertEqual(dotBefore.progressAlongEdge, 0.5, accuracy: 0.0001)

        // Rotate the switch while dot is mid-edge.
        engine.rotateSwitchNode(nodeID: "switch")

        // The current edge must not change.
        let dotAfter = try XCTUnwrap(engine.deliveryDot)
        XCTAssertEqual(dotAfter.currentEdgeID, "e_start_switch", "Edge must not change mid-traversal")
        XCTAssertEqual(dotAfter.progressAlongEdge, 0.5, accuracy: 0.0001)
    }

    func testSwitchRotationAffectsNextVisitToSwitchNode() throws {
        let engine = RouteEngine(dotSpeed: 1)
        try engine.buildGraph(from: makeLevelData())
        XCTAssertTrue(engine.startDotMovement())

        // Move dot past switch onto e_switch_package (first pass through switch node).
        // Distance = 1.5: 1.0 to reach switch, then 0.5 units into e_switch_package.
        engine.updateDot(deltaTime: 1.5)

        let dotMidLoop = try XCTUnwrap(engine.deliveryDot)
        XCTAssertEqual(dotMidLoop.currentEdgeID, "e_switch_package")

        // Rotate switch twice so destination is now the active direction.
        engine.rotateSwitchNode(nodeID: "switch") // -> e_switch_dead_end
        engine.rotateSwitchNode(nodeID: "switch") // -> e_switch_destination

        // Advance enough for the dot to complete the loop back to switch and then start the
        // destination edge.
        // Remaining on e_switch_package: (1 − 0.5/√2) * √2 ≈ 0.9142 units
        // e_package_return length = √2 ≈ 1.4142 units
        // Remaining after arriving at switch second time: 2.5 − (0.9142 + 1.4142) ≈ 0.1716 units
        engine.updateDot(deltaTime: 2.5)

        let dot = try XCTUnwrap(engine.deliveryDot)
        XCTAssertEqual(dot.currentEdgeID, "e_switch_destination",
                       "Dot should follow the newly active direction on its second visit to the switch")
    }

    func testWrongSwitchDirectionSendsDotToDeadEnd() throws {
        let engine = RouteEngine(dotSpeed: 4)
        try engine.buildGraph(from: makeLevelData())

        // Rotate switch to the dead-end branch.
        engine.rotateSwitchNode(nodeID: "switch") // -> e_switch_dead_end
        XCTAssertTrue(engine.startDotMovement())

        // Advance far enough to travel start -> switch -> dead_end.
        engine.updateDot(deltaTime: 2.0)

        let dot = try XCTUnwrap(engine.deliveryDot)
        XCTAssertEqual(dot.currentNodeID, "dead_end")
        XCTAssertNil(dot.currentEdgeID)
        XCTAssertTrue(engine.didHaltAtDeadEnd)
    }
}
