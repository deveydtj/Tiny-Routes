import XCTest
import simd
@testable import TinyRoutes

final class TRLevelMapLayoutTests: XCTestCase {
    private let layout = TRLevelMapLayout(levelCount: 12)

    func testStationsClimbTheIslandOnTheRoadAndInsideIt() {
        var previousY = -Double.infinity
        for index in 0..<layout.levelCount {
            let station = layout.station(index)
            XCTAssertGreaterThan(station.y, previousY)
            previousY = station.y
            // The distance is measured to samples 0.06 apart.
            XCTAssertEqual(layout.distanceToRoad(station), 0, accuracy: 0.04)
            XCTAssertLessThan(abs(station.x), TRLevelMapLayout.width / 2 - 0.6)
        }
        XCTAssertLessThan(previousY, layout.depth - 1)
    }

    func testTheVanParksNearEachStopClearOfEveryTile() {
        for index in 0..<layout.levelCount {
            let y = layout.parking(index)
            XCTAssertEqual(y, layout.station(index).y, accuracy: 0.75)
            let x = layout.roadPoint(atY: y).x
            XCTAssertEqual(layout.tileOverlap(minX: x - 0.33, maxX: x + 0.33, minY: y - 0.33, maxY: y + 0.6), 0, "level \(index + 1)")
        }
    }

    func testRoadSamplesRunEitherWayWithBothEndsAndNoGaps() {
        for (from, to) in [(0.4, 6.0), (9.0, 2.5)] {
            let samples = layout.roadSamples(fromY: from, toY: to, spacing: 0.1)
            XCTAssertEqual(samples.first?.y ?? .nan, from, accuracy: 1e-9)
            XCTAssertEqual(samples.last?.y ?? .nan, to, accuracy: 1e-9)
            for (a, b) in zip(samples, samples.dropFirst()) {
                // Steps are estimated from the heading, so a bend stretches one a little.
                XCTAssertLessThanOrEqual(hypot(b.x - a.x, b.y - a.y), 0.125)
            }
        }
    }

    func testViewPointsMatchTheOrthographicLens() {
        let width: CGFloat = 402
        let height = layout.viewHeight(viewWidth: width)
        let scale = TRLevelMapLayout.scale(viewWidth: width)
        // The lens looks at the middle of the view, and its scale spans the height.
        let centre = layout.viewPoint(layout.lens.target, viewWidth: width)
        XCTAssertEqual(centre.x, width / 2, accuracy: 0.01)
        XCTAssertEqual(centre.y, height / 2, accuracy: 0.01)
        XCTAssertEqual(CGFloat(layout.lens.orthographicScale) * 2 * scale, height, accuracy: 0.01)
        // The island's sides sit inside the view, and level 1 below level 12.
        let left = layout.viewPoint(layout.world(RoadPoint(x: -TRLevelMapLayout.width / 2, y: 1)), viewWidth: width)
        XCTAssertGreaterThan(left.x, 0)
        let first = layout.viewPoint(layout.world(layout.station(0)), viewWidth: width)
        let last = layout.viewPoint(layout.world(layout.station(11)), viewWidth: width)
        XCTAssertGreaterThan(first.y, last.y)
        XCTAssertLessThan(first.y, height)
        XCTAssertGreaterThan(last.y, TRLevelTile.size.height)
    }

    func testSceneryKeepsOffTheRoadAndCottagesAndPondsKeepClearOfTiles() {
        let scenery = TRLevelMapScenery(layout: layout)
        XCTAssertFalse(scenery.items.isEmpty)
        XCTAssertFalse(scenery.houses.isEmpty)
        for item in scenery.items {
            XCTAssertGreaterThan(layout.distanceToRoad(item.point), TRLevelMapLawn.Measure.curbWidth / 2, "\(item)")
        }
        for house in scenery.houses {
            let p = house.point
            XCTAssertEqual(layout.tileOverlap(minX: p.x - 0.3, maxX: p.x + 0.3, minY: p.y - 0.3, maxY: p.y + 0.6), 0, "\(house)")
        }
        for pond in scenery.ponds {
            let p = pond.centre
            XCTAssertEqual(layout.tileOverlap(minX: p.x - 0.6, maxX: p.x + 0.6, minY: p.y - 0.4, maxY: p.y + 0.4), 0, "\(pond)")
        }
    }

    func testSceneryIsTheSameEveryVisit() {
        XCTAssertEqual(TRLevelMapScenery(layout: layout), TRLevelMapScenery(layout: layout))
    }

    @MainActor
    func testDriveEasingAndDurations() {
        XCTAssertEqual(TRLevelMapScene.easedTime(progress: 0), 0, accuracy: 1e-9)
        XCTAssertEqual(TRLevelMapScene.easedTime(progress: 1), 1, accuracy: 1e-9)
        // The inverse of smoothstep.
        for t in stride(from: 0.0, through: 1.0, by: 0.1) {
            let p = t * t * (3 - 2 * t)
            XCTAssertEqual(TRLevelMapScene.easedTime(progress: p), t, accuracy: 1e-6)
        }
        XCTAssertEqual(TRLevelMapScene.duration(forLength: 0.1), 0.55)
        XCTAssertEqual(TRLevelMapScene.duration(forLength: 50), 1.6)
    }
}
