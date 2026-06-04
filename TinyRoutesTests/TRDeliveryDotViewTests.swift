import SwiftUI
import XCTest
@testable import TinyRoutes

final class TRDeliveryDotViewTests: XCTestCase {
    private let catalogService = ShopCatalogService()

    @MainActor
    func testDeliveryDotViewCanBeConstructedForEveryDotOption() {
        for option in catalogService.options(forCategoryID: ShopCosmeticCategoryID.deliveryDots) {
            let view = TRDeliveryDotView(
                option: option,
                isMoving: false,
                outerSize: TRGameplayStyle.Metrics.playerOuterSize,
                coreSize: TRGameplayStyle.Metrics.playerCoreSize,
                scale: TRGameplayStyle.Metrics.playerScale
            )

            XCTAssertNotNil(view)
        }
    }

    @MainActor
    func testDeliveryDotViewCanRenderMovingAndIdleStates() throws {
        let option = try XCTUnwrap(catalogService.option(withID: "dotCourierBlue"))
        let idleView = TRDeliveryDotView(
            option: option,
            isMoving: false,
            outerSize: 52,
            coreSize: 40,
            scale: 0.75
        )
        let movingView = TRDeliveryDotView(
            option: option,
            isMoving: true,
            outerSize: 52,
            coreSize: 40,
            scale: 0.75
        )

        XCTAssertNotNil(idleView)
        XCTAssertNotNil(movingView)
    }

    @MainActor
    func testUnknownDotOptionFallsBackSafely() {
        let option = ShopCosmeticOption(
            id: "unknownDot",
            categoryID: "unknown",
            title: "Unknown",
            price: nil,
            isUnlocked: true,
            isSelected: false,
            accent: .classic
        )
        let view = TRDeliveryDotView(
            option: option,
            isMoving: true,
            outerSize: 52,
            coreSize: 40,
            scale: 0.75
        )

        XCTAssertNotNil(view)
        XCTAssertFalse(TRDeliveryDotVisual.colors(for: option).isEmpty)
    }
}

final class GameplayCameraLayoutTests: XCTestCase {
    func testLevelPlayableExtentsIncludeNodesAndRoads() {
        let graph = makeRuntimeGraph(points: [
            ("start", 0, 0),
            ("switch", 1, 2),
            ("destination", -0.5, 4),
        ])

        let extents = LevelPlayableExtents.make(for: graph, cameraSafeMargin: 0.25)

        XCTAssertEqual(extents.levelWidth, 1.5, accuracy: 0.0001)
        XCTAssertEqual(extents.levelHeight, 4.0, accuracy: 0.0001)
        XCTAssertEqual(extents.cameraSafeBounds.minX, -0.75, accuracy: 0.0001)
        XCTAssertEqual(extents.cameraSafeBounds.maxY, 4.25, accuracy: 0.0001)
    }

    func testCameraFollowsPlayerInsideTallLevel() {
        let graph = makeRuntimeGraph(points: [
            ("start", 0, 0),
            ("middle", 0, 3),
            ("destination", 0, 6),
        ])
        let layout = BoardLayout.make(
            for: graph,
            in: CGSize(width: 320, height: 480),
            padding: 64,
            cameraMode: .follow(RoadPoint(x: 0, y: 3))
        )

        XCTAssertTrue(layout.cameraPlan?.isTrackingEnabled == true)
        let middlePoint = layout.pointsByNodeID["middle"]
        XCTAssertEqual(middlePoint?.x ?? 0, 160, accuracy: 0.001)
        XCTAssertEqual(middlePoint?.y ?? 0, 240, accuracy: 0.001)
    }

