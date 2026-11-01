import CoreGraphics
import SwiftUI
import UIKit
import XCTest
@testable import TinyRoutes

final class SwitchNodeViewTests: XCTestCase {
    @MainActor
    func testReferenceBoardsFitAndRenderBeforeDrivingStarts() throws {
        let levels = try TestLevelCatalog().loadAllProductionLevels().prefix(4)
        XCTAssertEqual(levels.map(\.timeLimitSeconds), [60, 90, 75, 75])
        for level in levels {
            let engine = RouteEngine()
            try engine.buildGraph(from: level)
            let graph = try XCTUnwrap(engine.runtimeGraph)
            let size = CGSize(width: 390, height: 540)
            let layout = BoardLayout.make(for: graph, in: size, padding: 64, cameraMode: .follow(nil))
            XCTAssertFalse(layout.cameraPlan?.isTrackingEnabled ?? false, "\(level.id) should show the entire board")
            let board = RouteBoardView(
                runtimeGraph: graph, deliveryDot: engine.deliveryDot,
                packageNodeID: level.packageNodeID, destinationNodeID: level.destinationNodeID,
                hasCollectedPackage: false, activeObjective: engine.activeObjective,
                activeObjectiveIndex: engine.activeObjectiveIndex,
                cosmeticLoadout: .default, isShowingPreview: false,
                pressedSwitchNodeID: nil, switchPressEventToken: 0,
                rejectedSwitchNodeID: nil, switchRejectionEventToken: 0,
                upcomingSwitchNodeID: nil, eligibleSwitchNodeID: nil, onNodeTapped: { _ in },
                startingEdgeIDs: engine.startingEdgeIDs, startNodeID: level.startNodeID,
                usesReferenceStyle: true
            ).frame(width: size.width, height: size.height).background(Color(red: 0.88, green: 0.95, blue: 0.98))
            let host = UIHostingController(rootView: board)
            let window = UIWindow(frame: CGRect(origin: .zero, size: size))
            window.rootViewController = host
            window.makeKeyAndVisible()
            host.view.layoutIfNeeded()
            let image = UIGraphicsImageRenderer(size: size).image { _ in
                host.view.drawHierarchy(in: host.view.bounds, afterScreenUpdates: true)
            }
            let attachment = XCTAttachment(image: image)
            attachment.name = "\(level.id)-starting-roads"
            attachment.lifetime = .keepAlways
            add(attachment)
            window.isHidden = true
        }
    }

    func testStartingRoadDotsAndTapTargetsFollowEachAvailableDeparture() throws {
        let level = try XCTUnwrap(TestLevelCatalog().loadAllProductionLevels().first { $0.id == "level_001" })
        let engine = RouteEngine()
        try engine.buildGraph(from: level)
        let graph = try XCTUnwrap(engine.runtimeGraph)
        let layout = BoardLayout.make(for: Array(graph.nodesByID.values), in: CGSize(width: 390, height: 540), padding: 64)
        let resolver = RouteBoardTapTargetResolver(runtimeGraph: graph, layout: layout)
        XCTAssertEqual(engine.startingEdgeIDs.count, 2)
        for edgeID in engine.startingEdgeIDs {
            let edge = try XCTUnwrap(graph.edgesByID[edgeID])
            let dots = RouteBoardTapTargetResolver.startingDotPoints(for: edge, layout: layout)
            XCTAssertGreaterThan(dots.count, 1)
            XCTAssertEqual(resolver.startingEdgeID(at: try XCTUnwrap(dots.last), edgeIDs: engine.startingEdgeIDs), edgeID)
        }
        XCTAssertNil(resolver.startingEdgeID(at: CGPoint(x: 0, y: 0), edgeIDs: engine.startingEdgeIDs))
        XCTAssertNil(resolver.startingEdgeID(at: try XCTUnwrap(layout.pointsByNodeID["start"]), edgeIDs: engine.startingEdgeIDs))
        XCTAssertTrue(engine.startDotMovement(edgeID: "start_to_bottom"))
        XCTAssertNil(resolver.startingEdgeID(at: CGPoint(x: 100, y: 100), edgeIDs: engine.startingEdgeIDs))
    }

