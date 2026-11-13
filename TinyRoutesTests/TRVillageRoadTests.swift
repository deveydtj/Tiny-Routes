@testable import TinyRoutes
import XCTest

final class TRVillageRoadTests: XCTestCase {
    func testHousesAlternateSidesWithTheRoadSwingingPastEach() {
        for level in 0...6 {
            let roadX = TRVillageRoad.roadX(Double(level) * TRVillageRoad.spacing)
            let houseX = TRVillageRoad.houseX(level)
            // The road bends out towards each house, leaving it room on the verge.
            XCTAssertEqual(roadX < TRVillageRoad.centerX, houseX < TRVillageRoad.centerX, "level \(level)")
            XCTAssertGreaterThan(abs(houseX - roadX), 40, "level \(level)")
        }
    }

    func testCameraParksTheVanAtEachHouse() {
        let road = TRVillageRoad(levelCount: 12, currentLevel: 7)
        for level in 1...7 {
            XCTAssertEqual(road.selectedLevel(camera: road.camera(forLevel: level)), level)
        }
        XCTAssertEqual(road.cameraRange, road.camera(forLevel: 1)...road.camera(forLevel: 7))
    }

    func testVanNeverPassesTheFurthestLevelOpen() {
        let road = TRVillageRoad(levelCount: 12, currentLevel: 4)
        XCTAssertEqual(road.vanY(camera: road.camera(forLevel: 9)), 4 * TRVillageRoad.spacing)
        XCTAssertEqual(road.selectedLevel(camera: road.camera(forLevel: 9)), 4)
        XCTAssertEqual(road.selectedLevel(camera: -10_000), 1)
    }

    func testCurrentLevelIsKeptOnTheRoad() {
        XCTAssertEqual(TRVillageRoad(levelCount: 12, currentLevel: 40).currentLevel, 12)
        XCTAssertEqual(TRVillageRoad(levelCount: 12, currentLevel: 0).currentLevel, 1)
    }

    func testRubberBandGivesLessTheFurtherPastAnEnd() {
        let road = TRVillageRoad(levelCount: 12, currentLevel: 5)
        let end = road.cameraRange.upperBound
        XCTAssertEqual(road.rubberBanded(end - 30), end - 30)
        let first = road.rubberBanded(end + 20) - end
        let later = road.rubberBanded(end + 120) - road.rubberBanded(end + 100)
        XCTAssertEqual(first, 10, accuracy: 1)
        XCTAssertLessThan(later, first)
        XCTAssertGreaterThan(later, 0)
        XCTAssertLessThan(road.rubberBanded(end + 10_000), end + TRVillageRoad.stretchLimit)
        XCTAssertEqual(road.give(at: end - 10), 1)
        XCTAssertLessThan(road.give(at: end + 100), road.give(at: end + 10))
    }

    func testTurningBackPastAnEndNeverJumps() {
        // With only the first level open, both ends are the same place.
        let road = TRVillageRoad(levelCount: 12, currentLevel: 1)
        let start = road.cameraRange.lowerBound
        var raw = start, shown = road.rubberBanded(raw)
        let steps: [Double] = [-1.0, 1, -1].flatMap { Array(repeating: $0, count: 150) }
        for step in steps {
            raw += step
            let next = road.rubberBanded(raw)
            XCTAssertLessThanOrEqual(abs(next - shown), 0.5 + 1e-9, "raw \(raw)")
            shown = next
        }
        // Back where the finger started, the camera is too.
        XCTAssertEqual(road.rubberBanded(start), start)
        for over in [-90.0, -10, 0, 25, 200] {
            XCTAssertEqual(road.unbanded(road.rubberBanded(start + over)), start + over, accuracy: 0.001)
        }
    }

