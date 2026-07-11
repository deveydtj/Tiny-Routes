import XCTest
@testable import TinyRoutes

final class SwitchEligibilityServiceTests: XCTestCase {
    private let service = SwitchEligibilityService()

    private func graph(cycle: Bool = false) -> RuntimeRouteGraph {
        let nodes = [
            "start": RuntimeRouteNode(id: "start", x: 0, y: 0, outgoingEdgeIDs: ["e0"], activeOutgoingEdgeID: "e0"),
            "route": RuntimeRouteNode(id: "route", x: 1, y: 0, outgoingEdgeIDs: ["e1"], activeOutgoingEdgeID: "e1"),
            "switch1": RuntimeRouteNode(id: "switch1", x: 2, y: 0, outgoingEdgeIDs: ["e2", "e3"], activeOutgoingEdgeID: "e2"),
            "switch2": RuntimeRouteNode(id: "switch2", x: 3, y: 0, outgoingEdgeIDs: ["e4", "e5"], activeOutgoingEdgeID: "e4"),
            "end": RuntimeRouteNode(id: "end", x: 4, y: 0, outgoingEdgeIDs: [], activeOutgoingEdgeID: nil)
        ]
        let definitions = cycle
            ? [("e0", "start", "route"), ("e1", "route", "start")]
            : [("e0", "start", "route"), ("e1", "route", "switch1"), ("e2", "switch1", "switch2"), ("e3", "switch1", "end"), ("e4", "switch2", "end"), ("e5", "switch2", "route")]
        let edges = Dictionary(uniqueKeysWithValues: definitions.map { id, from, to in
            (id, RuntimeRouteEdge(
                id: id, fromNodeID: from, toNodeID: to,
                roadPath: RoadPath.make(from: RoadPoint(x: nodes[from]!.x, y: nodes[from]!.y), to: RoadPoint(x: nodes[to]!.x, y: nodes[to]!.y))
            ))
        })
        return RuntimeRouteGraph(nodesByID: nodes, edgesByID: edges)
    }

    private func rules(window: Double) -> LevelRules {
        LevelRules(switchInteractionMode: .liveLookahead, switchLookaheadSeconds: window, switchTapCooldownSeconds: 0.12)
    }

    func testFindsFirstUpcomingSwitchThroughRouteNodes() {
        let snapshot = service.snapshot(graph: graph(), dot: DeliveryDot(currentNodeID: "start"), speed: 1, hasCollectedPackage: false, rules: rules(window: 3))
        XCTAssertEqual(snapshot.upcomingNodeID, "switch1")
        XCTAssertEqual(snapshot.eligibleNodeID, "switch1")
        XCTAssertEqual(snapshot.travelTimeSeconds!, 2, accuracy: 0.0001)
    }

    func testSecondSwitchDoesNotReplaceFirstUpcomingSwitch() {
        let snapshot = service.snapshot(graph: graph(), dot: DeliveryDot(currentNodeID: "start"), speed: 1, hasCollectedPackage: false, rules: rules(window: 1))
        XCTAssertEqual(snapshot.upcomingNodeID, "switch1")
        XCTAssertNil(snapshot.eligibleNodeID)
        XCTAssertEqual(snapshot.reason, .outsideLookaheadWindow)
    }

    func testPartwayAlongEdgeCanEnterEligibilityWindow() {
        let dot = DeliveryDot(currentNodeID: "start", currentEdgeID: "e0", progressAlongEdge: 0.5)
        let snapshot = service.snapshot(graph: graph(), dot: dot, speed: 1, hasCollectedPackage: false, rules: rules(window: 1.5))
        XCTAssertEqual(snapshot.eligibleNodeID, "switch1")
        XCTAssertEqual(snapshot.travelTimeSeconds!, 1.5, accuracy: 0.0001)
    }

    func testSwitchAtCurrentNodeHasZeroTravelTime() {
        let snapshot = service.snapshot(graph: graph(), dot: DeliveryDot(currentNodeID: "switch1"), speed: 1, hasCollectedPackage: false, rules: rules(window: 0))
        XCTAssertEqual(snapshot.eligibleNodeID, "switch1")
        XCTAssertEqual(snapshot.travelTimeSeconds, 0)
    }

    func testCycleTerminatesSafely() {
        let snapshot = service.snapshot(graph: graph(cycle: true), dot: DeliveryDot(currentNodeID: "start"), speed: 1, hasCollectedPackage: false, rules: rules(window: 10))
        XCTAssertEqual(snapshot.reason, .cycleDetected)
    }
}
