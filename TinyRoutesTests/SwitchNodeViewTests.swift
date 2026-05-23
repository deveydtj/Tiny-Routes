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
}
