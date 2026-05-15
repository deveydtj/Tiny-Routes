import XCTest
@testable import TinyRoutes

final class RouteEngineTests: XCTestCase {

    // MARK: - Helpers

    /// Returns a minimal LevelData that mirrors level_001.json.
    private func makeLevelData(
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
            packageNodeID: packageNodeID,
            destinationNodeID: destinationNodeID,
            timeLimitSeconds: 45,
            parTaps: 6
        )
    }

    // MARK: - Successful build

    func testBuildGraphStoresRuntimeGraph() throws {
        let engine = RouteEngine()
        try engine.buildGraph(from: makeLevelData())

        XCTAssertNotNil(engine.runtimeGraph)
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
}
