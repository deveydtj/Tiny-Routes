import Foundation
import XCTest
@testable import TinyRoutes

final class MultiVanPlaytestLogTests: XCTestCase {
    private final class Clock { var now = 100.0 }
    private final class Rig {
        let directory: URL
        let clock = Clock()
        let log: MultiVanPlaytestLog

        init() throws {
            directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
            try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
            let clock = self.clock
            log = MultiVanPlaytestLog(fileURL: directory.appendingPathComponent("playtest.jsonl"),
                uptime: { clock.now }, wallTime: { Date(timeIntervalSince1970: 1_800_000_000) })
        }

        deinit { log.flush(); try? FileManager.default.removeItem(at: directory) }

        func rows() throws -> [[String: Any]] {
            log.flush()
            XCTAssertNil(log.writeError)
            let data = try String(contentsOf: log.fileURL, encoding: .utf8)
            XCTAssertTrue(data.hasSuffix("\n"))
            return try data.split(separator: "\n").map {
                try XCTUnwrap(JSONSerialization.jsonObject(with: Data($0.utf8)) as? [String: Any])
            }
        }

        func attempts() throws -> [MultiVanPlaytestLog.Attempt] {
            log.flush()
            let decoder = JSONDecoder()
            decoder.dateDecodingStrategy = .iso8601
            return try String(contentsOf: log.fileURL, encoding: .utf8).split(separator: "\n").compactMap {
                let data = Data($0.utf8)
                let row = try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])
                return row["recordType"] as? String == "attempt" ? try decoder.decode(MultiVanPlaytestLog.Attempt.self, from: data) : nil
            }
        }
    }

    private var root: URL {
        URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent()
    }

    private func engine(_ id: String = "level_009") throws -> MultiVanEngine {
        let url = root.appendingPathComponent("TinyRoutes/Resources/PrototypeLevels/\(id).json")
        return try MultiVanEngine(level: JSONDecoder().decode(MultiVanLevel.self, from: Data(contentsOf: url)))
    }

    private func tap(_ engine: MultiVanEngine, _ log: MultiVanPlaytestLog, _ node: String) -> MultiVanTapResult {
        let result = engine.tapSwitch(nodeID: node)
        log.switchTapped(engine, nodeID: node, result: result)
        process(engine, log)
        return result
    }

    private func process(_ engine: MultiVanEngine, _ log: MultiVanPlaytestLog) {
        // Mirrors the existing single-drain dispatcher, preserving batch order.
        for event in engine.drainEvents() { log.observe(event, engine: engine) }
        log.completed(engine)
    }

    private func go(_ engine: MultiVanEngine, _ log: MultiVanPlaytestLog) {
        log.go(engine)
        engine.go()
        process(engine, log)
    }

    func testInitializesLazilyWithAnonymousSessionAndNoFile() throws {
        let a = try Rig(), b = try Rig()
        XCTAssertNotEqual(a.log.sessionID, b.log.sessionID)
        XCTAssertNil(a.log.lastAttempt)
        XCTAssertFalse(FileManager.default.fileExists(atPath: a.log.fileURL.path))
        XCTAssertNil(a.log.writeError)
    }

    func testPlanningTapResetAndStopUseRealPlanTimeAndConfigurationCount() throws {
        let rig = try Rig(), run = try engine()
        rig.log.open(run)
        rig.clock.now += 3
        XCTAssertEqual(tap(run, rig.log, "entry_switch"), .accepted)
        run.resetSwitches()
        rig.log.record(.reset, engine: run)
        XCTAssertEqual(tap(run, rig.log, "entry_switch"), .accepted)
        rig.clock.now += 4
        go(run, rig.log)
        run.advance(by: 0.5)
        rig.clock.now += 0.5
        rig.log.stop(run)
        let row = try XCTUnwrap(rig.log.lastAttempt)
        XCTAssertEqual(row.planRealSeconds, 7)
        XCTAssertEqual(row.simulationEndTime, 0.5)
        XCTAssertEqual(row.outcome, "stopped")
        XCTAssertEqual(row.changes, run.changeCount)
        XCTAssertEqual(row.events.map(\.action), [.levelStarted, .switchTap, .reset, .switchTap, .go, .stop])
        let first = row.events[1]
        XCTAssertEqual(first.phase, "plan")
        XCTAssertEqual(first.observedSimulationTime, 0)
        XCTAssertEqual(first.elapsedRealSeconds, 3)
        XCTAssertEqual(first.tapResult, "accepted")
        XCTAssertNotNil(first.selectedEdgeID)
        XCTAssertEqual(try rig.attempts(), [row])
    }

    func testStopAndRetryAttemptsHaveDistinctBoundariesAndKeepSettings() throws {
        let rig = try Rig(), run = try engine("level_007")
        rig.log.open(run)
        go(run, rig.log)
        run.advance(by: 0.5)
        rig.log.stop(run)
        let settings = run.changeCount
        run.stop()
        rig.log.begin(run, action: .planningStarted)
        XCTAssertEqual(run.changeCount, settings)
        go(run, rig.log)
        run.advance(by: 30)
        process(run, rig.log)
        XCTAssertEqual(rig.log.lastAttempt?.failReason, "collision")
        run.retry()
        rig.log.begin(run, action: .retry)
        rig.log.leaveLevel(run, reason: "level_list")
        let rows = try rig.attempts()
        XCTAssertEqual(rows.map(\.attemptNumber), [1, 2, 3])
        XCTAssertEqual(Set(rows.map(\.levelSessionID)).count, 1)
        XCTAssertEqual(rows.map(\.outcome), ["stopped", "failure", "abandoned"])
        XCTAssertEqual(rows[2].events.first?.action, .retry)
        XCTAssertEqual(rows[0].simulationEndTime, 0.5)
        XCTAssertEqual(rows[2].initialSimulationTime, 0)
    }

    func testRunningAcceptedFrozenAndTemporaryLockResultsUseEngineTime() throws {
        let rig = try Rig(), run = try engine()
        rig.log.open(run)
        XCTAssertEqual(tap(run, rig.log, "entry_switch"), .accepted)
        go(run, rig.log)
        let before = run.changeCount
        XCTAssertEqual(tap(run, rig.log, "entry_switch"), .rejectedFrozen)
        XCTAssertEqual(run.changeCount, before)
        run.advance(by: 1.25)
        let edge = run.runtimeGraph.nodesByID["switch"]?.activeOutgoingEdgeID
        XCTAssertEqual(tap(run, rig.log, "switch"), .rejectedLocked)
        XCTAssertEqual(run.runtimeGraph.nodesByID["switch"]?.activeOutgoingEdgeID, edge)
        XCTAssertEqual(run.changeCount, before)
        run.advance(by: 1)
        XCTAssertEqual(tap(run, rig.log, "switch"), .accepted)
        rig.log.leaveLevel(run, reason: "test")
        let taps = try XCTUnwrap(rig.log.lastAttempt).events.filter { $0.action == .switchTap }
        XCTAssertEqual(taps.map(\.tapResult), ["accepted", "rejected_frozen", "rejected_locked", "accepted"])
        XCTAssertEqual(taps.map(\.observedSimulationTime), [0, 0, 1.25, 2.25])
        XCTAssertEqual(taps.map(\.phase), ["plan", "run", "run", "run"])
        XCTAssertEqual(taps[2].selectedEdgeID, edge)
    }

    func testWrongHouseAndStuckAreDistinctAndNotTimeoutGuesses() throws {
        for (id, reason) in [("level_009", "wrong_house"), ("level_002", "stuck")] {
            let rig = try Rig(), run = try engine(id)
            rig.log.open(run)
            if id == "level_009" { XCTAssertEqual(tap(run, rig.log, "entry_switch"), .accepted) }
            go(run, rig.log)
            run.advance(by: 30)
            process(run, rig.log)
            XCTAssertEqual(rig.log.lastAttempt?.outcome, "failure")
            XCTAssertEqual(rig.log.lastAttempt?.failReason, reason)
            XCTAssertNil(rig.log.lastAttempt?.stars)
            XCTAssertEqual(try rig.attempts().count, 1)
        }
    }

    func testAbandonedPlanningRunAndRepeatedExitCallbacks() throws {
        for running in [false, true] {
            let rig = try Rig(), run = try engine()
            rig.log.open(run)
            rig.clock.now += 5
            if running { go(run, rig.log); run.advance(by: 0.25) }
            rig.clock.now += 1
            rig.log.leaveLevel(run, reason: "level_list")
            rig.log.leaveLevel(run, reason: "level_list")
            rig.log.quit(engine: nil, reason: "prototype_closed")
            rig.log.quit(engine: nil, reason: "prototype_dismissed")
            let attempts = try rig.attempts()
            XCTAssertEqual(attempts.count, 1)
            XCTAssertEqual(attempts[0].outcome, "abandoned")
            XCTAssertEqual(attempts[0].endReason, "level_list")
            XCTAssertEqual(attempts[0].planRealSeconds, running ? 5 : 6)
            XCTAssertEqual(attempts[0].simulationEndTime, running ? 0.25 : 0)
            let quits = try rig.rows().filter { $0["recordType"] as? String == "quit_at_level" }
            XCTAssertEqual(quits.count, 1)
            XCTAssertEqual(quits[0]["levelID"] as? String, run.level.id)
        }
    }

    func testBackgroundFinalizesAndResumeExcludesBackgroundTimeWithoutResettingRun() throws {
        let rig = try Rig(), run = try engine()
        rig.log.open(run)
        go(run, rig.log)
        run.advance(by: 0.25)
        rig.clock.now += 0.25
        rig.log.speedChanged(true, engine: run)
        rig.clock.now += 0.25
        run.advance(by: 0.5)
        rig.log.quit(engine: run, reason: "background")
        let position = run.vans.map(\.position)
        rig.clock.now += 100
        rig.log.resume(run)
        rig.log.resume(run)
        XCTAssertEqual(run.vans.map(\.position), position)
        rig.clock.now += 0.5
        rig.log.leaveLevel(run, reason: "level_list")
        let rows = try rig.attempts()
        XCTAssertEqual(rows.map(\.attemptNumber), [1, 2])
        XCTAssertEqual(rows[0].elapsedRealSeconds, 0.5)
        XCTAssertEqual(rows[0].fastForwardRealSeconds, 0.25)
        XCTAssertEqual(rows[1].elapsedRealSeconds, 0.5)
        XCTAssertEqual(rows[1].initialSimulationTime, 0.75)
        XCTAssertEqual(rows[1].events.first?.action, .resume)
        XCTAssertEqual(rows[1].planRealSeconds, 0)
    }

    func testFastForwardKeepsSeparateRealAndSimulationDurationsAndCountsTransitions() throws {
        let rig = try Rig(), run = try engine()
        rig.log.open(run)
        XCTAssertEqual(tap(run, rig.log, "entry_switch"), .accepted)
        go(run, rig.log)
        rig.log.speedChanged(true, engine: run)
        rig.log.speedChanged(true, engine: run)
        rig.clock.now += 0.5
        run.advance(by: 1)
        rig.log.speedChanged(false, engine: run)
        rig.clock.now += 0.25
        run.advance(by: 0.25)
        rig.log.speedChanged(true, engine: run)
        rig.clock.now += 0.25
        run.advance(by: 0.5)
        rig.log.stop(run)
        let row = try XCTUnwrap(rig.log.lastAttempt)
        XCTAssertEqual(row.fastForwardUseCount, 2)
        XCTAssertEqual(row.fastForwardRealSeconds, 0.75)
        XCTAssertEqual(row.fastForwardSimulationSeconds, 1.5)
        XCTAssertEqual(row.simulationEndTime, 1.75)
        XCTAssertEqual(row.elapsedRealSeconds, 1)
        XCTAssertEqual(row.events.filter { $0.action == .speedChanged }.map(\.speedMultiplier), [2, 1, 2])
    }

    func testLevelIsolationReopenNumbersAndStaleCallbacks() throws {
        let rig = try Rig(), a = try engine("level_007"), b = try engine("level_009")
        rig.log.open(a)
        rig.log.leaveLevel(a, reason: "level_changed")
        rig.log.open(b)
        rig.log.switchTapped(a, nodeID: "route_switch", result: .accepted)
        rig.log.leaveLevel(b, reason: "level_list")
        let reopened = try engine("level_007")
        rig.log.open(reopened)
        rig.log.leaveLevel(a, reason: "stale") // Same level ID, different engine.
        rig.log.leaveLevel(reopened, reason: "level_list")
        let rows = try rig.attempts()
        XCTAssertEqual(rows.map(\.levelID), ["level_007", "level_009", "level_007"])
        XCTAssertEqual(rows.map(\.attemptNumber), [1, 1, 2])
        XCTAssertEqual(Set(rows.map(\.levelSessionID)).count, 3)
        XCTAssertTrue(rows.allSatisfy { !$0.events.contains { $0.action == .switchTap } })
    }

    func testSessionNavigationRetainsThreeLevelRecordsAndQuitFromList() throws {
        let rig = try Rig()
        var session = MultiVanPrototypeSession(playtestLog: rig.log)
        let levels = try [engine("level_001").level, engine("level_002").level, engine("level_003").level]
        try session.open(levels[0])
        try session.next(in: levels)
        try session.next(in: levels)
        session.returnToList()
        session.playtestLog.quit(engine: session.engine, reason: "prototype_closed")
        let rows = try rig.attempts()
        XCTAssertEqual(rows.map(\.levelID), levels.map(\.id))
        XCTAssertEqual(rows.map(\.attemptNumber), [1, 1, 1])
        XCTAssertEqual(rows.map(\.endReason), ["level_changed", "level_changed", "level_list"])
        XCTAssertEqual(Set(rows.map(\.sessionID)), [rig.log.sessionID])
        XCTAssertEqual(try rig.rows().last?["levelID"] as? String, "level_003")
        XCTAssertNil(session.engine)
    }

    func testDecisionMemoryIsBoundedAndSummaryRemainsExact() throws {
        let rig = try Rig(), run = try engine()
        rig.log.open(run)
        for _ in 0..<1100 { _ = tap(run, rig.log, "entry_switch") }
        rig.log.leaveLevel(run, reason: "test")
        let row = try XCTUnwrap(rig.log.lastAttempt)
        XCTAssertEqual(row.events.count, 1024)
        XCTAssertEqual(row.omittedEventCount, 78)
        XCTAssertEqual(row.changes, run.changeCount)
        XCTAssertEqual(row.finalSwitchEdges["entry_switch"], run.runtimeGraph.nodesByID["entry_switch"]?.activeOutgoingEdgeID)
    }

    func testFileAppendSerializationPrivacyAndWriteFailure() throws {
        let rig = try Rig(), run = try engine()
        rig.log.open(run)
        rig.log.leaveLevel(run, reason: "test")
        let second = MultiVanPlaytestLog(fileURL: rig.log.fileURL)
        second.open(run)
        second.leaveLevel(run, reason: "test")
        second.flush()
        let rows = try rig.rows()
        XCTAssertEqual(rows.count, 2)
        XCTAssertNotEqual(rows[0]["sessionID"] as? String, rows[1]["sessionID"] as? String)
        XCTAssertEqual(rows[0]["timestamp"] as? String, "2027-01-15T08:00:00Z")
        XCTAssertEqual(rows[0]["schemaVersion"] as? Int, 2)
        let keys = Set(rows[0].keys)
        XCTAssertTrue(keys.isDisjoint(with: ["name", "email", "deviceID", "location", "advertisingID"]))
        let bad = MultiVanPlaytestLog(fileURL: rig.directory.appendingPathComponent("missing/log.jsonl"))
        bad.open(run)
        bad.leaveLevel(run, reason: "test")
        bad.flush()
        XCTAssertNotNil(bad.writeError)
        XCTAssertEqual(run.phase, .plan)
    }

    func testAllTwelveAuthoredSolutionsWinAtParAndMatchUnloggedEngineExactly() throws {
        for number in 1...12 {
            let id = String(format: "level_%03d", number)
            let rig = try Rig(), run = try engine(id)
            let url = root.appendingPathComponent("TinyRoutesTests/Resources/PrototypeSolutions/\(id).solution.json")
            let script = try JSONDecoder().decode(PrototypeSolutionScript.self, from: Data(contentsOf: url))
            let reference = try PrototypeSolutionRunner.verify(level: run.level, script: script)
            rig.log.open(run)
            for node in script.planTaps { XCTAssertEqual(tap(run, rig.log, node), .accepted, id) }
            go(run, rig.log)
            var index = 0
            while run.phase == .run && run.runTime < 120 {
                while index < script.liveTaps.count && script.liveTaps[index].atTime <= run.runTime {
                    XCTAssertEqual(tap(run, rig.log, script.liveTaps[index].nodeID), .accepted, id)
                    index += 1
                }
                run.advance(by: run.tuning.stepDuration)
                process(run, rig.log)
            }
            XCTAssertEqual(run.outcome, .win, id)
            XCTAssertEqual(run.outcome, reference.outcome, id)
            XCTAssertEqual(run.runTime, reference.runTime, id)
            XCTAssertEqual(run.changeCount, reference.changeCount, id)
            XCTAssertEqual(run.changeCount, run.level.parChanges, id)
            XCTAssertEqual(run.vans.map(\.position), reference.vans.map(\.position), id)
            XCTAssertEqual(run.vans.map(\.status), reference.vans.map(\.status), id)
            let row = try XCTUnwrap(rig.log.lastAttempt)
            XCTAssertEqual(row.outcome, "success", id)
            XCTAssertEqual(row.stars, 3, id)
            XCTAssertEqual(row.simulationEndTime, reference.runTime, id)
            XCTAssertEqual(row.changesMinusPar, 0, id)
            XCTAssertEqual(row.events.filter { $0.action == .delivered }.count, run.level.vans.count, id)
            let live = row.events.filter { $0.action == .switchTap && $0.phase == "run" }
            XCTAssertEqual(live.map(\.observedSimulationTime), script.liveTaps.map(\.atTime), id)
            XCTAssertEqual(live.map(\.nodeID), script.liveTaps.map(\.nodeID), id)
            for _ in 0..<5 { process(run, rig.log) } // Repeated callbacks cannot refinalize.
            XCTAssertEqual(try rig.attempts().count, 1, id)
            if number == 1 {
                run.retry()
                rig.log.begin(run, action: .replay)
                rig.log.leaveLevel(run, reason: "test")
                XCTAssertEqual(try rig.attempts().last?.events.first?.action, .replay)
            }
        }
    }

    func testMergeCollisionThenCorrectionAreSeparateFailureAndSuccess() throws {
        let rig = try Rig(), run = try engine("level_007")
        rig.log.open(run)
        go(run, rig.log)
        run.advance(by: 30)
        process(run, rig.log)
        guard case .failCrash = run.outcome else { return XCTFail("Expected authored initial crash") }
        run.retry()
        rig.log.begin(run, action: .retry)
        XCTAssertEqual(tap(run, rig.log, "route_switch"), .accepted)
        go(run, rig.log)
        run.advance(by: 30)
        process(run, rig.log)
        let rows = try rig.attempts()
        XCTAssertEqual(rows.map(\.outcome), ["failure", "success"])
        XCTAssertEqual(rows.map(\.failReason), ["collision", nil])
        XCTAssertEqual(rows.map(\.attemptNumber), [1, 2])
        XCTAssertEqual(rows[1].stars, 3)
    }

    func testBatchedDeliveryOrderAndCompletionArePreserved() throws {
        let rig = try Rig(), run = try engine("level_010")
        rig.log.open(run)
        for node in ["red_switch", "blue_switch", "yellow_switch"] { _ = tap(run, rig.log, node) }
        go(run, rig.log)
        run.advance(by: 30) // Multiple deliveries arrive in one dispatch batch.
        let events = run.drainEvents()
        for event in events { rig.log.observe(event, engine: run) }
        rig.log.completed(run)
        let row = try XCTUnwrap(rig.log.lastAttempt)
        let deliveries = events.compactMap { event -> String? in
            if case let .delivered(vanID, _) = event { return vanID }; return nil
        }
        XCTAssertEqual(row.events.filter { $0.action == .delivered }.map(\.vanID), deliveries)
        XCTAssertEqual(Array(row.events.suffix(2)).map(\.action), [.allDelivered, .completed])
        XCTAssertTrue(zip(row.events, row.events.dropFirst()).allSatisfy { $0.elapsedRealSeconds <= $1.elapsedRealSeconds })
    }

    func testUIIntegrationUsesActionBoundariesAndSingleFeedbackDrain() throws {
        let screen = try String(contentsOf: root.appendingPathComponent("TinyRoutes/Prototype/MultiVanGameplayScreen.swift"))
        let button = try String(contentsOf: root.appendingPathComponent("TinyRoutes/Prototype/MultiVanSwitchButton.swift"))
        let logger = try String(contentsOf: root.appendingPathComponent("TinyRoutes/Prototype/MultiVanPlaytestLog.swift"))
        XCTAssertEqual(screen.components(separatedBy: "drainEvents: engine.drainEvents").count - 1, 1)
        XCTAssertFalse(logger.contains(".drainEvents("))
        XCTAssertEqual(button.components(separatedBy: "engine.tapSwitch(nodeID: control.nodeID)").count - 1, 1)
        XCTAssertTrue(button.contains("let result = engine.tapSwitch(nodeID: control.nodeID)\n        onSwitchTapped?(control.nodeID, result)\n        onEventsProduced?()"))
        XCTAssertEqual(screen.components(separatedBy: "playtestLog?.switchTapped(").count - 1, 1)
        XCTAssertTrue(screen.contains("playtestLog?.go(engine)\n        engine.go()"))
        XCTAssertTrue(screen.contains("playtestLog?.stop(engine)"))
        XCTAssertTrue(screen.contains("playtestLog?.completed(engine)"))
        XCTAssertTrue(screen.contains(".onChange(of: voiceOverEnabled) { _, _ in\n            frameDriver.reset()\n            playtestLog?.speedChanged(false, engine: engine)"))
    }

    private func expectExportError(_ expected: MultiVanPlaytestLog.ExportError,
                                   log: MultiVanPlaytestLog, directory: URL? = nil) async {
        do {
            _ = try await log.prepareExport(in: directory)
            XCTFail("Expected export preparation to fail")
        } catch let error as MultiVanPlaytestLog.ExportError {
            XCTAssertEqual(error.localizedDescription, expected.localizedDescription)
            XCTAssertFalse(error.localizedDescription.isEmpty)
        } catch { XCTFail("Unexpected error: \(error)") }
    }

    func testExportAwaitsPendingWritesPreservesOrderAndAllowsContinuedLogging() async throws {
        let rig = try Rig(), run = try engine()
        rig.log.open(run)
        for number in 1...50 {
            rig.log.leaveLevel(run, reason: "test")
            if number < 50 { rig.log.begin(run, action: .retry) }
        }
        // Intentionally no test-side flush: export must wait for all appends.
        let lastAttempt = rig.log.lastAttempt
        let export = try await rig.log.prepareExport(in: rig.directory.appendingPathComponent("exports"))
        let bytes = try Data(contentsOf: export.fileURL)
        XCTAssertEqual(bytes, try Data(contentsOf: rig.log.fileURL))
        XCTAssertEqual(bytes.last, 0x0A)
        XCTAssertEqual(bytes.split(separator: 0x0A).count, 50)
        XCTAssertEqual(export.fileURL.pathExtension, "jsonl")
        XCTAssertTrue(export.fileURL.lastPathComponent.hasPrefix("Multi-Van-Playtest-"))
        XCTAssertNotEqual(export.fileURL, rig.log.fileURL)
        XCTAssertEqual(export.summaries.first?.attempts, 50)
        XCTAssertEqual(export.summaries.first?.id, run.level.id)
        XCTAssertEqual(rig.log.lastAttempt, lastAttempt)
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        let records = try bytes.split(separator: 0x0A).map {
            try decoder.decode(MultiVanPlaytestLog.Attempt.self, from: Data($0))
        }
        XCTAssertEqual(records.map(\.attemptNumber), Array(1...50))
        XCTAssertEqual(Set(records.map(\.sessionID)), [rig.log.sessionID])
        XCTAssertEqual(Set(records.map(\.levelSessionID)).count, 1)

        rig.log.begin(run, action: .retry)
        rig.log.leaveLevel(run, reason: "after_export")
        await rig.log.flush()
        XCTAssertEqual(try rig.attempts().map(\.attemptNumber), Array(1...51))
        XCTAssertEqual(try rig.attempts().last?.levelSessionID, records[0].levelSessionID)
        XCTAssertEqual(try Data(contentsOf: export.fileURL), bytes) // Stable while logging continues.
        XCTAssertTrue(try Data(contentsOf: rig.log.fileURL).starts(with: bytes))
        XCTAssertNil(rig.log.writeError)
        XCTAssertEqual(run.phase, .plan)
        XCTAssertEqual(run.runTime, 0)
    }

    func testConcurrentAndRepeatedExportsStayDistinctWithoutAddingRecords() async throws {
        let rig = try Rig(), run = try engine()
        rig.log.open(run)
        rig.log.leaveLevel(run, reason: "test")
        let directory = rig.directory.appendingPathComponent("exports")
        async let first = rig.log.prepareExport(in: directory)
        async let second = rig.log.prepareExport(in: directory)
        let (a, b) = try await (first, second)
        let c = try await rig.log.prepareExport(in: directory)
        XCTAssertEqual(Set([a.fileURL, b.fileURL, c.fileURL]).count, 3)
        let original = try Data(contentsOf: rig.log.fileURL)
        for export in [a, b, c] { XCTAssertEqual(try Data(contentsOf: export.fileURL), original) }
        XCTAssertEqual(try rig.attempts().count, 1)
        XCTAssertEqual(rig.log.lastAttempt?.attemptNumber, 1)
    }

    func testMissingAndEmptyLogsHaveEmptyStateWithoutWriteFailure() async throws {
        let rig = try Rig()
        await expectExportError(.empty, log: rig.log)
        XCTAssertFalse(FileManager.default.fileExists(atPath: rig.log.fileURL.path))
        try Data().write(to: rig.log.fileURL)
        await expectExportError(.empty, log: rig.log)
        XCTAssertNil(rig.log.writeError)
        XCTAssertEqual(try Data(contentsOf: rig.log.fileURL), Data())
    }

    func testUnreadableSourceProducesReadFailure() async throws {
        let rig = try Rig()
        try FileManager.default.createDirectory(at: rig.log.fileURL, withIntermediateDirectories: false)
        await expectExportError(.unreadable, log: rig.log)
        XCTAssertNil(rig.log.writeError)
        XCTAssertTrue(FileManager.default.fileExists(atPath: rig.log.fileURL.path))
    }

    func testWriteFailurePreventsSharingEvenIfOlderReadableDataIsRestored() async throws {
        let rig = try Rig(), run = try engine()
        rig.log.open(run)
        rig.log.leaveLevel(run, reason: "first")
        await rig.log.flush()
        let original = try Data(contentsOf: rig.log.fileURL)
        try FileManager.default.removeItem(at: rig.log.fileURL)
        try FileManager.default.createDirectory(at: rig.log.fileURL, withIntermediateDirectories: false)
        rig.log.begin(run, action: .retry)
        rig.log.leaveLevel(run, reason: "failed_write")
        await rig.log.flush()
        XCTAssertNotNil(rig.log.writeError)
        try FileManager.default.removeItem(at: rig.log.fileURL)
        try original.write(to: rig.log.fileURL)
        await expectExportError(.writeFailed, log: rig.log)
        XCTAssertEqual(try Data(contentsOf: rig.log.fileURL), original)
    }

    func testCopyFailurePreservesSourceAndPermitsRetry() async throws {
        let rig = try Rig(), run = try engine()
        rig.log.open(run)
        rig.log.leaveLevel(run, reason: "test")
        await rig.log.flush()
        let original = try Data(contentsOf: rig.log.fileURL)
        let blocked = rig.directory.appendingPathComponent("not-a-directory")
        try Data([1]).write(to: blocked)
        await expectExportError(.copyFailed, log: rig.log, directory: blocked)
        XCTAssertEqual(try Data(contentsOf: rig.log.fileURL), original)
        XCTAssertEqual(try Data(contentsOf: blocked), Data([1]))
        let retry = try await rig.log.prepareExport(in: rig.directory.appendingPathComponent("exports"))
        XCTAssertEqual(try Data(contentsOf: retry.fileURL), original)
        XCTAssertNil(rig.log.writeError)
    }

    func testExportLifetimeAndCancellationLeaveLoggerUsable() async throws {
        let rig = try Rig(), run = try engine()
        rig.log.open(run)
        rig.log.leaveLevel(run, reason: "test")
        let directory = rig.directory.appendingPathComponent("exports")
        var first: MultiVanPlaytestLog.Export? = try await rig.log.prepareExport(in: directory)
        let firstURL = try XCTUnwrap(first?.fileURL)
        var retainedBySheet = first
        first = nil
        await rig.log.flush()
        XCTAssertTrue(FileManager.default.fileExists(atPath: firstURL.path))
        XCTAssertNotNil(retainedBySheet)
        let second = try await rig.log.prepareExport(in: directory)
        retainedBySheet = nil // Dismissing/cancelling releases the sheet's ownership.
        await rig.log.flush()
        XCTAssertFalse(FileManager.default.fileExists(atPath: firstURL.path))
        XCTAssertTrue(FileManager.default.fileExists(atPath: second.fileURL.path))

        let cancelled = Task {
            withUnsafeCurrentTask { $0?.cancel() }
            return try await rig.log.prepareExport(in: directory)
        }
        do { _ = try await cancelled.value; XCTFail("Expected cancellation") }
        catch is CancellationError { /* Normal cancellation, no application error. */ }
        XCTAssertEqual(try FileManager.default.contentsOfDirectory(atPath: directory.path).count, 1)
        rig.log.begin(run, action: .retry)
        rig.log.leaveLevel(run, reason: "after_cancel")
        XCTAssertEqual(try rig.attempts().map(\.attemptNumber), [1, 2])
        XCTAssertNil(rig.log.writeError)
    }

    func testPerLevelSummaryExcludesQuitMarkersAndMatchesRecordedAttempts() async throws {
        let rig = try Rig(), run = try engine("level_007"), other = try engine("level_001")
        rig.log.open(run)
        for number in 1...2 {
            go(run, rig.log)
            run.advance(by: 30)
            process(run, rig.log)
            if number == 1 { run.retry(); rig.log.begin(run, action: .retry) }
        }
        rig.log.open(other)
        rig.log.leaveLevel(other, reason: "test")
        rig.log.quit(engine: nil, reason: "test")
        let summaries = try await rig.log.summary()
        XCTAssertEqual(summaries.map(\.id), ["level_001", "level_007"])
        XCTAssertEqual(summaries.map(\.attempts), [1, 2])
        XCTAssertEqual(summaries.map(\.mostCommonFailReason), ["None", "collision"])
        let attempts = try rig.attempts()
        for summary in summaries {
            let rows = attempts.filter { $0.levelID == summary.id }
            XCTAssertEqual(summary.averageChangesMinusPar,
                           Double(rows.map(\.changesMinusPar).reduce(0, +)) / Double(rows.count))
        }
        XCTAssertEqual(try rig.rows().count, 4)
    }

    func testBoardIsStampedOnAttemptsGoAndQuitAndChangesAreEvents() throws {
        let rig = try Rig(), run = try engine()
        // The prototype opens a level before its board appears.
        rig.log.open(run)
        rig.log.boardShown(.diorama, engine: run)
        rig.log.boardShown(.diorama, engine: run)
        XCTAssertEqual(tap(run, rig.log, "entry_switch"), .accepted)
        rig.log.boardShown(.flat, engine: run)
        go(run, rig.log)
        rig.log.stop(run)
        let first = try XCTUnwrap(rig.log.lastAttempt)
        XCTAssertEqual(first.boardStyle, "diorama")
        XCTAssertEqual(first.events.map(\.action), [.levelStarted, .switchTap, .boardChanged, .go, .stop])
        XCTAssertEqual(first.events.map(\.boardStyle), [nil, nil, "flat", "flat", nil])
        run.stop()
        rig.log.begin(run, action: .planningStarted)
        rig.log.quit(engine: run, reason: "test")
        XCTAssertEqual(rig.log.lastAttempt?.boardStyle, "flat")
        let quit = try XCTUnwrap(try rig.rows().last)
        XCTAssertEqual(quit["recordType"] as? String, "quit_at_level")
        XCTAssertEqual(quit["boardStyle"] as? String, "flat")
        XCTAssertEqual(quit["schemaVersion"] as? Int, 2)
    }

    func testBoardSummaryTimesFirstGoOnTheStartingBoardOnly() async throws {
        let rig = try Rig()
        func play(_ id: String, on style: MultiVanBoardStyle, planFor seconds: Double, switchingTo other: MultiVanBoardStyle? = nil) throws {
            let run = try engine(id)
            rig.log.boardShown(style, engine: run)
            rig.log.open(run)
            rig.clock.now += seconds
            if let other { rig.log.boardShown(other, engine: run) }
            go(run, rig.log)
            run.advance(by: 0.5)
            process(run, rig.log)
            // A second attempt never counts as a first Go.
            rig.log.stop(run)
            run.stop()
            rig.log.begin(run, action: .planningStarted)
            rig.clock.now += 1
            go(run, rig.log)
            rig.log.leaveLevel(run, reason: "test")
        }
        try play("level_001", on: .diorama, planFor: 12)
        try play("level_007", on: .diorama, planFor: 20)
        try play("level_009", on: .diorama, planFor: 4)
        try play("level_002", on: .diorama, planFor: 50, switchingTo: .flat)
        try play("level_003", on: .flat, planFor: 5)
        // A schema 1 row has no board and is left out.
        let unboarded = MultiVanPlaytestLog(fileURL: rig.log.fileURL)
        let old = try engine("level_004")
        unboarded.open(old)
        unboarded.leaveLevel(old, reason: "test")
        await unboarded.flush()
        let boards = try await rig.log.boardSummary()
        XCTAssertEqual(boards.map(\.id), ["diorama", "flat"])
        XCTAssertEqual(boards.map(\.attempts), [7, 3])
        XCTAssertEqual(boards[0].secondsToFirstGo, [12, 20, 4])
        XCTAssertEqual(boards[0].medianSecondsToFirstGo, 12)
        XCTAssertEqual(boards[1].secondsToFirstGo, [5])
        XCTAssertEqual(boards[1].medianSecondsToFirstGo, 5)
        XCTAssertEqual(MultiVanPlaytestLog.BoardSummary(id: "x", secondsToFirstGo: [4, 1, 3, 9]).medianSecondsToFirstGo, 3.5)
        XCTAssertNil(MultiVanPlaytestLog.BoardSummary(id: "x").medianSecondsToFirstGo)
        let levels = try await rig.log.summary()
        XCTAssertEqual(levels.map(\.attempts).reduce(0, +), 11)
    }

    func testShareUIIsInternalOnlyAccessibleAndOutsideGameplay() throws {
        let source = try String(contentsOf: root.appendingPathComponent("TinyRoutes/Prototype/MultiVanPrototypeScreen.swift"))
        let gameplay = try String(contentsOf: root.appendingPathComponent("TinyRoutes/Prototype/MultiVanGameplayScreen.swift"))
        XCTAssertTrue(source.hasPrefix("#if DEBUG || MULTIVAN_INTERNAL\n"))
        XCTAssertTrue(source.contains("Label(\"Playtest log\", systemImage: \"doc.text\")"))
        XCTAssertTrue(source.contains(".accessibilityLabel(\"Share Playtest Log\")"))
        XCTAssertTrue(source.contains(".disabled(isLoading || isPreparing || export != nil)"))
        XCTAssertTrue(source.contains("UIActivityViewController(activityItems: [export.fileURL], applicationActivities: nil)"))
        XCTAssertFalse(gameplay.contains("prepareExport"))
        XCTAssertFalse(gameplay.contains("UIActivityViewController"))
    }

    func testDistributionEntryRequiresInternalBuildAndSettingsOptIn() throws {
        let home = try String(contentsOf: root.appendingPathComponent("TinyRoutes/UI/HomeScreen.swift"))
        let settings = try String(contentsOf: root.appendingPathComponent("TinyRoutes/UI/SettingsScreen.swift"))
        let project = try String(contentsOf: root.appendingPathComponent("project.yml"))
        XCTAssertTrue(home.contains("#if DEBUG || MULTIVAN_INTERNAL"))
        XCTAssertTrue(home.contains("if canOpenPrototype {"))
        XCTAssertTrue(home.contains("#if DEBUG\n        true\n        #else\n        prototypeEnabled"))
        for source in [home, settings] {
            XCTAssertTrue(source.contains("#if MULTIVAN_INTERNAL\n    @AppStorage(\"multiVanPrototype.enabled\") private var prototypeEnabled = false"))
        }
        XCTAssertTrue(settings.contains("#if MULTIVAN_INTERNAL\n            TRSettingsToggleRow("))
        XCTAssertTrue(project.contains("InternalTestFlight: release"))
        XCTAssertTrue(project.contains("SWIFT_ACTIVE_COMPILATION_CONDITIONS: \"$(inherited) MULTIVAN_INTERNAL\""))
        let screen = try String(contentsOf: root.appendingPathComponent("TinyRoutes/Prototype/MultiVanPrototypeScreen.swift"))
        XCTAssertTrue(screen.contains("#if DEBUG\nprivate struct MultiVanTuningScreen"))
        XCTAssertTrue(screen.contains("#else\n        let nextEngine = try MultiVanEngine(level: level, tuning: .default)"))
    }
}
