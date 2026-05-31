import XCTest
@testable import TinyRoutes

final class RouteEngineTests: XCTestCase {

    // MARK: - Helpers

    /// Returns a minimal switch-puzzle LevelData used by route-engine behavior tests.
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

    private func makeFourWayIntersectionLevelData() -> LevelData {
        let nodes = [
            RouteNode(id: "start", x: -1.0, y: 0.0, outgoingEdgeIDs: ["e_start_entry"]),
            RouteNode(id: "entry", x: -0.5, y: 0.0, outgoingEdgeIDs: ["e_entry_central"]),
            RouteNode(
                id: "central_switch",
                x: 0.0,
                y: 0.0,
                outgoingEdgeIDs: [
                    "e_central_dead_end",
                    "e_central_package",
                    "e_central_destination",
                    "e_central_side_branch"
                ]
            ),
            RouteNode(id: "dead_end", x: 0.0, y: 0.75, outgoingEdgeIDs: []),
            RouteNode(id: "package", x: 0.0, y: -0.75, outgoingEdgeIDs: ["e_package_return"]),
            RouteNode(id: "return_node", x: -0.5, y: -0.75, outgoingEdgeIDs: ["e_return_central"]),
            RouteNode(id: "destination", x: 0.95, y: 0.0, outgoingEdgeIDs: []),
            RouteNode(id: "side_branch", x: -0.45, y: 0.62, outgoingEdgeIDs: [])
        ]
        let edges = [
            RouteEdge(id: "e_start_entry", fromNodeID: "start", toNodeID: "entry"),
            RouteEdge(id: "e_entry_central", fromNodeID: "entry", toNodeID: "central_switch"),
            RouteEdge(id: "e_central_dead_end", fromNodeID: "central_switch", toNodeID: "dead_end"),
            RouteEdge(id: "e_central_package", fromNodeID: "central_switch", toNodeID: "package"),
            RouteEdge(id: "e_package_return", fromNodeID: "package", toNodeID: "return_node"),
            RouteEdge(id: "e_return_central", fromNodeID: "return_node", toNodeID: "central_switch"),
            RouteEdge(id: "e_central_destination", fromNodeID: "central_switch", toNodeID: "destination"),
            RouteEdge(id: "e_central_side_branch", fromNodeID: "central_switch", toNodeID: "side_branch")
        ]
        return LevelData(
            id: "four_way_intersection",
            name: "Four-Way Intersection",
            graph: RouteGraph(nodes: nodes, edges: edges),
            startNodeID: "start",
            packageNodeID: "package",
            destinationNodeID: "destination",
            timeLimitSeconds: 30,
            parTaps: 2
        )
    }

    private func makeArrowDirectionFixtureLevelData() -> LevelData {
        let nodes = [
            RouteNode(id: "start", x: -2.0, y: 0.0, outgoingEdgeIDs: ["edge_0"]),
            RouteNode(id: "switch", x: 0.0, y: 0.0, outgoingEdgeIDs: ["edge_1", "edge_2", "edge_6"]),
            RouteNode(id: "left_target", x: -1.0, y: 0.0, outgoingEdgeIDs: []),
            RouteNode(id: "node", x: 1.0, y: 0.0, outgoingEdgeIDs: ["edge_3", "edge_5"]),
            RouteNode(id: "switch_down_target", x: 1.0, y: -1.0, outgoingEdgeIDs: []),
            RouteNode(id: "node_down_target", x: 1.0, y: -1.5, outgoingEdgeIDs: [])
        ]
        let edges = [
            RouteEdge(id: "edge_0", fromNodeID: "start", toNodeID: "switch"),
            RouteEdge(id: "edge_1", fromNodeID: "switch", toNodeID: "left_target"),
            RouteEdge(id: "edge_2", fromNodeID: "switch", toNodeID: "node"),
            RouteEdge(id: "edge_6", fromNodeID: "switch", toNodeID: "switch_down_target", roadShape: .verticalFirst),
            RouteEdge(id: "edge_3", fromNodeID: "node", toNodeID: "switch"),
            RouteEdge(id: "edge_5", fromNodeID: "node", toNodeID: "node_down_target")
        ]
        return LevelData(
            id: "arrow_direction_fixture",
            name: "Arrow Direction Fixture",
            graph: RouteGraph(nodes: nodes, edges: edges),
            startNodeID: "start",
            packageNodeID: "switch_down_target",
            destinationNodeID: "node_down_target",
            timeLimitSeconds: 20,
            parTaps: 0
        )
    }

    private func loadSwitchArrowBugLevelFixture() throws -> LevelData {
        let url = switchArrowBugFixtureURL(named: "level_028_style_switch_arrow_mismatch.json")
        let data = try Data(contentsOf: url)
        return try JSONDecoder().decode(LevelData.self, from: data)
    }

    private func loadSwitchArrowBugSolutionFixture() throws -> LevelSolutionScript {
        let url = switchArrowBugFixtureURL(named: "level_028_style_switch_arrow_mismatch.solution.json")
        let data = try Data(contentsOf: url)
        return try JSONDecoder().decode(LevelSolutionScript.self, from: data)
    }

