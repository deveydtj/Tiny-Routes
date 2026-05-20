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