    func testInteractionStatesHaveDistinctAccessibilityValues() {
        let values = Set([
            SwitchNodeInteractionState.inactive.accessibilityValue,
            SwitchNodeInteractionState.upcoming.accessibilityValue,
            SwitchNodeInteractionState.eligible.accessibilityValue,
            SwitchNodeInteractionState.locked.accessibilityValue
        ])
        XCTAssertEqual(values.count, 4)
        XCTAssertTrue(SwitchNodeInteractionState.eligible.accessibilityValue.contains("Available"))
    }
    func testDirectionalArrowTransformPointsRightAtZeroRadians() {
        let transform = DirectionalArrowTransform(angle: 0)

        XCTAssertEqual(transform.xScale, 1)
        XCTAssertEqual(transform.rotationAngle, 0, accuracy: 0.0001)
    }

    func testDirectionalArrowTransformKeepsVerticalDirectionsUnflipped() {
        let upTransform = DirectionalArrowTransform(angle: -.pi / 2)
        let downTransform = DirectionalArrowTransform(angle: .pi / 2)

        XCTAssertEqual(upTransform.xScale, 1)
        XCTAssertEqual(upTransform.rotationAngle, -.pi / 2, accuracy: 0.0001)
        XCTAssertEqual(downTransform.xScale, 1)
        XCTAssertEqual(downTransform.rotationAngle, .pi / 2, accuracy: 0.0001)
    }

    func testDirectionalArrowTransformMirrorsLeftFacingDirections() {
        let transform = DirectionalArrowTransform(angle: .pi)

        XCTAssertEqual(transform.xScale, -1)
        XCTAssertEqual(transform.rotationAngle, 0, accuracy: 0.0001)
    }

    func testDirectionalArrowTransformNormalizesAnglesBeyondPi() {
        let positiveOverflow = DirectionalArrowTransform(angle: 3 * .pi)
        let negativeOverflow = DirectionalArrowTransform(angle: -2 * .pi)

        XCTAssertEqual(positiveOverflow.xScale, -1)
        XCTAssertEqual(positiveOverflow.rotationAngle, 0, accuracy: 0.0001)
        XCTAssertEqual(negativeOverflow.xScale, 1)
        XCTAssertEqual(negativeOverflow.rotationAngle, 0, accuracy: 0.0001)
    }

    func testSwitchOptionIndicatorLayoutSupportsTwoThreeAndFourOptions() {
        XCTAssertEqual(SwitchOptionIndicatorLayout.angles(optionCount: 2, optionAngles: []).count, 2)
        XCTAssertEqual(SwitchOptionIndicatorLayout.angles(optionCount: 3, optionAngles: []).count, 3)
        XCTAssertEqual(SwitchOptionIndicatorLayout.angles(optionCount: 4, optionAngles: []).count, 4)
    }

    func testSwitchOptionIndicatorLayoutUsesProvidedOutgoingDirectionAngles() {
        let angles = SwitchOptionIndicatorLayout.angles(
            optionCount: 4,
            optionAngles: [0, .pi / 2, .pi, -.pi / 2]
        )

        XCTAssertEqual(angles[0], 0, accuracy: 0.0001)
        XCTAssertEqual(angles[1], .pi / 2, accuracy: 0.0001)
        XCTAssertEqual(angles[2], .pi, accuracy: 0.0001)
        XCTAssertEqual(angles[3], -.pi / 2, accuracy: 0.0001)
    }

    func testSwitchOptionIndicatorLayoutClampsUnsupportedOptionCounts() {
        XCTAssertEqual(SwitchOptionIndicatorLayout.angles(optionCount: 5, optionAngles: []).count, 4)
    }
}
