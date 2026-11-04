import XCTest
@testable import TinyRoutes

final class MultiVanBoardStyleTests: XCTestCase {
    func testResolverFollowsThePlanTable() {
        // Preference, Use 2D in Low Power Mode, Low Power Mode, board shown.
        let table: [(MultiVanBoardStyle, Bool, Bool, MultiVanBoardStyle)] = [
            (.flat, true, true, .flat), (.flat, true, false, .flat),
            (.flat, false, true, .flat), (.flat, false, false, .flat),
            (.diorama, true, true, .flat),
            (.diorama, true, false, .diorama),
            (.diorama, false, true, .diorama), (.diorama, false, false, .diorama)
        ]
        for (preference, flatInLowPower, lowPower, expected) in table {
            let label = "\(preference) / 2D in Low Power \(flatInLowPower) / Low Power \(lowPower)"
            XCTAssertEqual(MultiVanBoardStyle.resolve(
                preference: preference, flatInLowPower: flatInLowPower, isLowPowerMode: lowPower
            ), expected, label)
            let settings = UserSettings(boardStyle: preference, usesFlatBoardInLowPowerMode: flatInLowPower)
            XCTAssertEqual(MultiVanBoardStyle.resolve(settings: settings, isLowPowerMode: lowPower), expected, label)
        }
    }

    func testReduceAnimationsNeverChangesTheBoard() {
        for reduces in [false, true] {
            let settings = UserSettings(reducesExtraAnimations: reduces, boardStyle: .diorama)
            XCTAssertEqual(MultiVanBoardStyle.resolve(settings: settings, isLowPowerMode: false), .diorama)
        }
    }

    func testLowPowerModeSwapsStraightAwayOutsideARun() throws {
        let engine = try engine("level_002")
        var selection = MultiVanBoardSelection(showing: .diorama)
        XCTAssertEqual(engine.phase, .plan)
        selection.update(to: .flat, isAutomatic: true, phase: engine.phase)
        XCTAssertEqual(selection.shown, .flat)

        engine.go()
        finishRun(engine)
        XCTAssertEqual(engine.phase, .finished)
        selection.update(to: .diorama, isAutomatic: true, phase: engine.phase)
        XCTAssertEqual(selection.shown, .diorama)
    }

    func testLowPowerModeMidRunWaitsForTheRunToEnd() throws {
        let engine = try engine("level_002")
        var selection = MultiVanBoardSelection(showing: .diorama)
        engine.go()
        engine.advance(by: 0.5)
        XCTAssertEqual(engine.phase, .run)
        selection.update(to: .flat, isAutomatic: true, phase: engine.phase)
        XCTAssertEqual(selection.shown, .diorama, "No camera jump while vans are driving")

        // The switcher re-applies the current target whenever the phase changes.
        finishRun(engine)
        selection.update(to: .flat, isAutomatic: true, phase: engine.phase)
        XCTAssertEqual(selection.shown, .flat)

        // Stopping a run early also counts as the run ending.
        engine.retry()
        engine.go()
        XCTAssertEqual(engine.phase, .run)
        selection.update(to: .diorama, isAutomatic: true, phase: engine.phase)
        XCTAssertEqual(selection.shown, .flat)
        engine.stop()
        selection.update(to: .diorama, isAutomatic: true, phase: engine.phase)
        XCTAssertEqual(selection.shown, .diorama)
    }

    func testLowPowerModeFlickeringMidRunEndsWithNoSwap() throws {
        let engine = try engine("level_002")
        var selection = MultiVanBoardSelection(showing: .diorama)
        engine.go()
        selection.update(to: .flat, isAutomatic: true, phase: engine.phase)
        selection.update(to: .diorama, isAutomatic: true, phase: engine.phase)
        finishRun(engine)
        selection.update(to: .diorama, isAutomatic: true, phase: engine.phase)
        XCTAssertEqual(selection.shown, .diorama)
    }

    func testPlayerChoicesApplyEvenMidRun() throws {
        let engine = try engine("level_002")
        var selection = MultiVanBoardSelection(showing: .flat)
        engine.go()
        selection.update(to: .diorama, isAutomatic: false, phase: engine.phase)
        XCTAssertEqual(selection.shown, .diorama)
    }

