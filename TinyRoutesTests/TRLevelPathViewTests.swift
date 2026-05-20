import XCTest
@testable import TinyRoutes

final class TRLevelPathViewTests: XCTestCase {
    private let layout = TRSerpentineLayout(
        tileSize: TRLevelTile.size,
        horizontalSpacing: 16,
        verticalSpacing: 24
    )

    private func makeLevel(_ number: Int) -> LevelData {
        LevelData(
            id: "level_\(String(format: "%03d", number))",
            name: "Level \(number)",
            graph: RouteGraph(),
            startNodeID: "start",
            packageNodeID: "package",
            destinationNodeID: "destination",
            timeLimitSeconds: 60,
            parTaps: 6
        )
    }

    private func makeLevels(_ count: Int) -> [LevelData] {
        (1...count).map { makeLevel($0) }
    }

    func testHorizontalSegmentsAreCreatedBetweenAdjacentTilesPerRow() {
        let positions = layout.positions(for: makeLevels(8))
        let states = Dictionary(uniqueKeysWithValues: positions.map { ($0.levelID, TRLevelTileState.current) })

        let segments = makeHorizontalSegments(positions: positions, tileStatesByLevelID: states)

        XCTAssertEqual(segments.count, 6)
    }

    func testSegmentUnlockStateUsesBothConnectedTileStates() {
        let positions = layout.positions(for: makeLevels(8))
        var states = Dictionary(uniqueKeysWithValues: positions.map { ($0.levelID, TRLevelTileState.locked) })
        [1, 2, 3, 4].forEach { number in
            states["level_\(String(format: "%03d", number))"] = .completed
        }

        let segments = makeHorizontalSegments(positions: positions, tileStatesByLevelID: states)

        let unlockedCount = segments.filter(\.isUnlocked).count
        XCTAssertEqual(unlockedCount, 3)
    }

    func testRowTransitionSegmentsConnectAdjacentRows() {
        let positions = layout.positions(for: makeLevels(12))
        let states = Dictionary(uniqueKeysWithValues: positions.map { ($0.levelID, TRLevelTileState.current) })

        let transitions = makeRowTransitionSegments(positions: positions, tileStatesByLevelID: states)

        XCTAssertEqual(transitions.count, 2)
    }

    func testRowTransitionSegmentsFollowSerpentineTurnDirection() {
        let positions = layout.positions(for: makeLevels(12))
        let states = Dictionary(uniqueKeysWithValues: positions.map { ($0.levelID, TRLevelTileState.current) })

        let transitions = makeRowTransitionSegments(positions: positions, tileStatesByLevelID: states)

        XCTAssertEqual(transitions.count, 2)
        XCTAssertGreaterThan(transitions[0].control1.x, transitions[0].start.x)
        XCTAssertLessThan(transitions[1].control1.x, transitions[1].start.x)
    }

    func testRowTransitionUnlockStateUsesBothConnectedTileStates() {
        let positions = layout.positions(for: makeLevels(12))
        var states = Dictionary(uniqueKeysWithValues: positions.map { ($0.levelID, TRLevelTileState.locked) })
        [4, 5].forEach { number in
            states["level_\(String(format: "%03d", number))"] = .completed
        }

        let transitions = makeRowTransitionSegments(positions: positions, tileStatesByLevelID: states)

        XCTAssertEqual(transitions.count, 2)
        XCTAssertTrue(transitions[0].isUnlocked)
        XCTAssertFalse(transitions[1].isUnlocked)
    }

    func testRowTransitionSegmentsUseRowAndColumnGeometryWhenInputOrderDiffers() {
        let levels = [makeLevel(10), makeLevel(2), makeLevel(1), makeLevel(5), makeLevel(4), makeLevel(9)]
        let positions = layout.positions(for: levels)
        let states = Dictionary(uniqueKeysWithValues: positions.map { ($0.levelID, TRLevelTileState.current) })
        let endpointInset: CGFloat = 6

        let transitions = makeRowTransitionSegments(
            positions: positions,
            tileStatesByLevelID: states,
            endpointInset: endpointInset
        )

        XCTAssertEqual(transitions.count, 1)
        let row0Rightmost = positions.filter { $0.row == 0 }.max { $0.column < $1.column }!
        let expectedX = row0Rightmost.center.x + TRLevelTile.size.width / 2 - endpointInset
        XCTAssertEqual(transitions[0].start.x, expectedX, accuracy: 0.001)
        XCTAssertEqual(transitions[0].end.x, expectedX, accuracy: 0.001)
    }

    func testRowTransitionEndpointsAnchorToTileEdges() {
        let positions = layout.positions(for: makeLevels(8))
        let states = Dictionary(uniqueKeysWithValues: positions.map { ($0.levelID, TRLevelTileState.current) })
        let endpointInset: CGFloat = 6
        let tileWidth = TRLevelTile.size.width

        let transitions = makeRowTransitionSegments(
            positions: positions,
            tileStatesByLevelID: states,
            endpointInset: endpointInset
        )

        XCTAssertEqual(transitions.count, 1)
        let expectedEdgeX = positions.first { $0.levelNumber == 4 }!.center.x + tileWidth / 2 - endpointInset
        XCTAssertEqual(transitions[0].start.x, expectedEdgeX, accuracy: 0.001)
        XCTAssertEqual(transitions[0].end.x, expectedEdgeX, accuracy: 0.001)
    }
}
