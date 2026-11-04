#if DEBUG || MULTIVAN_INTERNAL
import XCTest
@testable import TinyRoutes

final class MultiVanPerformanceMeterTests: XCTestCase {
    private let refresh = 1.0 / 60

    func testSteadySixtyHasNoHitches() {
        var stats = MultiVanPerformanceMeter.FrameStats()
        for _ in 0..<600 { stats.add(refresh) }
        XCTAssertEqual(stats.frames, 600)
        XCTAssertEqual(stats.seconds, 10, accuracy: 1e-9)
        XCTAssertEqual(stats.framesPerSecond, 60, accuracy: 1e-9)
        XCTAssertEqual(stats.hitches(refresh: refresh), 0)
        XCTAssertEqual(stats.percentile(0.95), refresh, accuracy: 1e-12)
    }

    func testLateFramesCountAsHitchesAndShowInTheTail() {
        var stats = MultiVanPerformanceMeter.FrameStats()
        for index in 0..<100 { stats.add(index < 90 ? refresh : refresh * 2) }
        // A frame 1.4 refreshes late is jitter, not a drop.
        stats.add(refresh * 1.4)
        XCTAssertEqual(stats.hitches(refresh: refresh), 10)
        XCTAssertEqual(stats.percentile(0.5), refresh, accuracy: 1e-12)
        XCTAssertEqual(stats.percentile(0.95), refresh * 2, accuracy: 1e-12)
        XCTAssertEqual(stats.percentile(1), refresh * 2, accuracy: 1e-12)
    }

    func testIgnoresNonsenseIntervalsAndEmptyStatsReadZero() {
        var stats = MultiVanPerformanceMeter.FrameStats()
        stats.add(0)
        stats.add(-1)
        stats.add(.infinity)
        XCTAssertEqual(stats, MultiVanPerformanceMeter.FrameStats())
        XCTAssertEqual(stats.framesPerSecond, 0)
        XCTAssertEqual(stats.percentile(0.95), 0)
    }

    func testRowsReportMillisecondsForOneBoardAndPhase() throws {
        var stats = MultiVanPerformanceMeter.FrameStats()
        [0.016, 0.017, 0.034].forEach { stats.add($0) }
        let row = MultiVanPerformanceMeter.FramesRow(source: "scenekit", label: "diorama run", uptime: 42, stats: stats, refresh: refresh)
        XCTAssertEqual(row.frames, 3)
        XCTAssertEqual(row.hitches, 1)
        XCTAssertEqual(row.p50Milliseconds, 17, accuracy: 1e-9)
        XCTAssertEqual(row.maxMilliseconds, 34, accuracy: 1e-9)
        let json = try XCTUnwrap(JSONSerialization.jsonObject(with: JSONEncoder().encode(row)) as? [String: Any])
        XCTAssertEqual(json["recordType"] as? String, "frames")
        XCTAssertEqual(json["label"] as? String, "diorama run")
    }

    func testOnlyAutoplayLaunchesMeasure() {
        XCTAssertNil(MultiVanPerformanceMeter.shared)
    }
}
#endif
