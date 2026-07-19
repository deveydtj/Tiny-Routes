import SwiftUI
import XCTest
@testable import TinyRoutes

final class GameplayCosmeticLoadoutTests: XCTestCase {
    private let catalogService = ShopCatalogService()

    @MainActor
    func testGameplayScreenCanBeConstructedWithCustomLoadout() throws {
        let screen = GameplayScreen(
            levelID: "level_001",
            isPaused: false,
            cosmeticLoadout: try customLoadout(),
            onPauseResumeTapped: {},
            onCompleteTapped: { _, _ in },
            onFailTapped: { _, _, _ in },
            onExitTapped: {}
        )

        XCTAssertNotNil(screen)
    }

    @MainActor
    func testRouteBoardViewCanBeConstructedWithLoadout() throws {
        let graph = sampleRuntimeGraph()
        let board = RouteBoardView(
            runtimeGraph: graph,
            deliveryDot: DeliveryDot(currentNodeID: "start", currentEdgeID: "edge", progressAlongEdge: 0.5),
            packageNodeID: "start",
            destinationNodeID: "finish",
            hasCollectedPackage: true,
            activeObjective: RouteObjective(
                id: "finish",
                nodeID: "finish",
                kind: .destination,
                sequenceIndex: 1,
                revealPolicy: "whenActive"
            ),
            cosmeticLoadout: try customLoadout(),
            isShowingPreview: false,
            pressedSwitchNodeID: nil,
            switchPressEventToken: 0,
            rejectedSwitchNodeID: nil,
            switchRejectionEventToken: 0,
            upcomingSwitchNodeID: nil,
            eligibleSwitchNodeID: nil,
            onNodeTapped: { _ in }
        )

        XCTAssertNotNil(board)
    }

    func testCurrentObjectiveMarkerUsesAuthoredTitleAndSequenceForAccessibility() {
        let objective = RouteObjective(
            id: "inspect",
            nodeID: "checkpoint",
            kind: .checkpoint,
            sequenceIndex: 1,
            revealPolicy: "whenActive",
            displayMetadata: ["title": .string("Inspect the bridge")]
        )

        let presentation = TRCurrentObjectiveMarkerPresentation(objective: objective)

        XCTAssertEqual(presentation.visual, .systemImage("checkmark.seal.fill"))
        XCTAssertEqual(presentation.title, "Inspect the bridge")
        XCTAssertEqual(presentation.orderText, "2")
        XCTAssertEqual(presentation.accessibilityLabel, "Current objective 2: Inspect the bridge")
    }

    func testCurrentObjectiveMarkerProvidesDistinctVisualsForEveryObjectiveKind() {
        let kinds: [(RouteObjectiveKind, TRCurrentObjectiveMarkerPresentation.Visual)] = [
            (.pickup, .package),
            (.checkpoint, .systemImage("checkmark.seal.fill")),
            (.delivery, .systemImage("shippingbox.fill")),
            (.destination, .destination)
        ]

        for (index, pair) in kinds.enumerated() {
            let presentation = TRCurrentObjectiveMarkerPresentation(objective: RouteObjective(
                id: "objective_\(index)",
                nodeID: "node_\(index)",
                kind: pair.0,
                sequenceIndex: index,
                revealPolicy: "whenActive"
            ))
            XCTAssertEqual(presentation.visual, pair.1)
        }
    }

    func testRoadPresentationKeepsUnavailableRoadsVisibleAsLockedOrClosed() {
        let lockedEdge = RuntimeRouteEdge(
            id: "shortcut",
            fromNodeID: "start",
            toNodeID: "finish",
            roadPath: RoadPath.make(from: RoadPoint(x: 0, y: 0), to: RoadPoint(x: 1, y: 0)),
            availabilityRule: EdgeAvailabilityRule(
                requiredCompletedObjectiveIDs: ["pickup"]
            )
        )
        let closedEdge = RuntimeRouteEdge(
            id: "return",
            fromNodeID: "finish",
            toNodeID: "start",
            roadPath: RoadPath.make(from: RoadPoint(x: 1, y: 0), to: RoadPoint(x: 0, y: 0)),
            availabilityRule: EdgeAvailabilityRule(
                forbiddenCompletedObjectiveIDs: ["pickup"]
            )
        )

        let locked = RoadPresentation.resolve(
            edge: lockedEdge,
            edgeUsageCount: 0,
            completedObjectiveIDs: [],
            activeObjectiveIndex: 0
        )
        let opened = RoadPresentation.resolve(
            edge: lockedEdge,
            edgeUsageCount: 0,
            completedObjectiveIDs: ["pickup"],
            activeObjectiveIndex: 1
        )
        let closed = RoadPresentation.resolve(
            edge: closedEdge,
            edgeUsageCount: 0,
            completedObjectiveIDs: ["pickup"],
            activeObjectiveIndex: 1
        )

        XCTAssertEqual(locked.state, .locked)
        XCTAssertEqual(locked.accessibilityLabel, "Road shortcut, locked")
        XCTAssertEqual(opened.state, .available)
        XCTAssertEqual(closed.state, .closed)
        XCTAssertEqual(closed.accessibilityLabel, "Road return, closed")
    }

    func testRoadPresentationMarksExhaustedOneUseRoadConsumed() {
        let edge = RuntimeRouteEdge(
            id: "one_use",
            fromNodeID: "start",
            toNodeID: "finish",
            roadPath: RoadPath.make(from: RoadPoint(x: 0, y: 0), to: RoadPoint(x: 1, y: 0)),
            availabilityRule: EdgeAvailabilityRule(usageLimit: 1)
        )

        let presentation = RoadPresentation.resolve(
            edge: edge,
            edgeUsageCount: 1,
            completedObjectiveIDs: [],
            activeObjectiveIndex: 0
        )

        XCTAssertEqual(presentation.state, .consumed)
        XCTAssertEqual(presentation.accessibilityLabel, "Road one_use, consumed")
    }

    private func customLoadout() throws -> GameplayCosmeticLoadout {
        GameplayCosmeticLoadout(
            routeTheme: try XCTUnwrap(catalogService.option(withID: "themeForestPath")),
            deliveryDot: try XCTUnwrap(catalogService.option(withID: "dotGolden")),
            trail: try XCTUnwrap(catalogService.option(withID: "trailBubbles")),
            confetti: try XCTUnwrap(catalogService.option(withID: "confettiCandy")),
            destination: try XCTUnwrap(catalogService.option(withID: "destinationCabin"))
        )
    }

    private func sampleRuntimeGraph() -> RuntimeRouteGraph {
        let start = RuntimeRouteNode(
            id: "start",
            x: 0,
            y: 0,
            outgoingEdgeIDs: ["edge"],
            activeOutgoingEdgeID: "edge"
        )
        let finish = RuntimeRouteNode(
            id: "finish",
            x: 1,
            y: 0,
            outgoingEdgeIDs: [],
            activeOutgoingEdgeID: nil
        )
        let edge = RuntimeRouteEdge(
            id: "edge",
            fromNodeID: "start",
            toNodeID: "finish",
            roadPath: RoadPath.make(from: RoadPoint(x: 0, y: 0), to: RoadPoint(x: 1, y: 0))
        )

        return RuntimeRouteGraph(
            nodesByID: [
                start.id: start,
                finish.id: finish
            ],
            edgesByID: [
                edge.id: edge
            ]
        )
    }
}