    func testCameraClampsAtTopAndBottomBounds() {
        let graph = makeRuntimeGraph(points: [
            ("start", 0, 0),
            ("middle", 0, 3),
            ("destination", 0, 6),
        ])
        let viewport = CGSize(width: 320, height: 480)
        let topLayout = BoardLayout.make(
            for: graph,
            in: viewport,
            padding: 64,
            cameraMode: .follow(RoadPoint(x: 0, y: 6))
        )
        let bottomLayout = BoardLayout.make(
            for: graph,
            in: viewport,
            padding: 64,
            cameraMode: .follow(RoadPoint(x: 0, y: 0))
        )

        let topOffset = topLayout.cameraPlan?.contentOffset.y ?? .infinity
        let bottomOffset = bottomLayout.cameraPlan?.contentOffset.y ?? -.infinity
        let contentHeight = topLayout.cameraPlan?.contentSize.height ?? 0
        XCTAssertLessThanOrEqual(topOffset, 0.001)
        XCTAssertGreaterThanOrEqual(bottomOffset, viewport.height - contentHeight - 0.001)
        XCTAssertGreaterThan(topLayout.pointsByNodeID["destination"]?.y ?? 0, 0)
        XCTAssertLessThan(bottomLayout.pointsByNodeID["start"]?.y ?? viewport.height, viewport.height)
    }

    func testSmallLevelsKeepFitToScreenLayout() {
        let graph = makeRuntimeGraph(points: [
            ("start", -1, -0.3),
            ("package", 0, 0.4),
            ("destination", 1, -0.3),
        ])
        let nodes = graph.nodesByID.values.sorted { $0.id < $1.id }
        let oldLayout = BoardLayout.make(
            for: nodes,
            in: CGSize(width: 320, height: 480),
            padding: 64
        )
        let cameraLayout = BoardLayout.make(
            for: graph,
            in: CGSize(width: 320, height: 480),
            padding: 64,
            cameraMode: .follow(RoadPoint(x: 0, y: 0))
        )

        XCTAssertNil(cameraLayout.cameraPlan)
        XCTAssertEqual(cameraLayout.pointsByNodeID, oldLayout.pointsByNodeID)
    }

    func testLargePortraitPreviewFitsFullLevelBeforeTracking() {
        let graph = makeRuntimeGraph(points: [
            ("start", 0, 0),
            ("one", -0.25, 1.6),
            ("two", 0.25, 3.2),
            ("destination", 0, 4.8),
        ])
        let layout = BoardLayout.make(
            for: graph,
            in: CGSize(width: 320, height: 480),
            padding: 64,
            cameraMode: .preview
        )

        XCTAssertEqual(layout.cameraPlan?.isTrackingEnabled, false)
        for point in layout.pointsByNodeID.values {
            XCTAssertGreaterThanOrEqual(point.x, 0)
            XCTAssertLessThanOrEqual(point.x, 320)
            XCTAssertGreaterThanOrEqual(point.y, 0)
            XCTAssertLessThanOrEqual(point.y, 480)
        }
    }

    private func makeRuntimeGraph(points: [(String, Double, Double)]) -> RuntimeRouteGraph {
        var nodesByID: [String: RuntimeRouteNode] = [:]
        var edgesByID: [String: RuntimeRouteEdge] = [:]

        for (index, point) in points.enumerated() {
            let outgoingEdgeID = index + 1 < points.count ? "edge_\(index)" : nil
            nodesByID[point.0] = RuntimeRouteNode(
                id: point.0,
                x: point.1,
                y: point.2,
                outgoingEdgeIDs: outgoingEdgeID.map { [$0] } ?? [],
                activeOutgoingEdgeID: outgoingEdgeID
            )
        }

        for index in 0..<(points.count - 1) {
            let from = points[index]
            let to = points[index + 1]
            let edgeID = "edge_\(index)"
            edgesByID[edgeID] = RuntimeRouteEdge(
                id: edgeID,
                fromNodeID: from.0,
                toNodeID: to.0,
                roadPath: RoadPath.make(
                    from: RoadPoint(x: from.1, y: from.2),
                    to: RoadPoint(x: to.1, y: to.2)
                )
            )
        }

        return RuntimeRouteGraph(nodesByID: nodesByID, edgesByID: edgesByID)
    }
}