    private func switchArrowBugFixtureURL(named filename: String) -> URL {
        URL(fileURLWithPath: #filePath)
            .deletingLastPathComponent()
            .appendingPathComponent("Fixtures")
            .appendingPathComponent("SwitchArrowBug")
            .appendingPathComponent(filename)
    }

    private func makeRuntimeGraphForSwitchClassification(
        validOutgoingCount: Int,
        includeInvalidListedEdgeIDs: Bool = false
    ) -> (RuntimeRouteGraph, RuntimeRouteNode) {
        var outgoingEdgeIDs = (0..<validOutgoingCount).map { "e_valid_\($0)" }
        if includeInvalidListedEdgeIDs {
            outgoingEdgeIDs.append(contentsOf: ["e_missing", "e_wrong_source"])
        }

        let node = RuntimeRouteNode(
            id: "node",
            x: 0,
            y: 0,
            outgoingEdgeIDs: outgoingEdgeIDs,
            activeOutgoingEdgeID: outgoingEdgeIDs.first
        )
        var edgesByID: [String: RuntimeRouteEdge] = [:]
        for index in 0..<validOutgoingCount {
            edgesByID["e_valid_\(index)"] = RuntimeRouteEdge(
                id: "e_valid_\(index)",
                fromNodeID: "node",
                toNodeID: "target_\(index)",
                roadPath: RoadPath.make(from: RoadPoint(x: 0, y: 0), to: RoadPoint(x: Double(index + 1), y: 0))
            )
        }
        if includeInvalidListedEdgeIDs {
            edgesByID["e_wrong_source"] = RuntimeRouteEdge(
                id: "e_wrong_source",
                fromNodeID: "other",
                toNodeID: "target_wrong",
                roadPath: RoadPath.make(from: RoadPoint(x: 0, y: 0), to: RoadPoint(x: 1, y: 1))
            )
        }

        return (RuntimeRouteGraph(nodesByID: ["node": node], edgesByID: edgesByID), node)
    }

    private func makeSwitchRuntimeGraphForTarget(
        _ target: RoadPoint,
        roadShape: RoadShape
    ) -> (RuntimeRouteGraph, RuntimeRouteNode) {
        let switchNode = RuntimeRouteNode(
            id: "switch",
            x: 0,
            y: 0,
            outgoingEdgeIDs: ["e_switch_target", "e_switch_alternate"],
            activeOutgoingEdgeID: "e_switch_target"
        )
        let targetNode = RuntimeRouteNode(
            id: "target",
            x: target.x,
            y: target.y,
            outgoingEdgeIDs: [],
            activeOutgoingEdgeID: nil
        )
        let alternateNode = RuntimeRouteNode(
            id: "alternate",
            x: 2,
            y: 0,
            outgoingEdgeIDs: [],
            activeOutgoingEdgeID: nil
        )
        let graph = RuntimeRouteGraph(
            nodesByID: [
                switchNode.id: switchNode,
                targetNode.id: targetNode,
                alternateNode.id: alternateNode
            ],
            edgesByID: [
                "e_switch_target": RuntimeRouteEdge(
                    id: "e_switch_target",
                    fromNodeID: switchNode.id,
                    toNodeID: targetNode.id,
                    roadPath: RoadPath.make(
                        from: RoadPoint(x: switchNode.x, y: switchNode.y),
                        to: target,
                        shape: roadShape
                    )
                ),
                "e_switch_alternate": RuntimeRouteEdge(
                    id: "e_switch_alternate",
                    fromNodeID: switchNode.id,
                    toNodeID: alternateNode.id,
                    roadPath: RoadPath.make(
                        from: RoadPoint(x: switchNode.x, y: switchNode.y),
                        to: RoadPoint(x: alternateNode.x, y: alternateNode.y)
                    )
                )
            ]
        )

        return (graph, switchNode)
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

    private func assertRoadPoint(
        _ point: RoadPoint?,
        equals expected: RoadPoint,
        accuracy: Double = 0.0001,
        file: StaticString = #filePath,
        line: UInt = #line
    ) {
        guard let point else {
            return XCTFail("Expected a road point.", file: file, line: line)
        }

        XCTAssertEqual(point.x, expected.x, accuracy: accuracy, file: file, line: line)
        XCTAssertEqual(point.y, expected.y, accuracy: accuracy, file: file, line: line)
    }

    private func makeBoardLayout(pointsByNodeID: [String: CGPoint]) -> BoardLayout {
        BoardLayout(pointsByNodeID: pointsByNodeID)
    }

    private func roadLength(for edgeID: String, in graph: RuntimeRouteGraph) throws -> Double {
        try XCTUnwrap(graph.edgesByID[edgeID]).roadPath.totalLength
    }

    // MARK: - Road geometry

    func testRoadPathGenerationCreatesHorizontalStraightEdge() {
        let path = RoadPath.make(from: RoadPoint(x: 0, y: 0), to: RoadPoint(x: 2, y: 0))

        XCTAssertEqual(path.segments.count, 1)
        XCTAssertEqual(path.segments.first?.kind, .straight)
        XCTAssertEqual(path.totalLength, 2, accuracy: 0.0001)
        XCTAssertEqual(path.point(atProgress: 0.5), RoadPoint(x: 1, y: 0))
        XCTAssertEqual(path.tangent(atProgress: 0), RoadVector(x: 1, y: 0))
    }

    func testRoadPathGenerationCreatesVerticalStraightEdge() {
        let path = RoadPath.make(from: RoadPoint(x: 0, y: 0), to: RoadPoint(x: 0, y: 2))

        XCTAssertEqual(path.segments.count, 1)
        XCTAssertEqual(path.segments.first?.kind, .straight)
        XCTAssertEqual(path.totalLength, 2, accuracy: 0.0001)
        XCTAssertEqual(path.point(atProgress: 0.5), RoadPoint(x: 0, y: 1))
        XCTAssertEqual(path.tangent(atProgress: 0), RoadVector(x: 0, y: 1))
    }

    func testRoadPathGenerationDefaultsDiagonalEdgeToHorizontalFirstElbow() {
        let path = RoadPath.make(from: RoadPoint(x: 0, y: 0), to: RoadPoint(x: 1, y: 1))

        XCTAssertEqual(path.segments.map(\.kind), [.straight, .quarterTurn, .straight])
        assertRoadPoint(path.segments.first?.start, equals: RoadPoint(x: 0, y: 0))
        assertRoadPoint(path.segments.first?.end, equals: RoadPoint(x: 0.82, y: 0))
        assertRoadPoint(path.segments.last?.start, equals: RoadPoint(x: 1, y: 0.18))
        assertRoadPoint(path.segments.last?.end, equals: RoadPoint(x: 1, y: 1))
        XCTAssertEqual(path.tangent(atProgress: 0), RoadVector(x: 1, y: 0))
    }

    func testRoadPathGenerationHonorsExplicitVerticalFirstElbow() {
        let path = RoadPath.make(
            from: RoadPoint(x: 0, y: 0),
            to: RoadPoint(x: 1, y: 1),
            shape: .verticalFirst
        )

        XCTAssertEqual(path.segments.map(\.kind), [.straight, .quarterTurn, .straight])
        assertRoadPoint(path.segments.first?.start, equals: RoadPoint(x: 0, y: 0))
        assertRoadPoint(path.segments.first?.end, equals: RoadPoint(x: 0, y: 0.82))
        assertRoadPoint(path.segments.last?.start, equals: RoadPoint(x: 0.18, y: 1))
        assertRoadPoint(path.segments.last?.end, equals: RoadPoint(x: 1, y: 1))
        XCTAssertEqual(path.tangent(atProgress: 0), RoadVector(x: 0, y: 1))
    }

    func testRoadPathConnectorInfersPerpendicularTurnBetweenEdges() throws {
        let incoming = RoadPath.make(from: RoadPoint(x: 0, y: 0), to: RoadPoint(x: 1, y: 0))
        let outgoing = RoadPath.make(from: RoadPoint(x: 1, y: 0), to: RoadPoint(x: 1, y: 1))

        let connector = try XCTUnwrap(
            RoadPath.makePerpendicularConnector(
                at: RoadPoint(x: 1, y: 0),
                from: incoming,
                to: outgoing
            )
        )

        XCTAssertEqual(connector.entryDistanceAlongIncomingPath, 0.82, accuracy: 0.0001)
        XCTAssertEqual(connector.exitDistanceAlongOutgoingPath, 0.18, accuracy: 0.0001)
        XCTAssertEqual(connector.roadPath.segments.map(\.kind), [.smoothTurn])
        assertRoadPoint(connector.roadPath.segments.first?.start, equals: RoadPoint(x: 0.82, y: 0))
        assertRoadPoint(connector.roadPath.segments.first?.end, equals: RoadPoint(x: 1, y: 0.18))

        let startTangent = connector.roadPath.tangent(atProgress: 0)
        XCTAssertEqual(startTangent.x, 1, accuracy: 0.0001)
        XCTAssertEqual(startTangent.y, 0, accuracy: 0.0001)

        let endTangent = connector.roadPath.tangent(atProgress: 1)
        XCTAssertEqual(endTangent.x, 0, accuracy: 0.0001)
        XCTAssertEqual(endTangent.y, 1, accuracy: 0.0001)
    }

    func testRoadPathConnectorIgnoresStraightThroughEdges() {
        let incoming = RoadPath.make(from: RoadPoint(x: 0, y: 0), to: RoadPoint(x: 1, y: 0))
        let outgoing = RoadPath.make(from: RoadPoint(x: 1, y: 0), to: RoadPoint(x: 2, y: 0))

        let connector = RoadPath.makePerpendicularConnector(
            at: RoadPoint(x: 1, y: 0),
            from: incoming,
            to: outgoing
        )

        XCTAssertNil(connector)
    }

    func testRoadPathConnectorTrimsPastTinyTerminalJogs() throws {
        let node = RoadPoint(x: -0.8056, y: -0.5667)
        let incoming = RoadPath.make(
            from: RoadPoint(x: 0.0111, y: -0.5278),
            to: node,
            shape: .horizontalFirst
        )
        let outgoing = RoadPath.make(
            from: node,
            to: RoadPoint(x: -0.7667, y: 0.2889),
            shape: .horizontalFirst
        )

        let connector = try XCTUnwrap(
            RoadPath.makePerpendicularConnector(
                at: node,
                from: incoming,
                to: outgoing
            )
        )

        let segment = try XCTUnwrap(connector.roadPath.segments.first)
        XCTAssertEqual(segment.kind, .smoothTurn)
        XCTAssertEqual(connector.entryDistanceAlongIncomingPath, incoming.totalLength - 0.18, accuracy: 0.0001)
        XCTAssertEqual(connector.exitDistanceAlongOutgoingPath, 0.18, accuracy: 0.0001)
        assertRoadPoint(segment.start, equals: incoming.point(atDistance: connector.entryDistanceAlongIncomingPath))
        assertRoadPoint(segment.end, equals: outgoing.point(atDistance: connector.exitDistanceAlongOutgoingPath))
        XCTAssertGreaterThan(segment.start.x, node.x)
        XCTAssertGreaterThan(segment.end.y, node.y)
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
        let graph = try XCTUnwrap(engine.runtimeGraph)
        let expectedProgress = 1 / (try roadLength(for: "e_switch_package", in: graph))
        XCTAssertEqual(dot.progressAlongEdge, expectedProgress, accuracy: 0.0001)
    }

    func testUpdateDotUsesSmoothTransitionBetweenPerpendicularRoads() throws {
        let nodes = [
            RouteNode(id: "start", x: 0, y: 0, outgoingEdgeIDs: ["to_corner"]),
            RouteNode(id: "corner", x: 1, y: 0, outgoingEdgeIDs: ["to_end"]),
            RouteNode(id: "end", x: 1, y: 1, outgoingEdgeIDs: [])
        ]
        let edges = [
            RouteEdge(id: "to_corner", fromNodeID: "start", toNodeID: "corner"),
            RouteEdge(id: "to_end", fromNodeID: "corner", toNodeID: "end")
        ]
        let level = LevelData(
            id: "smooth_corner",
            name: "Smooth Corner",
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

        engine.updateDot(deltaTime: 0.9)

        let graph = try XCTUnwrap(engine.runtimeGraph)
        let dot = try XCTUnwrap(engine.deliveryDot)
        let transition = try XCTUnwrap(dot.transition)
        XCTAssertNil(dot.currentEdgeID)
        XCTAssertEqual(transition.nodeID, "corner")
        XCTAssertEqual(transition.toEdgeID, "to_end")
        XCTAssertGreaterThan(transition.progressAlongTransition, 0)
        XCTAssertLessThan(transition.progressAlongTransition, 1)
        XCTAssertEqual(transition.roadPath.tangent(atProgress: 0).x, 1, accuracy: 0.0001)
        XCTAssertEqual(transition.roadPath.tangent(atProgress: 0).y, 0, accuracy: 0.0001)
        XCTAssertEqual(transition.roadPath.tangent(atProgress: 1).x, 0, accuracy: 0.0001)
        XCTAssertEqual(transition.roadPath.tangent(atProgress: 1).y, 1, accuracy: 0.0001)
        let position = try XCTUnwrap(dot.runtimePosition(in: graph))
        XCTAssertGreaterThan(position.x, 0.82)
        XCTAssertLessThan(position.x, 1)
        XCTAssertGreaterThan(position.y, 0)
        XCTAssertLessThan(position.y, 0.18)
    }

    func testUpdateDotDoesNotSmoothThroughSwitchNodes() throws {
        let nodes = [
            RouteNode(id: "start", x: 0, y: 0, outgoingEdgeIDs: ["to_switch"]),
            RouteNode(id: "switch", x: 1, y: 0, outgoingEdgeIDs: ["to_end", "to_dead_end"]),
            RouteNode(id: "end", x: 1, y: 1, outgoingEdgeIDs: []),
            RouteNode(id: "dead_end", x: 2, y: 0, outgoingEdgeIDs: [])
        ]
        let edges = [
            RouteEdge(id: "to_switch", fromNodeID: "start", toNodeID: "switch"),
            RouteEdge(id: "to_end", fromNodeID: "switch", toNodeID: "end"),
            RouteEdge(id: "to_dead_end", fromNodeID: "switch", toNodeID: "dead_end")
        ]
        let level = LevelData(
            id: "switch_corner",
            name: "Switch Corner",
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

        engine.updateDot(deltaTime: 0.9)

        let dot = try XCTUnwrap(engine.deliveryDot)
        XCTAssertNil(dot.transition)
        XCTAssertEqual(dot.currentEdgeID, "to_switch")
        XCTAssertEqual(dot.progressAlongEdge, 0.9, accuracy: 0.0001)
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
            RouteNode(id: "dead", x: 2, y: 0, outgoingEdgeIDs: []),
            RouteNode(id: "goal", x: 3, y: 0, outgoingEdgeIDs: [])
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
            destinationNodeID: "goal",
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
        XCTAssertEqual(engine.levelOutcome, .failed(reason: .deadEnd))
    }

    func testUpdateDotMarksDidHaltAtDeadEndFalseWhenStillMoving() throws {
        let engine = RouteEngine(dotSpeed: 1)
        try engine.buildGraph(from: makeLevelData())
        XCTAssertTrue(engine.startDotMovement())

        engine.updateDot(deltaTime: 0.25)

        XCTAssertFalse(engine.didHaltAtDeadEnd)
    }

    func testRouteBoardTapTargetResolverReturnsNearestSwitchNodeWithinRadius() throws {
        let level = makeLevelData()
        let engine = RouteEngine()
        try engine.buildGraph(from: level)

        let graph = try XCTUnwrap(engine.runtimeGraph)
        let resolver = RouteBoardTapTargetResolver(
            runtimeGraph: graph,
            layout: makeBoardLayout(
                pointsByNodeID: [
                    "start": CGPoint(x: 10, y: 20),
                    "switch": CGPoint(x: 50, y: 20),
                    "package": CGPoint(x: 90, y: 10),
                    "dead_end": CGPoint(x: 90, y: 40),
                    "destination": CGPoint(x: 130, y: 20)
                ]
            ),
            tapRadius: 30
        )

        XCTAssertEqual(resolver.nodeID(at: CGPoint(x: 52, y: 22)), "switch")
    }

    func testRouteBoardTapTargetResolverIdentifiesFourWaySwitch() throws {
        let engine = RouteEngine()
        try engine.buildGraph(from: makeFourWayIntersectionLevelData())

        let graph = try XCTUnwrap(engine.runtimeGraph)
        let resolver = RouteBoardTapTargetResolver(
            runtimeGraph: graph,
            layout: makeBoardLayout(
                pointsByNodeID: [
                    "start": CGPoint(x: 0, y: 20),
                    "entry": CGPoint(x: 30, y: 20),
                    "central_switch": CGPoint(x: 60, y: 20),
                    "dead_end": CGPoint(x: 60, y: 0),
                    "package": CGPoint(x: 60, y: 40),
                    "return_node": CGPoint(x: 30, y: 40),
                    "destination": CGPoint(x: 100, y: 20),
                    "side_branch": CGPoint(x: 30, y: 0)
                ]
            ),
            tapRadius: 20
        )

        XCTAssertEqual(resolver.nodeID(at: CGPoint(x: 61, y: 19)), "central_switch")
    }

    func testRouteBoardTapTargetResolverIgnoresNonSwitchNodes() throws {
        let level = makeLevelData()
        let engine = RouteEngine()
        try engine.buildGraph(from: level)

        let graph = try XCTUnwrap(engine.runtimeGraph)
        let resolver = RouteBoardTapTargetResolver(
            runtimeGraph: graph,
            layout: makeBoardLayout(
                pointsByNodeID: [
                    "start": CGPoint(x: 10, y: 20),
                    "switch": CGPoint(x: 50, y: 20),
                    "package": CGPoint(x: 90, y: 10),
                    "dead_end": CGPoint(x: 90, y: 40),
                    "destination": CGPoint(x: 130, y: 20)
                ]
            ),
            tapRadius: 20
        )

        XCTAssertNil(resolver.nodeID(at: CGPoint(x: 130, y: 20)))
        XCTAssertNil(resolver.nodeID(at: CGPoint(x: 10, y: 20)))
    }

    func testRouteBoardTapTargetResolverReturnsNilOutsideTapRadius() throws {
        let level = makeLevelData()
        let engine = RouteEngine()
        try engine.buildGraph(from: level)

        let graph = try XCTUnwrap(engine.runtimeGraph)
        let resolver = RouteBoardTapTargetResolver(
            runtimeGraph: graph,
            layout: makeBoardLayout(
                pointsByNodeID: [
                    "start": CGPoint(x: 10, y: 20),
                    "switch": CGPoint(x: 50, y: 20),
                    "package": CGPoint(x: 90, y: 10),
                    "dead_end": CGPoint(x: 90, y: 40),
                    "destination": CGPoint(x: 130, y: 20)
                ]
            ),
            tapRadius: 12
        )

        XCTAssertNil(resolver.nodeID(at: CGPoint(x: 75, y: 20)))
    }

    func testDirectionalArrowTransformMirrorsLeftFacingArrow() {
        let transform = DirectionalArrowTransform(angle: .pi)

        XCTAssertEqual(transform.xScale, -1)
        XCTAssertEqual(transform.rotationAngle, 0, accuracy: 0.0001)
    }

    func testDirectionalArrowTransformKeepsRightFacingArrowUnflipped() {
        let transform = DirectionalArrowTransform(angle: 0)

        XCTAssertEqual(transform.xScale, 1)
        XCTAssertEqual(transform.rotationAngle, 0, accuracy: 0.0001)
    }

    func testDirectionalArrowTransformKeepsVerticalArrowsRotated() {
        let upTransform = DirectionalArrowTransform(angle: -.pi / 2)
        let downTransform = DirectionalArrowTransform(angle: .pi / 2)

        XCTAssertEqual(upTransform.xScale, 1)
        XCTAssertEqual(upTransform.rotationAngle, -.pi / 2, accuracy: 0.0001)
        XCTAssertEqual(downTransform.xScale, 1)
        XCTAssertEqual(downTransform.rotationAngle, .pi / 2, accuracy: 0.0001)
    }

    func testSwitchArrowDirectionUsesStraightHorizontalRoadStart() throws {
        let rightPath = RoadPath.make(from: RoadPoint(x: 0, y: 0), to: RoadPoint(x: 1, y: 0))
        let leftPath = RoadPath.make(from: RoadPoint(x: 0, y: 0), to: RoadPoint(x: -1, y: 0))

        let rightAngle = try XCTUnwrap(SwitchArrowDirectionResolver.directionAngleForRoadPathStart(rightPath))
        let leftAngle = try XCTUnwrap(SwitchArrowDirectionResolver.directionAngleForRoadPathStart(leftPath))

        XCTAssertEqual(rightAngle, 0, accuracy: 0.0001)
        XCTAssertEqual(leftAngle, .pi, accuracy: 0.0001)
    }

    func testSwitchArrowDirectionUsesStraightVerticalRoadStart() throws {
        let upPath = RoadPath.make(from: RoadPoint(x: 0, y: 0), to: RoadPoint(x: 0, y: 1))
        let downPath = RoadPath.make(from: RoadPoint(x: 0, y: 0), to: RoadPoint(x: 0, y: -1))

        let upAngle = try XCTUnwrap(SwitchArrowDirectionResolver.directionAngleForRoadPathStart(upPath))
        let downAngle = try XCTUnwrap(SwitchArrowDirectionResolver.directionAngleForRoadPathStart(downPath))

        XCTAssertEqual(upAngle, -.pi / 2, accuracy: 0.0001)
        XCTAssertEqual(downAngle, .pi / 2, accuracy: 0.0001)
    }

    func testSwitchArrowDirectionUsesRoadExitDirectionForHorizontalFirstElbow() throws {
        let (graph, switchNode) = makeSwitchRuntimeGraphForTarget(
            RoadPoint(x: 1, y: 1),
            roadShape: .horizontalFirst
        )

        let angle = try XCTUnwrap(SwitchArrowDirectionResolver.activeDirectionAngle(for: switchNode, in: graph))

        XCTAssertEqual(angle, 0, accuracy: 0.0001)
    }

    func testSwitchArrowDirectionUsesRoadExitDirectionForVerticalFirstElbow() throws {
        let (graph, switchNode) = makeSwitchRuntimeGraphForTarget(
            RoadPoint(x: 1, y: 1),
            roadShape: .verticalFirst
        )

        let angle = try XCTUnwrap(SwitchArrowDirectionResolver.activeDirectionAngle(for: switchNode, in: graph))

        XCTAssertEqual(angle, -.pi / 2, accuracy: 0.0001)
    }

    func testSwitchArrowDirectionSnapsHorizontalFirstLeftExitToWest() throws {
        let (graph, switchNode) = makeSwitchRuntimeGraphForTarget(
            RoadPoint(x: -1, y: 1),
            roadShape: .horizontalFirst
        )

        let angle = try XCTUnwrap(SwitchArrowDirectionResolver.activeDirectionAngle(for: switchNode, in: graph))

        XCTAssertEqual(angle, .pi, accuracy: 0.0001)
    }

    func testSwitchArrowDirectionSnapsVerticalFirstDownExitToSouth() throws {
        let (graph, switchNode) = makeSwitchRuntimeGraphForTarget(
            RoadPoint(x: 1, y: -1),
            roadShape: .verticalFirst
        )

        let angle = try XCTUnwrap(SwitchArrowDirectionResolver.activeDirectionAngle(for: switchNode, in: graph))

        XCTAssertEqual(angle, .pi / 2, accuracy: 0.0001)
    }

    func testActiveOutgoingEdgeChangesArrowDirectionAfterRotation() throws {
        let switchNode = RuntimeRouteNode(
            id: "switch",
            x: 0,
            y: 0,
            outgoingEdgeIDs: ["e_switch_east", "e_switch_north"],
            activeOutgoingEdgeID: "e_switch_east"
        )
        let rotatedSwitchNode = RuntimeRouteNode(
            id: "switch",
            x: 0,
            y: 0,
            outgoingEdgeIDs: ["e_switch_east", "e_switch_north"],
            activeOutgoingEdgeID: "e_switch_north"
        )
        let eastNode = RuntimeRouteNode(id: "east", x: 1, y: 0, outgoingEdgeIDs: [], activeOutgoingEdgeID: nil)
        let northNode = RuntimeRouteNode(id: "north", x: 0, y: 1, outgoingEdgeIDs: [], activeOutgoingEdgeID: nil)
        let edges = [
            "e_switch_east": RuntimeRouteEdge(
                id: "e_switch_east",
                fromNodeID: switchNode.id,
                toNodeID: eastNode.id,
                roadPath: RoadPath.make(from: RoadPoint(x: 0, y: 0), to: RoadPoint(x: 1, y: 0))
            ),
            "e_switch_north": RuntimeRouteEdge(
                id: "e_switch_north",
                fromNodeID: switchNode.id,
                toNodeID: northNode.id,
                roadPath: RoadPath.make(from: RoadPoint(x: 0, y: 0), to: RoadPoint(x: 0, y: 1))
            )
        ]
        let graph = RuntimeRouteGraph(
            nodesByID: [
                switchNode.id: switchNode,
                eastNode.id: eastNode,
                northNode.id: northNode
            ],
            edgesByID: edges
        )
        let rotatedGraph = RuntimeRouteGraph(
            nodesByID: [
                rotatedSwitchNode.id: rotatedSwitchNode,
                eastNode.id: eastNode,
                northNode.id: northNode
            ],
            edgesByID: edges
        )

        let initialAngle = try XCTUnwrap(SwitchArrowDirectionResolver.activeDirectionAngle(for: switchNode, in: graph))
        let rotatedAngle = try XCTUnwrap(
            SwitchArrowDirectionResolver.activeDirectionAngle(for: rotatedSwitchNode, in: rotatedGraph)
        )

        XCTAssertEqual(initialAngle, 0, accuracy: 0.0001)
        XCTAssertEqual(rotatedAngle, -.pi / 2, accuracy: 0.0001)
    }

    func testSwitchArrowDirectionFallbackSnapsTargetVectorToCardinalAxis() throws {
        let switchNode = RuntimeRouteNode(
            id: "switch",
            x: 0,
            y: 0,
            outgoingEdgeIDs: ["e_switch_target"],
            activeOutgoingEdgeID: "e_switch_target"
        )
        let targetNode = RuntimeRouteNode(
            id: "target",
            x: 1,
            y: 1,
            outgoingEdgeIDs: [],
            activeOutgoingEdgeID: nil
        )
        let edge = RuntimeRouteEdge(
            id: "e_switch_target",
            fromNodeID: switchNode.id,
            toNodeID: targetNode.id,
            roadPath: RoadPath(segments: [])
        )
        let graph = RuntimeRouteGraph(
            nodesByID: [
                switchNode.id: switchNode,
                targetNode.id: targetNode
            ],
            edgesByID: [edge.id: edge]
        )

        let angle = SwitchArrowDirectionResolver.directionAngle(for: edge, from: switchNode, in: graph)

        XCTAssertEqual(angle, 0, accuracy: 0.0001)
    }

    func testLevel021CentralSideBranchArrowUsesHorizontalExitDirection() throws {
        let engine = RouteEngine()
        try engine.buildGraph(from: makeFourWayIntersectionLevelData())
        let graph = try XCTUnwrap(engine.runtimeGraph)
        let centralSwitch = try XCTUnwrap(graph.nodesByID["central_switch"])
        let sideBranchEdge = try XCTUnwrap(graph.edgesByID["e_central_side_branch"])

        let angle = SwitchArrowDirectionResolver.directionAngle(for: sideBranchEdge, from: centralSwitch, in: graph)

        XCTAssertEqual(angle, .pi, accuracy: 0.0001)
    }

    func testLevel022BacktrackAndDestinationArrowsUseVerticalExitDirection() throws {
        let engine = RouteEngine()
        try engine.buildGraph(from: makeArrowDirectionFixtureLevelData())
        let graph = try XCTUnwrap(engine.runtimeGraph)
        let switchNode = try XCTUnwrap(graph.nodesByID["switch"])
        let rightNode = try XCTUnwrap(graph.nodesByID["node"])
        let expectedAnglesByEdgeID: [String: (node: RuntimeRouteNode, angle: Double)] = [
            "edge_1": (switchNode, .pi),
            "edge_2": (switchNode, 0),
            "edge_6": (switchNode, .pi / 2),
            "edge_3": (rightNode, .pi),
            "edge_5": (rightNode, .pi / 2)
        ]

        for (edgeID, expectation) in expectedAnglesByEdgeID {
            let edge = try XCTUnwrap(graph.edgesByID[edgeID])
            let angle = SwitchArrowDirectionResolver.directionAngle(
                for: edge,
                from: expectation.node,
                in: graph
            )

            XCTAssertEqual(angle, expectation.angle, accuracy: 0.0001, "Unexpected angle for \(edgeID)")
        }
    }

    func testLevel028StyleFixtureSwitchArrowsUseRoadStartTangents() throws {
        let level = try loadSwitchArrowBugLevelFixture()
        let solution = try loadSwitchArrowBugSolutionFixture()
        XCTAssertEqual(solution.levelID, level.id)

        let engine = RouteEngine()
        try engine.buildGraph(from: level)
        let graph = try XCTUnwrap(engine.runtimeGraph)
        let expectedAnglesByEdgeID: [String: (sourceNodeID: String, angle: Double)] = [
            "e_multi_switch_chain_zigzag_switch_a_package": (
                "multi_switch_chain_zigzag_switch_a",
                -.pi / 2
            ),
            "e_multi_switch_chain_zigzag_switch_b_multi_switch_chain_zigzag_switch_c": (
                "multi_switch_chain_zigzag_switch_b",
                -.pi / 2
            ),
            "e_multi_switch_chain_zigzag_switch_c_multi_switch_chain_zigzag_switch_d": (
                "multi_switch_chain_zigzag_switch_c",
                .pi / 2
            ),
            "e_multi_switch_chain_zigzag_switch_d_destination": (
                "multi_switch_chain_zigzag_switch_d",
                -.pi / 2
            )
        ]

        for (edgeID, expectation) in expectedAnglesByEdgeID {
            let edge = try XCTUnwrap(graph.edgesByID[edgeID])
            let sourceNode = try XCTUnwrap(graph.nodesByID[expectation.sourceNodeID])
            let targetNode = try XCTUnwrap(graph.nodesByID[edge.toNodeID])

            XCTAssertNotEqual(targetNode.x, sourceNode.x, "Fixture edge \(edgeID) should have a diagonal target vector")
            XCTAssertNotEqual(targetNode.y, sourceNode.y, "Fixture edge \(edgeID) should have a diagonal target vector")

            let angle = SwitchArrowDirectionResolver.directionAngle(for: edge, from: sourceNode, in: graph)

            XCTAssertEqual(angle, expectation.angle, accuracy: 0.0001, "Unexpected angle for \(edgeID)")
        }
    }

    func testFourWaySwitchOutgoingOptionAnglesAreCardinal() throws {
        let engine = RouteEngine()
        try engine.buildGraph(from: makeFourWayIntersectionLevelData())
        let graph = try XCTUnwrap(engine.runtimeGraph)
        let centralSwitch = try XCTUnwrap(graph.nodesByID["central_switch"])
        let expectedAnglesByEdgeID: [String: Double] = [
            "e_central_dead_end": -.pi / 2,
            "e_central_package": .pi / 2,
            "e_central_destination": 0,
            "e_central_side_branch": .pi
        ]

        for (edgeID, expectedAngle) in expectedAnglesByEdgeID {
            let edge = try XCTUnwrap(graph.edgesByID[edgeID])
            let angle = SwitchArrowDirectionResolver.directionAngle(for: edge, from: centralSwitch, in: graph)

            XCTAssertEqual(angle, expectedAngle, accuracy: 0.0001, "Unexpected angle for \(edgeID)")
        }
    }

    func testIncomingDirectionAngleUsesRoadEntryDirectionForElbow() throws {
        let sourceNode = RuntimeRouteNode(
            id: "source",
            x: 0,
            y: 0,
            outgoingEdgeIDs: ["e_source_target"],
            activeOutgoingEdgeID: "e_source_target"
        )
        let targetNode = RuntimeRouteNode(
            id: "target",
            x: 1,
            y: 1,
            outgoingEdgeIDs: [],
            activeOutgoingEdgeID: nil
        )
        let edge = RuntimeRouteEdge(
            id: "e_source_target",
            fromNodeID: sourceNode.id,
            toNodeID: targetNode.id,
            roadPath: RoadPath.make(
                from: RoadPoint(x: sourceNode.x, y: sourceNode.y),
                to: RoadPoint(x: targetNode.x, y: targetNode.y),
                shape: .horizontalFirst
            )
        )
        let graph = RuntimeRouteGraph(
            nodesByID: [
                sourceNode.id: sourceNode,
                targetNode.id: targetNode
            ],
            edgesByID: [edge.id: edge]
        )

        let angle = SwitchArrowDirectionResolver.incomingDirectionAngle(for: edge, toward: targetNode, in: graph)

        XCTAssertEqual(angle, .pi / 2, accuracy: 0.0001)
    }

    func testBuildGraphInitializesTimerFromLevelData() throws {
        let engine = RouteEngine()

        try engine.buildGraph(from: makeLevelData())

        XCTAssertEqual(engine.timeLimit ?? -1, 45, accuracy: 0.0001)
        XCTAssertEqual(engine.timeRemaining ?? -1, 45, accuracy: 0.0001)
        XCTAssertEqual(engine.elapsedTime ?? -1, 0, accuracy: 0.0001)
    }

    func testUpdateDotFailsWhenTimeExpires() throws {
        let engine = RouteEngine(dotSpeed: 1)
        let level = makeLevelData()
        let timedLevel = LevelData(
            id: level.id,
            name: level.name,
            graph: level.graph,
            startNodeID: level.startNodeID,
            packageNodeID: level.packageNodeID,
            destinationNodeID: level.destinationNodeID,
            timeLimitSeconds: 1,
            parTaps: level.parTaps
        )
        try engine.buildGraph(from: timedLevel)
        XCTAssertTrue(engine.startDotMovement())

        engine.updateDot(deltaTime: 1.1)

        XCTAssertEqual(engine.timeRemaining ?? -1, 0, accuracy: 0.0001)
        XCTAssertEqual(engine.elapsedTime ?? -1, 1, accuracy: 0.0001)
        XCTAssertEqual(engine.levelOutcome, .failed(reason: .timeExpired))
    }

    func testUpdateDotFailsImmediatelyWhenIdleAndTimeIsConsumed() throws {
        let engine = RouteEngine(dotSpeed: 1)
        let level = makeLevelData()
        let timedLevel = LevelData(
            id: level.id,
            name: level.name,
            graph: level.graph,
            startNodeID: level.startNodeID,
            packageNodeID: level.packageNodeID,
            destinationNodeID: level.destinationNodeID,
            timeLimitSeconds: 1,
            parTaps: level.parTaps
        )
        try engine.buildGraph(from: timedLevel)

        // Dot is idle because movement has not started.
        engine.updateDot(deltaTime: 1.1)

        XCTAssertEqual(engine.timeRemaining ?? -1, 0, accuracy: 0.0001)
        XCTAssertEqual(engine.elapsedTime ?? -1, 1, accuracy: 0.0001)
        XCTAssertEqual(engine.levelOutcome, .failed(reason: .timeExpired))
    }

    func testUpdateDotReducesTimeRemainingByConsumedFrameTime() throws {
        let engine = RouteEngine(dotSpeed: 1)
        try engine.buildGraph(from: makeLevelData())
        XCTAssertTrue(engine.startDotMovement())

        engine.updateDot(deltaTime: 0.25)

        XCTAssertEqual(engine.timeRemaining ?? -1, 44.75, accuracy: 0.0001)
        XCTAssertEqual(engine.elapsedTime ?? -1, 0.25, accuracy: 0.0001)
    }

    func testUpdateDotConsumesRemainingTimeSliceBeforeTimingOut() throws {
        let nodes = [
            RouteNode(id: "start", x: 0, y: 0, outgoingEdgeIDs: ["to_destination"]),
            RouteNode(id: "destination", x: 1, y: 0, outgoingEdgeIDs: [])
        ]
        let edges = [
            RouteEdge(id: "to_destination", fromNodeID: "start", toNodeID: "destination")
        ]
        let level = LevelData(
            id: "time_slice",
            name: "Time Slice",
            graph: RouteGraph(nodes: nodes, edges: edges),
            startNodeID: "start",
            packageNodeID: "start",
            destinationNodeID: "destination",
            timeLimitSeconds: 1,
            parTaps: 1
        )

        let engine = RouteEngine(dotSpeed: 2)
        try engine.buildGraph(from: level)
        XCTAssertTrue(engine.startDotMovement())

        // Oversized frame delta should still move for the final 1.0s time slice.
        engine.updateDot(deltaTime: 1.5)

        let dot = try XCTUnwrap(engine.deliveryDot)
        XCTAssertEqual(dot.currentNodeID, "destination")
        XCTAssertNil(dot.currentEdgeID)
        XCTAssertEqual(engine.levelOutcome, .completed)
    }

    func testRestartLevelResetsDotPackageAndMovementState() throws {
        let engine = RouteEngine(dotSpeed: 1)
        try engine.buildGraph(from: makeLevelData())
        XCTAssertTrue(engine.startDotMovement())

        engine.updateDot(deltaTime: 3)

        let movedDot = try XCTUnwrap(engine.deliveryDot)
        XCTAssertEqual(movedDot.currentNodeID, "package")
        XCTAssertNil(movedDot.currentEdgeID)
        XCTAssertEqual(movedDot.transition?.toEdgeID, "e_package_return")
        XCTAssertTrue(movedDot.hasCollectedPackage)

        XCTAssertTrue(engine.restartLevel())

        let resetDot = try XCTUnwrap(engine.deliveryDot)
        XCTAssertEqual(resetDot.currentNodeID, "start")
        XCTAssertEqual(resetDot.currentEdgeID, "e_start_switch")
        XCTAssertEqual(resetDot.progressAlongEdge, 0)
        XCTAssertFalse(resetDot.hasCollectedPackage)
        XCTAssertEqual(engine.timeRemaining ?? -1, 45, accuracy: 0.0001)
        XCTAssertEqual(engine.elapsedTime ?? -1, 0, accuracy: 0.0001)
        XCTAssertNil(engine.levelOutcome)
        XCTAssertFalse(engine.didHaltAtDeadEnd)
    }

    func testRestartLevelResetsSwitchDirectionsToDefault() throws {
        let engine = RouteEngine()
        try engine.buildGraph(from: makeLevelData())

        XCTAssertTrue(engine.rotateSwitchNode(nodeID: "switch"))
        XCTAssertTrue(engine.rotateSwitchNode(nodeID: "switch"))

        let rotatedGraph = try XCTUnwrap(engine.runtimeGraph)
        XCTAssertEqual(rotatedGraph.nodesByID["switch"]?.activeOutgoingEdgeID, "e_switch_destination")

        XCTAssertTrue(engine.restartLevel())

        let resetGraph = try XCTUnwrap(engine.runtimeGraph)
        XCTAssertEqual(resetGraph.nodesByID["switch"]?.activeOutgoingEdgeID, "e_switch_package")
    }

    func testRestartLevelResetsTapCountToZero() throws {
        let engine = RouteEngine()
        try engine.buildGraph(from: makeLevelData())

        XCTAssertTrue(engine.rotateSwitchNode(nodeID: "switch"))
        XCTAssertTrue(engine.rotateSwitchNode(nodeID: "switch"))
        XCTAssertEqual(engine.tapCount, 2)

        XCTAssertTrue(engine.restartLevel())
        XCTAssertEqual(engine.tapCount, 0)
    }

    func testRestartLevelClearsFailureOutcome() throws {
        let engine = RouteEngine(dotSpeed: 1)
        try engine.buildGraph(from: makeLevelData())
        XCTAssertTrue(engine.startDotMovement())
        XCTAssertTrue(engine.rotateSwitchNode(nodeID: "switch"))
        XCTAssertTrue(engine.rotateSwitchNode(nodeID: "switch"))

        engine.updateDot(deltaTime: 3)

        XCTAssertEqual(engine.levelOutcome, .failed(reason: .reachedDestinationWithoutPackage))

        XCTAssertTrue(engine.restartLevel())

        XCTAssertNil(engine.levelOutcome)
        let dot = try XCTUnwrap(engine.deliveryDot)
        XCTAssertEqual(dot.currentNodeID, "start")
        XCTAssertEqual(dot.currentEdgeID, "e_start_switch")
    }

    func testRestartLevelReturnsFalseBeforeAnyLevelIsLoaded() {
        let engine = RouteEngine()

        XCTAssertFalse(engine.restartLevel())
    }

    func testRestartLevelReturnsTrueWhenRestoredLevelStartsAtLeafNode() throws {
        let engine = RouteEngine()
        try engine.buildGraph(from: makeLevelData(startNodeID: "destination"))

        XCTAssertTrue(engine.restartLevel())

        let dot = try XCTUnwrap(engine.deliveryDot)
        XCTAssertEqual(dot.currentNodeID, "destination")
        XCTAssertNil(dot.currentEdgeID)
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

    func testSwitchNodeKindClassifiesByValidOutgoingEdgeCount() {
        let cases: [(Int, SwitchNodeKind)] = [
            (0, .terminal),
            (1, .passThrough),
            (2, .twoWaySwitch),
            (3, .threeWaySwitch),
            (4, .fourWayIntersectionSwitch),
            (5, .invalidTooManyOutgoingEdges(validOutgoingEdgeCount: 5))
        ]

        for (validOutgoingCount, expectedKind) in cases {
            let (graph, node) = makeRuntimeGraphForSwitchClassification(validOutgoingCount: validOutgoingCount)

            XCTAssertEqual(graph.switchKind(for: node), expectedKind)
        }
    }

    func testSwitchNodeKindIgnoresMissingAndWrongSourceOutgoingEdgeIDs() {
        let (graph, node) = makeRuntimeGraphForSwitchClassification(
            validOutgoingCount: 1,
            includeInvalidListedEdgeIDs: true
        )

        XCTAssertEqual(graph.validOutgoingEdgeIDs(for: node), ["e_valid_0"])
        XCTAssertEqual(graph.switchKind(for: node), .passThrough)
    }

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

    func testFourWaySwitchInitializesAndCyclesThroughAllOutgoingEdges() throws {
        let engine = RouteEngine()
        try engine.buildGraph(from: makeFourWayIntersectionLevelData())

        var graph = try XCTUnwrap(engine.runtimeGraph)
        var switchNode = try XCTUnwrap(graph.nodesByID["central_switch"])
        XCTAssertEqual(switchNode.activeOutgoingEdgeID, "e_central_dead_end")

        XCTAssertTrue(engine.rotateSwitchNode(nodeID: "central_switch"))
        graph = try XCTUnwrap(engine.runtimeGraph)
        switchNode = try XCTUnwrap(graph.nodesByID["central_switch"])
        XCTAssertEqual(switchNode.activeOutgoingEdgeID, "e_central_package")

        XCTAssertTrue(engine.rotateSwitchNode(nodeID: "central_switch"))
        graph = try XCTUnwrap(engine.runtimeGraph)
        switchNode = try XCTUnwrap(graph.nodesByID["central_switch"])
        XCTAssertEqual(switchNode.activeOutgoingEdgeID, "e_central_destination")

        XCTAssertTrue(engine.rotateSwitchNode(nodeID: "central_switch"))
        graph = try XCTUnwrap(engine.runtimeGraph)
        switchNode = try XCTUnwrap(graph.nodesByID["central_switch"])
        XCTAssertEqual(switchNode.activeOutgoingEdgeID, "e_central_side_branch")

        XCTAssertTrue(engine.rotateSwitchNode(nodeID: "central_switch"))
        graph = try XCTUnwrap(engine.runtimeGraph)
        switchNode = try XCTUnwrap(graph.nodesByID["central_switch"])
        XCTAssertEqual(switchNode.activeOutgoingEdgeID, "e_central_dead_end")
        XCTAssertEqual(engine.tapCount, 4)
    }

    func testBuildGraphInitializesTapCountToZero() throws {
        let engine = RouteEngine()

        try engine.buildGraph(from: makeLevelData())

        XCTAssertEqual(engine.tapCount, 0)
    }

    func testRotateSwitchNodeIncrementsTapCountOnlyOnSuccessfulRotation() throws {
        let engine = RouteEngine()
        try engine.buildGraph(from: makeLevelData())

        XCTAssertTrue(engine.rotateSwitchNode(nodeID: "switch"))
        XCTAssertEqual(engine.tapCount, 1)

        XCTAssertFalse(engine.rotateSwitchNode(nodeID: "start"))
        XCTAssertEqual(engine.tapCount, 1)

        XCTAssertFalse(engine.rotateSwitchNode(nodeID: "unknown"))
        XCTAssertEqual(engine.tapCount, 1)
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
        XCTAssertEqual(startNode.activeOutgoingEdgeID, "valid")

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
        XCTAssertNil(startNode.activeOutgoingEdgeID)

        XCTAssertFalse(engine.rotateSwitchNode(nodeID: "start"))

        graph = try XCTUnwrap(engine.runtimeGraph)
        startNode = try XCTUnwrap(graph.nodesByID["start"])
        XCTAssertNil(startNode.activeOutgoingEdgeID)
    }

    func testBuildGraphThrowsForFiveWaySwitch() {
        let outgoingEdgeIDs = (0..<5).map { "e_switch_\($0)" }
        let targetNodes = (0..<5).map { RouteNode(id: "target_\($0)", x: Double($0 + 1), y: 0, outgoingEdgeIDs: []) }
        let nodes = [
            RouteNode(id: "start", x: 0, y: 0, outgoingEdgeIDs: ["e_start_switch"]),
            RouteNode(id: "switch", x: 1, y: 0, outgoingEdgeIDs: outgoingEdgeIDs)
        ] + targetNodes
        let edges = [
            RouteEdge(id: "e_start_switch", fromNodeID: "start", toNodeID: "switch")
        ] + (0..<5).map {
            RouteEdge(id: "e_switch_\($0)", fromNodeID: "switch", toNodeID: "target_\($0)")
        }
        let level = LevelData(
            id: "five_way_switch",
            name: "Five-Way Switch",
            graph: RouteGraph(nodes: nodes, edges: edges),
            startNodeID: "start",
            packageNodeID: "target_0",
            destinationNodeID: "target_1",
            timeLimitSeconds: 10,
            parTaps: 1
        )

        XCTAssertThrowsError(try RouteEngine().buildGraph(from: level)) { error in
            guard case RouteEngineError.switchHasTooManyOutgoingEdges(let nodeID, let outgoingEdgeCount) = error else {
                return XCTFail("Expected switchHasTooManyOutgoingEdges, got \(error)")
            }
            XCTAssertEqual(nodeID, "switch")
            XCTAssertEqual(outgoingEdgeCount, 5)
        }
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

    func testBuildGraphFailureDoesNotReplaceRestartTarget() throws {
        let engine = RouteEngine()
        let validLevel = makeLevelData()
        try engine.buildGraph(from: validLevel)

        let invalidLevel = makeLevelData(startNodeID: "missing")
        XCTAssertThrowsError(try engine.buildGraph(from: invalidLevel))
        XCTAssertNil(engine.runtimeGraph)
        XCTAssertNil(engine.deliveryDot)

        XCTAssertTrue(engine.restartLevel())
        let dot = try XCTUnwrap(engine.deliveryDot)
        XCTAssertEqual(dot.currentNodeID, validLevel.startNodeID)
        XCTAssertEqual(dot.currentEdgeID, "e_start_switch")
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
        let expectedProgress = 0.2 / (try roadLength(for: "e_switch_dead_end", in: graph))
        XCTAssertEqual(dot.progressAlongEdge, expectedProgress, accuracy: 0.0001)
        let expectedRoadPoint = try XCTUnwrap(graph.edgesByID["e_switch_dead_end"]).roadPath.point(atProgress: expectedProgress)
        assertPosition(
            dot.runtimePosition(in: graph),
            equals: DeliveryDotPosition(x: expectedRoadPoint.x, y: expectedRoadPoint.y)
        )
    }

    func testDotDoesNotChangeCourseWhenSwitchIsRotatedMidEdge() throws {
        let engine = RouteEngine(dotSpeed: 1)
        try engine.buildGraph(from: makeLevelData())
        XCTAssertTrue(engine.startDotMovement())

        // Move dot 1.5 units: 1.0 to cross e_start_switch and reach the switch node, then 0.5 units
        // into e_switch_package (the outgoing edge that the switch selected). This places the dot
        // partway along a switch-selected outgoing edge — the edge the acceptance criterion protects.
        engine.updateDot(deltaTime: 1.5)

        let dotBefore = try XCTUnwrap(engine.deliveryDot)
        XCTAssertEqual(dotBefore.currentEdgeID, "e_switch_package")
        let graph = try XCTUnwrap(engine.runtimeGraph)
        let expectedProgress = 0.5 / (try roadLength(for: "e_switch_package", in: graph))
        XCTAssertEqual(dotBefore.progressAlongEdge, expectedProgress, accuracy: 0.0001)

        // Rotating the switch that launched the current edge is ignored so the arrow cannot
        // contradict the dot's committed movement.
        XCTAssertFalse(engine.rotateSwitchNode(nodeID: "switch"))

        // Advance the dot further along the edge AFTER the rotation.
        // This step is what catches a regression where updateDot re-reads the switch direction
        // mid-edge and reroutes the dot to the newly active outgoing edge.
        engine.updateDot(deltaTime: 0.4)

        // The dot must still be on e_switch_package, now 0.9 road units in.
        let dotAfter = try XCTUnwrap(engine.deliveryDot)
        XCTAssertEqual(dotAfter.currentEdgeID, "e_switch_package", "Edge must not change mid-traversal")
        let expectedProgressAfter = 0.9 / (try roadLength(for: "e_switch_package", in: graph))
        XCTAssertEqual(dotAfter.progressAlongEdge, expectedProgressAfter, accuracy: 0.0001)
    }

    func testSwitchCannotRotateWhileDotIsOnEdgeLeavingThatSwitch() throws {
        let engine = RouteEngine(dotSpeed: 1)
        try engine.buildGraph(from: makeLevelData())
        XCTAssertTrue(engine.startDotMovement())

        engine.updateDot(deltaTime: 1.5)

        let dotBefore = try XCTUnwrap(engine.deliveryDot)
        XCTAssertEqual(dotBefore.currentEdgeID, "e_switch_package")
        XCTAssertFalse(engine.rotateSwitchNode(nodeID: "switch"))

        let graph = try XCTUnwrap(engine.runtimeGraph)
        let switchNode = try XCTUnwrap(graph.nodesByID["switch"])
        XCTAssertEqual(switchNode.activeOutgoingEdgeID, "e_switch_package")
        XCTAssertEqual(engine.tapCount, 0)
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

        // Move onto the package return edge so the switch is no longer the source of the
        // current committed movement.
        engine.updateDot(deltaTime: 1.5)

        let dotReturning = try XCTUnwrap(engine.deliveryDot)
        XCTAssertNil(dotReturning.currentEdgeID)
        XCTAssertEqual(dotReturning.transition?.toEdgeID, "e_package_return")

        // Rotate switch twice so destination is now the active direction for the next visit.
        engine.rotateSwitchNode(nodeID: "switch") // -> e_switch_dead_end
        engine.rotateSwitchNode(nodeID: "switch") // -> e_switch_destination

        // Advance enough for the dot to complete the loop back to switch and then start the
        // destination edge.
        // Advance enough for the orthogonal package return road to finish, then enter destination.
        engine.updateDot(deltaTime: 2.0)

        let dot = try XCTUnwrap(engine.deliveryDot)
        XCTAssertEqual(dot.currentEdgeID, "e_switch_destination",
                       "Dot should follow the newly active direction on its second visit to the switch")
    }

    func testPlayableFourWaySwitchRoutesToPackageThenDestinationAfterReturn() throws {
        let engine = RouteEngine(dotSpeed: 1)
        try engine.buildGraph(from: makeFourWayIntersectionLevelData())

        XCTAssertTrue(engine.rotateSwitchNode(nodeID: "central_switch"))
        XCTAssertEqual(engine.tapCount, 1)
        XCTAssertTrue(engine.startDotMovement())

        engine.updateDot(deltaTime: 1.75)
        var dot = try XCTUnwrap(engine.deliveryDot)
        XCTAssertEqual(dot.currentNodeID, "package")
        XCTAssertTrue(dot.hasCollectedPackage)
        XCTAssertNil(engine.levelOutcome)

        engine.updateDot(deltaTime: 0.70)
        dot = try XCTUnwrap(engine.deliveryDot)
        XCTAssertNotEqual(dot.currentNodeID, "central_switch")
        XCTAssertTrue(engine.rotateSwitchNode(nodeID: "central_switch"))
        XCTAssertEqual(engine.tapCount, 2)

        engine.updateDot(deltaTime: 2.5)

        dot = try XCTUnwrap(engine.deliveryDot)
        XCTAssertTrue(dot.hasCollectedPackage)
        XCTAssertEqual(dot.currentNodeID, "destination")
        XCTAssertEqual(engine.levelOutcome, .completed)
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

    // MARK: - Package pickup state (STORY-014)

    func testDotCollectsPackageWhenReachingPackageNode() throws {
        let engine = RouteEngine(dotSpeed: 1)
        try engine.buildGraph(from: makeLevelData())
        XCTAssertTrue(engine.startDotMovement())

        // Includes the longer orthogonal road from switch to package.
        engine.updateDot(deltaTime: 3.0)

        let dot = try XCTUnwrap(engine.deliveryDot)
        XCTAssertTrue(dot.hasCollectedPackage)
        XCTAssertEqual(dot.currentNodeID, "package")
    }

    func testReturningToPackageNodeDoesNotClearCollectedPackageState() throws {
        let engine = RouteEngine(dotSpeed: 1)
        try engine.buildGraph(from: makeLevelData())
        XCTAssertTrue(engine.startDotMovement())

        engine.updateDot(deltaTime: 3.0)
        let dotAfterFirstPickup = try XCTUnwrap(engine.deliveryDot)
        XCTAssertTrue(dotAfterFirstPickup.hasCollectedPackage)

        // From this point: finish package_return then traverse back into package again.
        engine.updateDot(deltaTime: 3.9)

        let dotAfterRevisit = try XCTUnwrap(engine.deliveryDot)
        XCTAssertTrue(dotAfterRevisit.hasCollectedPackage)
        XCTAssertEqual(dotAfterRevisit.currentNodeID, "package")
    }

    func testBuildGraphMarksPackageCollectedWhenStartNodeIsPackageNode() throws {
        let engine = RouteEngine()
        try engine.buildGraph(from: makeLevelData(startNodeID: "package", packageNodeID: "package"))

        let dot = try XCTUnwrap(engine.deliveryDot)
        XCTAssertTrue(dot.hasCollectedPackage)
        XCTAssertEqual(dot.currentNodeID, "package")
    }

    // MARK: - Destination completion state (STORY-015)

    func testReachingDestinationWithPackageCompletesLevel() throws {
        let engine = RouteEngine(dotSpeed: 1)
        try engine.buildGraph(from: makeLevelData())
        XCTAssertTrue(engine.startDotMovement())

        // Reach package first.
        engine.updateDot(deltaTime: 3.0)
        engine.rotateSwitchNode(nodeID: "switch") // -> e_switch_dead_end
        engine.rotateSwitchNode(nodeID: "switch") // -> e_switch_destination

        // Complete package->switch->destination.
        engine.updateDot(deltaTime: 4.0)

        let dot = try XCTUnwrap(engine.deliveryDot)
        XCTAssertTrue(dot.hasCollectedPackage)
        XCTAssertEqual(dot.currentNodeID, "destination")
        XCTAssertNil(dot.currentEdgeID)
        XCTAssertEqual(engine.levelOutcome, .completed)
    }

    func testReachingDestinationWithoutPackageFailsLevel() throws {
        let engine = RouteEngine(dotSpeed: 1)
        try engine.buildGraph(from: makeLevelData())

        // Route start->switch->destination without touching package.
        engine.rotateSwitchNode(nodeID: "switch") // -> e_switch_dead_end
        engine.rotateSwitchNode(nodeID: "switch") // -> e_switch_destination
        XCTAssertTrue(engine.startDotMovement())
        engine.updateDot(deltaTime: 3.1)

        let dot = try XCTUnwrap(engine.deliveryDot)
        XCTAssertFalse(dot.hasCollectedPackage)
        XCTAssertEqual(dot.currentNodeID, "destination")
        XCTAssertNil(dot.currentEdgeID)
        XCTAssertEqual(engine.levelOutcome, .failed(reason: .reachedDestinationWithoutPackage))
    }

    func testTerminalOutcomeStopsFurtherMovement() throws {
        let engine = RouteEngine(dotSpeed: 1)
        try engine.buildGraph(from: makeLevelData())

        // Force fail by routing directly to destination.
        engine.rotateSwitchNode(nodeID: "switch") // -> e_switch_dead_end
        engine.rotateSwitchNode(nodeID: "switch") // -> e_switch_destination
        XCTAssertTrue(engine.startDotMovement())
        engine.updateDot(deltaTime: 3.1)

        let dotAtOutcome = try XCTUnwrap(engine.deliveryDot)
        XCTAssertEqual(engine.levelOutcome, .failed(reason: .reachedDestinationWithoutPackage))
        XCTAssertEqual(dotAtOutcome.currentNodeID, "destination")
        XCTAssertNil(dotAtOutcome.currentEdgeID)

        // No additional movement or restart from terminal state.
        engine.updateDot(deltaTime: 10)
        XCTAssertFalse(engine.startDotMovement())
        let dotAfterExtraUpdate = try XCTUnwrap(engine.deliveryDot)
        XCTAssertEqual(dotAfterExtraUpdate.currentNodeID, "destination")
        XCTAssertNil(dotAfterExtraUpdate.currentEdgeID)
    }
}
