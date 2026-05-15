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
        let position = try? XCTUnwrap(position, file: file, line: line)
        XCTAssertNotNil(position, file: file, line: line)
        XCTAssertEqual(position?.x, expected.x, accuracy: accuracy, file: file, line: line)
        XCTAssertEqual(position?.y, expected.y, accuracy: accuracy, file: file, line: line)
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

    func testUpdateDotSnapsToTargetNodeWithoutOvershooting() throws {
        let engine = RouteEngine(dotSpeed: 4)
        try engine.buildGraph(from: makeLevelData())
        XCTAssertTrue(engine.startDotMovement())

        engine.updateDot(deltaTime: 1)

        let graph = try XCTUnwrap(engine.runtimeGraph)
        let dot = try XCTUnwrap(engine.deliveryDot)
        XCTAssertEqual(dot.currentNodeID, "switch")
        XCTAssertNil(dot.currentEdgeID)
        XCTAssertEqual(dot.progressAlongEdge, 0)
        assertPosition(dot.runtimePosition(in: graph), equals: DeliveryDotPosition(x: 1, y: 0))
    }

    func testStartDotMovementReturnsFalseAtLeafNode() throws {
        let engine = RouteEngine()
        try engine.buildGraph(from: makeLevelData(startNodeID: "destination"))

        XCTAssertFalse(engine.startDotMovement())

        let dot = try XCTUnwrap(engine.deliveryDot)
        XCTAssertEqual(dot.currentNodeID, "destination")
        XCTAssertNil(dot.currentEdgeID)
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
}