    func testSwitchSettingsSurviveEverySwap() throws {
        let engine = try engine("level_012")
        for node in MultiVanBoardRules.switchNodes(in: engine.runtimeGraph) {
            XCTAssertEqual(engine.tapSwitch(nodeID: node.id), .accepted)
        }
        func settings() -> [String: String?] {
            Dictionary(uniqueKeysWithValues: MultiVanBoardRules.switchNodes(in: engine.runtimeGraph).map {
                ($0.id, $0.activeOutgoingEdgeID)
            })
        }
        let planned = settings()
        let changes = engine.changeCount
        XCTAssertGreaterThan(changes, 0)

        // Swaps in every phase, both automatic and the player's own.
        var selection = MultiVanBoardSelection(showing: .diorama)
        for (target, isAutomatic) in [(MultiVanBoardStyle.flat, true), (.diorama, false), (.flat, false)] {
            selection.update(to: target, isAutomatic: isAutomatic, phase: engine.phase)
            XCTAssertEqual(selection.shown, target)
            XCTAssertEqual(settings(), planned)
            XCTAssertEqual(engine.changeCount, changes)
        }
        engine.go()
        selection.update(to: .diorama, isAutomatic: true, phase: engine.phase)
        selection.update(to: .diorama, isAutomatic: false, phase: engine.phase)
        XCTAssertEqual(selection.shown, .diorama)
        engine.stop()
        selection.update(to: .flat, isAutomatic: true, phase: engine.phase)
        XCTAssertEqual(settings(), planned)
        XCTAssertEqual(engine.changeCount, changes)
        // Both boards list their switches from the same engine, so they agree after a swap.
        XCTAssertEqual(MultiVanSwitchControl.controls(engine: engine, graph: engine.runtimeGraph).map(\.activeAngle),
                       MultiVanBoardRules.switchNodes(in: engine.runtimeGraph).map { node in
                           let edge = engine.runtimeGraph.edgesByID[node.activeOutgoingEdgeID!]!
                           return SwitchArrowDirectionResolver.directionAngle(for: edge, from: node, in: engine.runtimeGraph)
                       })
    }

    private func engine(_ id: String) throws -> MultiVanEngine {
        let level = try XCTUnwrap(MultiVanLevelRepository().loadAllLevels().first { $0.id == id })
        return try MultiVanEngine(level: level)
    }

    private func finishRun(_ engine: MultiVanEngine) {
        for _ in 0..<600 where engine.outcome == nil {
            engine.advance(by: 0.1)
        }
        XCTAssertNotNil(engine.outcome)
    }
}

@MainActor
final class MultiVanPowerMonitorTests: XCTestCase {
    /// Stands in for ProcessInfo; it records which thread reads it.
    private final class FakePowerState: @unchecked Sendable {
        private let lock = NSLock()
        private var value = false
        private var reads: [Bool] = []

        func set(_ enabled: Bool) { lock.withLock { value = enabled } }

        func read() -> Bool {
            lock.withLock {
                reads.append(Thread.isMainThread)
                return value
            }
        }

        var readCount: Int { lock.withLock { reads.count } }
        var everyReadWasOnTheMainThread: Bool { lock.withLock { reads.allSatisfy { $0 } } }
    }

    func testStartsFromTheCurrentValue() {
        XCTAssertTrue(MultiVanPowerMonitor(readsLowPowerMode: { true }).isLowPowerModeEnabled)
        XCTAssertFalse(MultiVanPowerMonitor(readsLowPowerMode: { false }).isLowPowerModeEnabled)
    }

    func testNotificationsFromAnyThreadPublishOnTheMainActor() async throws {
        let center = NotificationCenter()
        let state = FakePowerState()
        let monitor = MultiVanPowerMonitor(readsLowPowerMode: { state.read() })
        let listening = Task { await monitor.monitor(center: center) }
        defer { listening.cancel() }

        // One read at init, one when listening starts; only then does the value change.
        for _ in 0..<200 where state.readCount < 2 { try await Task.sleep(for: .milliseconds(5)) }
        XCTAssertEqual(state.readCount, 2)
        XCTAssertFalse(monitor.isLowPowerModeEnabled)
        state.set(true)
        // Repost until heard, in case the observer is still registering.
        for _ in 0..<100 where !monitor.isLowPowerModeEnabled {
            DispatchQueue.global().async { center.post(name: .NSProcessInfoPowerStateDidChange, object: nil) }
            try await Task.sleep(for: .milliseconds(10))
        }
        XCTAssertTrue(monitor.isLowPowerModeEnabled)
        XCTAssertTrue(state.everyReadWasOnTheMainThread)
    }

    func testCancellingTheTaskStopsListening() async throws {
        let center = NotificationCenter()
        let state = FakePowerState()
        let monitor = MultiVanPowerMonitor(readsLowPowerMode: { state.read() })
        let listening = Task { await monitor.monitor(center: center) }
        for _ in 0..<200 where state.readCount < 2 { try await Task.sleep(for: .milliseconds(5)) }

        listening.cancel()
        let ended = expectation(description: "monitor returns once its task is cancelled")
        Task {
            await listening.value
            ended.fulfill()
        }
        await fulfillment(of: [ended], timeout: 2)
        state.set(true)
        center.post(name: .NSProcessInfoPowerStateDidChange, object: nil)
        try await Task.sleep(for: .milliseconds(50))
        XCTAssertFalse(monitor.isLowPowerModeEnabled)
    }
}
