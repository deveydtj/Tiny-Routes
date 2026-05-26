import CoreGraphics
import XCTest
@testable import TinyRoutes

final class SwitchNodeViewTests: XCTestCase {
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