    func testLetGoCameraRestsAtAHouseOrBackInsideTheEnds() {
        let road = TRVillageRoad(levelCount: 12, currentLevel: 8)
        let three = road.camera(forLevel: 3)
        XCTAssertEqual(road.restingCamera(from: three + 30, velocity: 0), three)
        // A flick carries on a few houses.
        XCTAssertEqual(road.restingCamera(from: three, velocity: 1000), road.camera(forLevel: 6))
        XCTAssertEqual(road.restingCamera(from: three, velocity: 99_999), road.camera(forLevel: 8))
        XCTAssertEqual(road.restingCamera(from: road.cameraRange.upperBound + 60, velocity: -500), road.cameraRange.upperBound)
        XCTAssertEqual(road.restingCamera(from: road.cameraRange.lowerBound - 60, velocity: 500), road.cameraRange.lowerBound)
    }

    func testArcLengthRoundTrips() {
        let road = TRVillageRoad(levelCount: 12, currentLevel: 12)
        for y in stride(from: 0.0, through: 900, by: 37) {
            XCTAssertEqual(road.y(atArcLength: road.arcLength(atY: y)), y, accuracy: 0.01)
        }
        XCTAssertGreaterThan(road.arcLength(atY: 80) - road.arcLength(atY: 0), 80)
    }

    func testChaptersHoldTenLevelsEach() {
        XCTAssertEqual(TRVillageRoad(levelCount: 12, currentLevel: 1).chapterCount, 2)
        XCTAssertEqual(TRVillageRoad(levelCount: 10, currentLevel: 1).chapterCount, 1)
        XCTAssertEqual(TRVillageRoad.chapter(ofLevel: 10), 1)
        XCTAssertEqual(TRVillageRoad.chapter(ofLevel: 11), 2)
        XCTAssertEqual(TRVillageRoad.firstLevel(ofChapter: 2), 11)
        XCTAssertEqual(TRVillageRoad.chapterName(1), "Willow Bend")
        XCTAssertEqual(TRVillageRoad.chapterName(9), "Chapter 9")
    }

    func testLensPutsTheBoardsEdgesWhereTheyBelong() {
        let lens = TRVillageLens(width: 390, boardTop: 104, lip: 523)
        // At the lip things are full size; at the far edge, the far scale.
        let near = lens.project(x: 195, y: 0, camera: 0)
        XCTAssertEqual(near.point.y, 523, accuracy: 0.001)
        XCTAssertEqual(near.scale, 1, accuracy: 0.001)
        let farDepth = TRVillageLens.depth / TRVillageLens.farScale - TRVillageLens.depth
        let far = lens.project(x: 195, y: farDepth, camera: 0)
        XCTAssertEqual(far.point.y, 104, accuracy: 0.001)
        // Off-centre points draw in towards the middle as they recede.
        XCTAssertLessThan(lens.project(x: 340, y: farDepth, camera: 0).point.x, 340)
        // Wider screens stretch across.
        XCTAssertEqual(TRVillageLens(width: 430, boardTop: 104, lip: 600).project(x: 390, y: 0, camera: 0).point.x, 430, accuracy: 0.001)
    }

    func testDraggingMovesTheGroundUnderTheFingerByTheFingersDistance() {
        let lens = TRVillageLens(width: 390, boardTop: 104, lip: 523)
        let fingerY = 400.0
        let ppu = lens.pointsPerUnit(atScreenY: fingerY)
        // Find the ground under the finger, then move the camera by 10 points' worth.
        var depth = 0.0
        while lens.project(x: 195, y: depth, camera: 0).point.y > fingerY { depth += 0.01 }
        let moved = lens.project(x: 195, y: depth, camera: 10 / ppu).point.y
        XCTAssertEqual(moved - fingerY, 10, accuracy: 0.2)
    }

    func testRoadSlopeMatchesItsBendsAsTheirSwingsVary() {
        for y in stride(from: -15.0, through: 900, by: 23) {
            let measured = (TRVillageRoad.roadX(y + 0.001) - TRVillageRoad.roadX(y - 0.001)) / 0.002
            XCTAssertEqual(TRVillageRoad.roadSlope(y), measured, accuracy: 0.01, "y \(y)")
        }
        // Bends swing by different amounts, but still cross the middle between houses.
        let swings = Set((0..<8).map { Int(abs(TRVillageRoad.roadX(Double($0) * 80) - 195)) })
        XCTAssertGreaterThan(swings.count, 3)
        XCTAssertEqual(TRVillageRoad.roadX(40), 195, accuracy: 0.001)
    }

