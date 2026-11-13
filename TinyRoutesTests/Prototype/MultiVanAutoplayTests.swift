#if DEBUG || MULTIVAN_INTERNAL
import Foundation
import XCTest
@testable import TinyRoutes

final class MultiVanAutoplayTests: XCTestCase {
    private var root: URL {
        URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent()
    }

    private func level(_ id: String) throws -> MultiVanLevel {
        let url = root.appendingPathComponent("TinyRoutes/Resources/PrototypeLevels/\(id).json")
        return try JSONDecoder().decode(MultiVanLevel.self, from: Data(contentsOf: url))
    }

    /// The launch option as the profiling script builds it: the solution file's
    /// taps plus the level and board.
    private func autoplay(_ id: String, board: MultiVanBoardStyle = .diorama) throws -> MultiVanAutoplay {
        let url = root.appendingPathComponent("TinyRoutesTests/Resources/PrototypeSolutions/\(id).solution.json")
        var script = try XCTUnwrap(JSONSerialization.jsonObject(with: Data(contentsOf: url)) as? [String: Any])
        script["levelID"] = id
        script["board"] = board.rawValue
        let json = String(decoding: try JSONSerialization.data(withJSONObject: script), as: UTF8.self)
        return try XCTUnwrap(MultiVanAutoplay.configuration(from: json))
    }

    func testDecodesTheLaunchOptionWithDefaults() throws {
        let autoplay = try XCTUnwrap(MultiVanAutoplay.configuration(from: #"{"levelID": "level_005", "board": "flat"}"#))
        XCTAssertEqual(autoplay, MultiVanAutoplay(levelID: "level_005", board: .flat))
        XCTAssertEqual(autoplay.planSeconds, 4)
        XCTAssertEqual(autoplay.resultSeconds, 4)
        let timed = try XCTUnwrap(MultiVanAutoplay.configuration(
            from: #"{"levelID": "level_014", "board": "diorama", "planSeconds": 2, "liveTaps": [{"atTime": 5.25, "nodeID": "split_switch"}]}"#
        ))
        XCTAssertEqual(timed.planSeconds, 2)
        XCTAssertEqual(timed.liveTaps, [.init(atTime: 5.25, nodeID: "split_switch")])
        XCTAssertNil(MultiVanAutoplay.configuration(from: nil))
        XCTAssertNil(MultiVanAutoplay.configuration(from: "level_014"))
        XCTAssertNil(MultiVanAutoplay.configuration(from: #"{"levelID": "level_014", "board": "hologram"}"#))
        let json = #"{"levelID": "level_005", "board": "flat"}"#
        XCTAssertEqual(MultiVanAutoplay.configuration(arguments: ["TinyRoutes", "-MultiVanAutoplay", json]), autoplay)
        XCTAssertNil(MultiVanAutoplay.configuration(arguments: ["TinyRoutes", "-MultiVanAutoplay"]))
        XCTAssertNil(MultiVanAutoplay.configuration(arguments: ["TinyRoutes", json]))
        // Tests never launch with the option.
        XCTAssertNil(MultiVanAutoplay.launchConfiguration)
    }

    func testPinsItsBoardWithoutTouchingOtherSettings() {
        var saved = UserSettings.defaultValue
        saved.boardStyle = .flat
        saved.usesFlatBoardInLowPowerMode = true
        let pinned = MultiVanAutoplay(levelID: "level_001", board: .diorama).settings(from: saved)
        XCTAssertEqual(MultiVanBoardStyle.resolve(settings: pinned, isLowPowerMode: true), .diorama)
        var expected = saved
        expected.boardStyle = .diorama
        expected.usesFlatBoardInLowPowerMode = false
        XCTAssertEqual(pinned, expected)
    }

    /// Drives the engine as the gameplay screen does, one display frame at a time,
    /// and returns each finished run's outcome and change count.
    private func loop(_ autoplay: MultiVanAutoplay, runs: Int, frame: Double) throws -> [(MultiVanEngine.Outcome?, Int)] {
        let engine = try MultiVanEngine(level: level(autoplay.levelID))
        let driver = MultiVanAutoplayDriver(autoplay)
        var now = 0.0, results: [(MultiVanEngine.Outcome?, Int)] = []
        while results.count < runs, now < 600 {
            switch driver.nextPress(engine: engine, now: now) {
            case .resetSwitches: engine.resetSwitches()
            case let .tap(nodeID): XCTAssertEqual(engine.tapSwitch(nodeID: nodeID), .accepted, "\(autoplay.levelID) \(nodeID)")
            case .go: engine.go()
            case .retry:
                results.append((engine.outcome, engine.changeCount))
                engine.retry()
            case nil: break
            }
            now += frame
            if engine.phase == .run { engine.advance(by: frame) }
            _ = engine.drainEvents()
        }
        return results
    }

    func testEverySolutionWinsAtParOnEveryLoopAtSixtyAndThirtyFramesASecond() throws {
        for number in 1...14 {
            let id = String(format: "level_%03d", number)
            let autoplay = try autoplay(id)
            let par = try level(id).parChanges
            for frame in [1.0 / 60, 1.0 / 30] {
                let results = try loop(autoplay, runs: 3, frame: frame)
                XCTAssertEqual(results.count, 3, id)
                for (outcome, changes) in results {
                    XCTAssertEqual(outcome, .win, "\(id) at \(Int(1 / frame)) fps")
                    // Reset switches undoes the last run, so each loop starts fresh.
                    XCTAssertEqual(changes, par, "\(id) at \(Int(1 / frame)) fps")
                }
            }
        }
    }

    func testPlanTapsSpreadAcrossThePlanBeforeGo() throws {
        let autoplay = MultiVanAutoplay(levelID: "level_014", board: .flat, planTaps: ["a", "b", "c"], planSeconds: 4)
        let engine = try MultiVanEngine(level: level("level_014"))
        let driver = MultiVanAutoplayDriver(autoplay)
        var presses: [(Double, MultiVanAutoplayDriver.Press)] = []
        for tick in 0...40 { // Go repeats until the engine leaves the plan.
            let now = Double(tick) / 10
            if let press = driver.nextPress(engine: engine, now: now) { presses.append((now, press)) }
        }
        XCTAssertEqual(presses.map(\.1), [.resetSwitches, .tap("a"), .tap("b"), .tap("c"), .go])
        XCTAssertEqual(presses.map(\.0), [0, 1, 2, 3, 4])
    }
}
#endif
