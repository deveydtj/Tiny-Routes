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