    func testSceneryIsScatteredTheSameEveryTime() {
        let road = TRVillageRoad(levelCount: 12, currentLevel: 3)
        XCTAssertEqual(road.props(inBand: 5), TRVillageRoad(levelCount: 12, currentLevel: 9).props(inBand: 5))
        // Not the same layout in every band.
        let layouts = (1...8).map { road.props(inBand: $0).map { Int($0.x) } }
        XCTAssertEqual(Set(layouts).count, layouts.count)
        let kinds = Set((0...20).flatMap { road.props(inBand: $0).map { "\($0.kind)" } })
        XCTAssertEqual(kinds.count, 6)
    }

    func testSceneryKeepsOffTheRoadAndClearOfHousesAndSigns() {
        let road = TRVillageRoad(levelCount: 12, currentLevel: 12)
        for band in 0...14 {
            let props = road.props(inBand: band)
            XCTAssertGreaterThanOrEqual(props.count, 2, "band \(band)")
            for prop in props {
                XCTAssertGreaterThan(abs(prop.x - TRVillageRoad.roadX(prop.y)), prop.reach + 12, "band \(band) \(prop)")
                XCTAssert((Double(band) * 80...Double(band + 1) * 80).contains(prop.y))
                for level in max(band - 1, 0)...(band + 1) where level <= 12 {
                    let dx = abs(prop.x - TRVillageRoad.houseX(level)), dy = prop.y - TRVillageRoad.houseY(level)
                    XCTAssertFalse(dx < 30 && dy > -46 && dy < 16, "band \(band) \(prop) by house \(level)")
                }
                for sign in [band, band + 1] where road.signLabel(atBand: sign) != nil {
                    let dy = prop.y - Double(sign) * 80
                    XCTAssertFalse(abs(prop.x - 195) < 18 && dy > -38 && dy < 24, "band \(band) \(prop) by sign \(sign)")
                }
                if prop.kind == .pond {
                    for level in max(band - 1, 0)...(band + 1) where level <= 12 {
                        let dx = abs(prop.x - TRVillageRoad.houseX(level)), dy = prop.y - TRVillageRoad.houseY(level)
                        XCTAssertFalse(dx < 30 + prop.reach && dy > -46 && dy < 40, "band \(band) pond by house \(level)")
                    }
                }
            }
        }
        XCTAssertEqual(road.signLabel(atBand: 10), "Ch 2")
        XCTAssertEqual(road.signLabel(atBand: 13), "Soon")
        XCTAssertNil(road.signLabel(atBand: 4))
    }

    func testDriveChipHoldsSteadyThroughASlowUnevenDrag() {
        let motion = TRVillageMotion(camera: 0)
        var time = 0.0, y = 0.0
        // A brisk drive brings the chip up.
        for _ in 0..<30 {
            time += 1 / 60; y += 4
            motion.noteVan(atY: y, time: time)
        }
        XCTAssertEqual(motion.chip, 1, accuracy: 0.001)
        XCTAssertFalse(motion.isReversing)
        // Then a slow drag: moving every other frame, and now and then a frame back.
        var lowest = 1.0
        for frame in 0..<120 {
            time += 1 / 60
            y += frame % 2 == 0 ? 2.2 : (frame % 7 == 0 ? -0.6 : 0)
            motion.noteVan(atY: y, time: time)
            lowest = min(lowest, motion.chip)
            XCTAssertFalse(motion.isReversing, "frame \(frame)")
        }
        XCTAssertEqual(lowest, 1, accuracy: 0.001)
        // Stopped, it fades away.
        for _ in 0..<60 {
            time += 1 / 60
            motion.noteVan(atY: y, time: time)
        }
        XCTAssertEqual(motion.chip, 0)
    }
}
