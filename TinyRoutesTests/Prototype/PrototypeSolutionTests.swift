import XCTest
@testable import TinyRoutes

final class MultiVanStarsTests: XCTestCase {
    func testRatingThresholds() {
        let cases = [
            (par: 0, changes: 0, expected: 3),
            (par: 0, changes: 1, expected: 2),
            (par: 0, changes: 2, expected: 2),
            (par: 0, changes: 3, expected: 1),
            (par: 3, changes: 2, expected: 3),
            (par: 3, changes: 3, expected: 3),
            (par: 3, changes: 4, expected: 2),
            (par: 3, changes: 5, expected: 2),
            (par: 3, changes: 6, expected: 1)
        ]
        for testCase in cases {
            XCTAssertEqual(MultiVanStars.rating(changes: testCase.changes, par: testCase.par), testCase.expected,
                           "par \(testCase.par), changes \(testCase.changes)")
        }
    }
}

final class PrototypeSolutionTests: XCTestCase {
    private let levelBundle = Bundle(for: MultiVanEngine.self)

    private func levels() throws -> [MultiVanLevel] {
        // Reuse production discovery; MV-17 owns graph/schema validation.
        let levels = try MultiVanLevelRepository(bundle: levelBundle).loadAllLevels()
        XCTAssertFalse(levels.isEmpty, "Prototype repository discovered no levels")
        return levels
    }

    private func level(_ id: String) throws -> MultiVanLevel {
        try XCTUnwrap(levels().first { $0.id == id }, "\(id): missing authored prototype level")
    }

    private func assertDiagnostic(_ expected: [String], _ action: () throws -> Void,
                                  file: StaticString = #filePath, line: UInt = #line) {
        XCTAssertThrowsError(try action(), file: file, line: line) { error in
            for fragment in expected {
                XCTAssertTrue(error.localizedDescription.contains(fragment),
                              "Expected '\(fragment)' in diagnostic: \(error.localizedDescription)", file: file, line: line)
            }
        }
    }

    private func fixture(_ id: String, mutate: (inout [String: Any]) -> Void) throws -> MultiVanLevel {
        let url = try XCTUnwrap(levelBundle.url(forResource: id, withExtension: "json", subdirectory: "PrototypeLevels"))
        var json = try XCTUnwrap(JSONSerialization.jsonObject(with: Data(contentsOf: url)) as? [String: Any])
        mutate(&json)
        return try JSONDecoder().decode(MultiVanLevel.self, from: JSONSerialization.data(withJSONObject: json))
    }

    func testEveryDiscoveredLevelHasAWinningSolutionAtPar() throws {
        for level in try levels() {
            do {
                let script = try PrototypeSolutionScript.load(levelID: level.id)
                let engine = try PrototypeSolutionRunner.verify(level: level, script: script)
                XCTAssertEqual(engine.outcome, .win, "\(level.id): recorded solution must win")
                XCTAssertEqual(engine.changeCount, level.parChanges, "\(level.id): recorded solution must match par")
                for van in engine.vans {
                    let house = try XCTUnwrap(level.houses.first { $0.color == van.color }, "\(level.id): \(van.id) has no matching house")
                    let node = try XCTUnwrap(engine.runtimeGraph.nodesByID[house.nodeID])
                    XCTAssertEqual(van.status, .parked, "\(level.id): \(van.id) did not park")
                    XCTAssertEqual(van.position, RoadPoint(x: node.x, y: node.y), "\(level.id): \(van.id) did not reach \(house.nodeID)")
                }
            } catch {
                XCTFail("\(level.id): \(error.localizedDescription)")
            }
        }
    }

    func testLevelsRequiringChangesDoNotAlreadyWin() throws {
        for level in try levels() where level.parChanges > 0 {
            do {
                let engine = try PrototypeSolutionRunner.run(level: level, script: .init())
                XCTAssertNotEqual(engine.outcome, .win, "\(level.id): initial configuration already wins despite par \(level.parChanges)")
            } catch let error as PrototypeSolutionError {
                // A loop that reaches the simulation limit also does not win.
                XCTAssertTrue(error.message.contains("\(level.id): timed out after 120 seconds;"), error.message)
            }
        }
    }

    func testLevelOneZeroTapTutorialWinsAtZeroPar() throws {
        let level = try level("level_001")
        let script = try PrototypeSolutionScript.load(levelID: level.id)
        XCTAssertTrue(script.planTaps.isEmpty, "level_001: tutorial needs no input")
        let engine = try PrototypeSolutionRunner.verify(level: level, script: script)
        XCTAssertEqual(engine.outcome, .win)
        XCTAssertEqual(engine.changeCount, 0)
        XCTAssertEqual(level.parChanges, 0)
    }

    func testLevelTwoRequiresItsOneAuthoredTap() throws {
        let level = try level("level_002")
        let script = try PrototypeSolutionScript.load(levelID: level.id)
        XCTAssertEqual(script.planTaps, ["switch"])
        let engine = try PrototypeSolutionRunner.verify(level: level, script: script)
        XCTAssertEqual(engine.changeCount, 1)
        XCTAssertEqual(level.parChanges, 1)
        let initial = try PrototypeSolutionRunner.run(level: level, script: .init())
        XCTAssertEqual(initial.outcome, .failStuck(vanID: "red", nodeID: "barrier"))
        XCTAssertEqual(initial.changeCount, 0)
    }

    func testLevelThreeRequiresBothSwitchesAndWrongExitLoopsHarmlessly() throws {
        let level = try level("level_003")
        let script = try PrototypeSolutionScript.load(levelID: level.id)
        XCTAssertEqual(script.planTaps, ["loop_switch", "house_switch"])
        XCTAssertTrue(script.liveTaps.isEmpty)
        XCTAssertEqual(level.parChanges, 2)

        // Exhaust every distinct configuration of the two two-way switches.
        for taps in [[], ["house_switch"], ["loop_switch"], ["loop_switch", "house_switch"]] {
            let engine = try MultiVanEngine(level: level)
            for nodeID in taps { XCTAssertEqual(engine.tapSwitch(nodeID: nodeID), .accepted) }
            let preview = try XCTUnwrap(engine.previewRoutes.first)
            if !taps.contains("loop_switch") {
                XCTAssertEqual(preview.ending, .loopLimit)
                XCTAssertEqual(preview.edgeIDs.count, engine.tuning.previewEdgeLimit)
                XCTAssertEqual(Array(preview.edgeIDs.prefix(5)),
                               ["to_loop_switch", "to_loop_corner", "loop_return", "to_loop_corner", "loop_return"])
                engine.go()
                for _ in 0..<Int(120 / engine.tuning.stepDuration) {
                    engine.advance(by: engine.tuning.stepDuration)
                }
                XCTAssertNil(engine.outcome, "level_003: loop must remain harmless for 120 seconds")
                XCTAssertEqual(engine.phase, .run)
                XCTAssertEqual(engine.vans.first?.status, .driving)
            } else {
                let solved = taps.contains("house_switch")
                XCTAssertEqual(preview.ending, solved ? .matchingHouse : .deadEnd)
                let result = try PrototypeSolutionRunner.run(level: level, script: .init(planTaps: taps))
                XCTAssertEqual(result.outcome, solved ? .win : .failStuck(vanID: "red", nodeID: "barrier"))
                XCTAssertEqual(result.changeCount, solved ? 2 : 1)
            }
        }
    }

    func testLevelFourCyclesThreeExitsAndRequiresTwoForwardChanges() throws {
        let level = try level("level_004")
        let script = try PrototypeSolutionScript.load(levelID: level.id)
        XCTAssertEqual(script.planTaps, ["switch", "switch"])
        XCTAssertTrue(script.liveTaps.isEmpty)
        XCTAssertEqual(level.parChanges, 2)
        let engine = try MultiVanEngine(level: level)
        XCTAssertEqual(engine.runtimeGraph.nodesByID["switch"]?.outgoingEdgeIDs,
                       ["to_right_barrier", "to_top_barrier", "to_house"])
        for tapCount in 0...3 {
            let expectedEdge = ["to_right_barrier", "to_top_barrier", "to_house", "to_right_barrier"][tapCount]
            XCTAssertEqual(engine.runtimeGraph.nodesByID["switch"]?.activeOutgoingEdgeID, expectedEdge)
            XCTAssertEqual(engine.changeCount, tapCount % 3)
            XCTAssertEqual(engine.previewRoutes.first?.ending, tapCount == 2 ? .matchingHouse : .deadEnd)
            let result = try PrototypeSolutionRunner.run(level: level,
                                                        script: .init(planTaps: Array(repeating: "switch", count: tapCount)))
            let expected: MultiVanEngine.Outcome = tapCount == 2 ? .win : .failStuck(
                vanID: "red", nodeID: tapCount == 1 ? "top_barrier" : "right_barrier")
            XCTAssertEqual(result.outcome, expected)
            XCTAssertEqual(result.changeCount, tapCount % 3)
            XCTAssertEqual(engine.tapSwitch(nodeID: "switch"), .accepted)
        }
        // A full extra cycle must not inflate MV-07's configuration-based count.
        let wrapped = try PrototypeSolutionRunner.verify(level: level,
                                                         script: .init(planTaps: Array(repeating: "switch", count: 5)))
        XCTAssertEqual(wrapped.changeCount, 2)
    }

    func testLevelFiveRequiresBothColourRoutesAtPar() throws {
        let level = try level("level_005")
        let script = try PrototypeSolutionScript.load(levelID: level.id)
        XCTAssertEqual(script.planTaps, ["red_switch", "blue_switch"])
        XCTAssertTrue(script.liveTaps.isEmpty)
        XCTAssertEqual(level.parChanges, 2)
        XCTAssertEqual(level.vans.map(\.color), [.red, .blue])
        XCTAssertTrue(level.liveSwitchNodeIDs.isEmpty)

        // All four configurations: neither single correction can win below par.
        for taps in [[], ["red_switch"], ["blue_switch"], script.planTaps] {
            let engine = try MultiVanEngine(level: level)
            for nodeID in taps { XCTAssertEqual(engine.tapSwitch(nodeID: nodeID), .accepted) }
            for (index, van) in level.vans.enumerated() {
                let corrected = taps.contains("\(van.id)_switch")
                let route = engine.previewRoutes[index]
                XCTAssertEqual(route.ending, corrected ? .matchingHouse : .wrongHouse)
                let lastEdge = try XCTUnwrap(route.edgeIDs.last.flatMap { engine.runtimeGraph.edgesByID[$0] })
                XCTAssertEqual(lastEdge.toNodeID, "\(corrected ? van.id : (van.id == "red" ? "blue" : "red"))_house")
            }
            let result = try PrototypeSolutionRunner.run(level: level, script: .init(planTaps: taps))
            XCTAssertEqual(result.changeCount, taps.count)
            switch taps.count {
            case 2:
                XCTAssertEqual(result.outcome, .win)
                XCTAssertEqual(result.vans.map(\.status), [.parked, .parked])
                XCTAssertNil(result.lastFailPoint)
            default:
                guard case .failWrongHouse = result.outcome else {
                    return XCTFail("level_005: uncorrected route must fail at the wrong house: \(String(describing: result.outcome))")
                }
            }
        }
        // An extra full cycle preserves MV-07's configuration-based par.
        let wrapped = try PrototypeSolutionRunner.verify(level: level, script: .init(
            planTaps: ["red_switch", "red_switch", "red_switch", "blue_switch"]))
        XCTAssertEqual(wrapped.changeCount, 2)
    }

    func testLevelSixConvoyDepartureSpacingLiveSplitAndBothDeliveries() throws {
        let level = try level("level_006")
        let script = try PrototypeSolutionScript.load(levelID: level.id)
        XCTAssertTrue(script.planTaps.isEmpty)
        XCTAssertEqual(script.liveTaps.count, 1)
        XCTAssertEqual(script.liveTaps.first?.nodeID, "switch")
        XCTAssertEqual(script.liveTaps.first?.atTime, 2.75)
        XCTAssertEqual(level.parChanges, 1)
        XCTAssertEqual(level.liveSwitchNodeIDs, ["switch"])
        XCTAssertEqual(level.vans.map(\.color), [.red, .blue])
        XCTAssertEqual(level.vans.map(\.startNodeID), ["start", "blue_start"])
        XCTAssertEqual(level.vans.map(\.departDelay), [0, 0.83])

        let engine = try MultiVanEngine(level: level)
        XCTAssertNotEqual(engine.vans[0].position, engine.vans[1].position, "Blue waits on its own spot behind Red")
        XCTAssertEqual(engine.previewRoutes.map(\.edgeIDs),
                       [["approach", "red_exit"], ["blue_lead", "approach", "red_exit"]])
        XCTAssertEqual(engine.previewRoutes.map(\.ending), [.matchingHouse, .wrongHouse])
        engine.go()
        let start = engine.vans[1].position
        XCTAssertEqual(engine.vans.map(\.status), [.driving, .waiting])
        XCTAssertEqual(engine.vans[0].currentEdgeID, "approach")
        let step = engine.tuning.stepDuration
        engine.advance(by: step)
        XCTAssertNotEqual(engine.vans[0].position, start)
        XCTAssertEqual(engine.vans[1].position, start)
        XCTAssertNil(engine.outcome, "The waiting van must not collide with Red")
        engine.advance(by: 98 * step)
        XCTAssertEqual(engine.runTime, 99 * step)
        XCTAssertEqual(engine.vans[1].status, .waiting)
        XCTAssertEqual(engine.vans[1].position, start)
        engine.advance(by: step)
        // Departure is tested at the start of each fixed step: tick 100 is the
        // first past 0.83, and the next step performs Blue's first move.
        XCTAssertEqual(engine.runTime, 100 * step)
        XCTAssertEqual(engine.vans[1].status, .waiting)
        XCTAssertEqual(engine.vans[1].position, start)
        XCTAssertEqual(engine.vans[0].distanceAlongEdge, 1.25, accuracy: 1e-9)
        engine.advance(by: step)
        XCTAssertEqual(engine.runTime, 101 * step)
        XCTAssertEqual(engine.vans.map(\.status), [.driving, .driving])
        XCTAssertEqual(engine.vans.map(\.currentEdgeID), ["approach", "blue_lead"])
        XCTAssertEqual(engine.vans[1].distanceAlongEdge, engine.tuning.vanSpeed * step, accuracy: 1e-9)
        XCTAssertEqual(engine.vans[0].position.y - engine.vans[1].position.y, 2.25, accuracy: 1e-9)

        var minimumSeparation = Double.infinity
        var sawRedParkedWhileBlueDriving = false
        for _ in 101..<Int(120 / step) {
            if engine.outcome != nil { break }
            if engine.runTime == script.liveTaps[0].atTime {
                XCTAssertEqual(engine.vans.map(\.currentEdgeID), ["red_exit", "approach"])
                XCTAssertFalse(engine.lockedSwitchNodeIDs.contains("switch"))
                XCTAssertEqual(engine.tapSwitch(nodeID: "switch"), .accepted)
            }
            engine.advance(by: step)
            if engine.vans.allSatisfy({ $0.status == .driving }) {
                let red = engine.vans[0].position
                let blue = engine.vans[1].position
                minimumSeparation = min(minimumSeparation, hypot(red.x - blue.x, red.y - blue.y))
            }
            if engine.vans[0].status == .parked, engine.vans[1].status == .driving {
                sawRedParkedWhileBlueDriving = true
                XCTAssertNil(engine.outcome, "Red's delivery alone must not win")
            }
        }
        XCTAssertTrue(minimumSeparation.isFinite)
        XCTAssertTrue(minimumSeparation > 1.5, "Measured convoy clearance: \(minimumSeparation)")
        XCTAssertTrue(minimumSeparation > engine.tuning.crashDistance)
        XCTAssertTrue(sawRedParkedWhileBlueDriving)
        XCTAssertEqual(engine.outcome, .win)
        XCTAssertEqual(engine.vans.map(\.status), [.parked, .parked])
        XCTAssertEqual(engine.vans.map(\.position), [RoadPoint(x: 0, y: 4), RoadPoint(x: 4, y: 4)])
        XCTAssertEqual(engine.changeCount, level.parChanges)
        XCTAssertNil(engine.lastFailPoint)
        let recorded = try PrototypeSolutionRunner.verify(level: level, script: script)
        XCTAssertEqual(recorded.runTime, engine.runTime)
        XCTAssertEqual(recorded.vans.map(\.position), engine.vans.map(\.position))
    }

    func testLevelSixCannotWinWithEitherFrozenConfiguration() throws {
        let level = try level("level_006")
        let untouched = try PrototypeSolutionRunner.run(level: level, script: .init())
        XCTAssertEqual(untouched.outcome, .failWrongHouse(vanID: "blue", houseNodeID: "red_house"))
        XCTAssertEqual(untouched.changeCount, 0)
        let flipped = try PrototypeSolutionRunner.run(level: level, script: .init(planTaps: ["switch"]))
        XCTAssertEqual(flipped.outcome, .failWrongHouse(vanID: "red", houseNodeID: "blue_house"))
        XCTAssertEqual(flipped.changeCount, 1)
    }

    func testInvalidSwitchAndNonSwitchAreRejectedInScriptOrder() throws {
        let level = try level("level_002")
        for nodeID in ["missing", "red_start"] {
            assertDiagnostic([level.id, "planTaps[1]", "node \(nodeID)", "notASwitch"]) {
                _ = try PrototypeSolutionRunner.run(level: level, script: .init(planTaps: ["switch", nodeID]))
            }
        }
    }

    func testWrongSolutionReportsLevelOutcomeAndVan() throws {
        let level = try level("level_002")
        assertDiagnostic([level.id, "expected .win", "failStuck", "red", "barrier", "changeCount=0"]) {
            try PrototypeSolutionRunner.verify(level: level, script: .init())
        }
    }

    func testParMismatchReportsEngineCount() throws {
        let level = try fixture("level_002") { $0["parChanges"] = 2 }
        assertDiagnostic([level.id, "expected changeCount == parChanges (2)", "changeCount=1"]) {
            try PrototypeSolutionRunner.verify(level: level, script: .init(planTaps: ["switch"]))
        }
    }

    func testRepeatedTapsUseConfigurationCountRatherThanTapHistory() throws {
        let engine = try PrototypeSolutionRunner.verify(level: level("level_002"),
                                                       script: .init(planTaps: ["switch", "switch", "switch"]))
        XCTAssertEqual(engine.changeCount, 1, "level_002: three taps on a two-way switch count as one change")
    }

    func testMissingSolutionReportsExpectedPath() {
        assertDiagnostic(["level_missing", "missing solution file", "PrototypeSolutions/level_missing.solution.json"]) {
            _ = try PrototypeSolutionScript.load(levelID: "level_missing")
        }
    }

    func testTimeoutReportsLevelTimeAndWaitingVan() throws {
        let level = try fixture("level_001") {
            $0["vans"] = [["id": "red", "color": "red", "startNodeID": "red_start", "departDelay": 121]]
        }
        assertDiagnostic([level.id, "timed out after 120 seconds", "runTime=120.0", "red=waiting", "outcome=nil"]) {
            _ = try PrototypeSolutionRunner.run(level: level, script: .init())
        }
    }

    func testLiveTapFieldsDecodeAndInvalidSwitchReportsTimedDiagnostic() throws {
        let script = try JSONDecoder().decode(PrototypeSolutionScript.self, from: Data(
            #"{"planTaps":["switch"],"liveTaps":[{"atTime":3.25,"nodeID":"s3"}]}"#.utf8))
        XCTAssertEqual(script.liveTaps.first?.atTime, 3.25)
        XCTAssertEqual(script.liveTaps.first?.nodeID, "s3")
        let level = try level("level_002")
        assertDiagnostic([level.id, "liveTaps[0]", "s3", "3.25", "notASwitch"]) {
            _ = try PrototypeSolutionRunner.run(level: level, script: script)
        }
    }

    func testTimedLiveTapSplitWinsAtParAndReplaysDeterministically() throws {
        let level = try MultiVanLiveSwitchTests.fixture()
        // Off-grid timestamp rounds up to the first simulation boundary at or after it.
        let script = PrototypeSolutionScript(liveTaps: [.init(atTime: 1.001, nodeID: "switch")])
        let first = try PrototypeSolutionRunner.verify(level: level, script: script)
        let second = try PrototypeSolutionRunner.verify(level: level, script: script)
        XCTAssertEqual(first.outcome, .win)
        XCTAssertEqual(first.changeCount, 1)
        XCTAssertEqual(first.vans.map(\.currentEdgeID), ["red_exit", "blue_exit"])
        XCTAssertEqual(first.runTime, second.runTime)
        XCTAssertEqual(first.vans.map(\.position), second.vans.map(\.position))
    }

    func testLockedTimedTapIdentifiesLevelSwitchTimestampAndReason() throws {
        let level = try MultiVanLiveSwitchTests.fixture()
        assertDiagnostic([level.id, "liveTaps[0]", "node switch", "atTime 0.5", "runTime 0.5", "rejectedLocked"]) {
            _ = try PrototypeSolutionRunner.run(level: level, script: .init(liveTaps: [.init(atTime: 0.5, nodeID: "switch")]))
        }
    }

    func testSameTimestampTapsKeepScriptOrder() throws {
        let level = try MultiVanLiveSwitchTests.fixture()
        // Two invalid switches make the first rejection observably order-dependent.
        for ids in [["missing", "normal"], ["normal", "missing"]] {
            assertDiagnostic([level.id, "liveTaps[0]", "node \(ids[0])", "atTime 1.0",
                              ids[0] == "normal" ? "rejectedFrozen" : "notASwitch"]) {
                _ = try PrototypeSolutionRunner.run(level: level, script: .init(liveTaps: ids.map {
                    .init(atTime: 1, nodeID: $0)
                }))
            }
        }
        // All accepted taps at that boundary must run before movement resumes.
        let script = PrototypeSolutionScript(liveTaps: Array(repeating: .init(atTime: 1, nodeID: "switch"), count: 3))
        let result = try PrototypeSolutionRunner.verify(level: level, script: script)
        XCTAssertEqual(result.changeCount, 1)
    }

    func testTimedRunnerAppliesPlanBeforeGoAndSortsByTime() throws {
        let level = try MultiVanLiveSwitchTests.fixture()
        let script = PrototypeSolutionScript(planTaps: ["switch"], liveTaps: [
            .init(atTime: 1, nodeID: "switch"), .init(atTime: 0, nodeID: "switch")
        ])
        let result = try PrototypeSolutionRunner.verify(level: level, script: script)
        XCTAssertEqual(result.vans.map(\.currentEdgeID), ["red_exit", "blue_exit"])
        XCTAssertEqual(result.changeCount, 1)
    }

    func testTimedRunnerRejectsInvalidAndUnreachedTimestamps() throws {
        let level = try MultiVanLiveSwitchTests.fixture()
        for time in [-1.0, Double.nan, Double.infinity] {
            assertDiagnostic([level.id, "liveTaps[0]", "switch", "invalid timestamp"]) {
                _ = try PrototypeSolutionRunner.run(level: level, script: .init(liveTaps: [.init(atTime: time, nodeID: "switch")]))
            }
        }
        assertDiagnostic([level.id, "liveTaps[0]", "switch", "atTime 100.0", "not applied before outcome"]) {
            _ = try PrototypeSolutionRunner.run(level: level, script: .init(liveTaps: [.init(atTime: 100, nodeID: "switch")]))
        }
    }

    func testOmittedLiveTapsDecodeAsEmpty() throws {
        let script = try JSONDecoder().decode(PrototypeSolutionScript.self, from: Data(#"{"planTaps":[]}"#.utf8))
        XCTAssertTrue(script.liveTaps.isEmpty)
        XCTAssertTrue(script.planTaps.isEmpty)
    }

    func testFreshEnginesPreventRunAndSwitchStateLeaking() throws {
        let level = try level("level_002")
        let script = try PrototypeSolutionScript.load(levelID: level.id)
        let first = try PrototypeSolutionRunner.verify(level: level, script: script)
        first.retry()
        first.resetSwitches()
        first.go()
        first.advance(by: first.tuning.stepDuration)
        let second = try PrototypeSolutionRunner.run(level: level, script: .init())
        XCTAssertFalse(first === second)
        XCTAssertEqual(second.outcome, .failStuck(vanID: "red", nodeID: "barrier"))
        XCTAssertEqual(second.changeCount, 0)
        let third = try PrototypeSolutionRunner.verify(level: level, script: script)
        XCTAssertFalse(second === third)
        XCTAssertEqual(third.changeCount, 1)
    }

    func testReplayingEveryScriptIsDeterministic() throws {
        for level in try levels() {
            let script = try PrototypeSolutionScript.load(levelID: level.id)
            let first = try PrototypeSolutionRunner.verify(level: level, script: script)
            let second = try PrototypeSolutionRunner.verify(level: level, script: script)
            XCTAssertFalse(first === second, "\(level.id): engine reused")
            XCTAssertEqual(first.outcome, second.outcome, level.id)
            XCTAssertEqual(first.changeCount, second.changeCount, level.id)
            XCTAssertEqual(first.runTime, second.runTime, level.id)
            XCTAssertEqual(first.vans.map(\.status), second.vans.map(\.status), level.id)
            XCTAssertEqual(first.vans.map(\.position), second.vans.map(\.position), level.id)
            XCTAssertEqual(first.vans.map(\.currentEdgeID), second.vans.map(\.currentEdgeID), level.id)
        }
    }

    func testOutcomeAtGoStopsWithoutAdvancing() throws {
        let level = try fixture("level_001") {
            $0["vans"] = [["id": "red", "color": "red", "startNodeID": "red_house"]]
        }
        let engine = try PrototypeSolutionRunner.verify(level: level, script: .init())
        XCTAssertEqual(engine.runTime, 0, "level_001: runner must stop immediately when go() produces an outcome")
    }
}

// MV-29: sample the actual fixed-step engine, including rounded-road positions.
// Keep timing diagnostics in tests; previews intentionally say nothing about crashes.
extension PrototypeSolutionTests {
    #if DEBUG
    /// MV-46 engineering evidence only; these checks make no claim about human usability.
    func testMV46DefaultAndSingleParameterTrialsPreserveSolutionsAndReplay() throws {
        let suite = "MultiVanMV46.\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suite))
        defer { defaults.removePersistentDomain(forName: suite) }
        let store = MultiVanPrototypeTuning(defaults: defaults)
        let defaultTicks = [794, 560, 640, 400, 480, 580, 954, 1434, 634, 480, 954, 1108]
        let trials: [(MultiVanPrototypeTuning.Parameter, Double, [Int])] = [
            (.vanSpeed, 1.5, defaultTicks),
            (.vanSpeed, 1.3, [916, 647, 739, 462, 554, 654, 1101, 1655, 732, 554, 1101, 1279]),
            (.liveSwitchLockRadius, 0.3, defaultTicks)
        ]
        for (parameter, value, completionTicks) in trials {
            store.reset() // No trial inherits another trial's overrides.
            store.set(value, for: parameter)
            let tuning = store.tuning // Same validated snapshot injected by MV-45.
            XCTAssertEqual(tuning.vanSpeed, parameter == .vanSpeed ? value : 1.5)
            XCTAssertEqual(tuning.crashDistance, 0.35)
            XCTAssertEqual(tuning.liveSwitchLockRadius, parameter == .liveSwitchLockRadius ? value : 0.4)
            XCTAssertEqual(tuning.stepDuration, 1.0 / 120)
            for (index, level) in try levels().enumerated() {
                let script = try PrototypeSolutionScript.load(levelID: level.id)
                let reference = try replay(level, script: script, frames: [1.0 / 120], duration: 20, tuning: tuning)
                XCTAssertEqual(reference.engine.outcome, .win, level.id)
                XCTAssertEqual(reference.engine.changeCount, level.parChanges, level.id)
                XCTAssertEqual(reference.engine.runTime, Double(completionTicks[index]) * tuning.stepDuration, level.id)
                for frames in [[1.0 / 60], [0.004, 0.030]] {
                    for speeds in [[false], [true], [false, true, true, false]] {
                        let run = try replay(level, script: script, frames: frames, duration: 20,
                                             playbackSpeeds: speeds, tuning: tuning)
                        assertSameState(run.engine, reference.engine)
                        XCTAssertEqual(run.events, reference.events)
                        XCTAssertEqual(run.taps, reference.taps)
                    }
                }
                let untouched = try replay(level, frames: [1.0 / 60], duration: 20, tuning: tuning)
                let repeated = try replay(level, frames: [0.004, 0.030], duration: 20,
                                          playbackSpeeds: [true], tuning: tuning)
                assertSameState(repeated.engine, untouched.engine)
                XCTAssertEqual(repeated.events, untouched.events)
            }
        }
    }

    func testMV46EveryStepOfMeasuredLiveWindowsWinsAndAdjacentStepsReject() throws {
        // Tick bounds are [first accepted, first relocked), at 120 Hz.
        // Level 8 measures its FIRST safe release opportunity, not a global deadline.
        let trials: [(MultiVanTuning, [(Int, Int, Int)])] = [
            (.default, [(6, 272, 388), (8, 432, 1009), (9, 192, 362), (11, 506, 609), (12, 506, 762)]),
            (MultiVanTuning(vanSpeed: 1.3), [(6, 314, 433), (8, 499, 1164), (9, 222, 418), (11, 584, 702), (12, 584, 880)]),
            (MultiVanTuning(liveSwitchLockRadius: 0.3), [(6, 264, 396), (8, 424, 1017), (9, 184, 370), (11, 498, 617), (12, 498, 770)])
        ]
        for (tuning, windows) in trials {
            for (number, first, end) in windows {
                let level = try level(String(format: "level_%03d", number))
                let script = try PrototypeSolutionScript.load(levelID: level.id)
                let node = try XCTUnwrap(script.liveTaps.first?.nodeID)
                // Every tick is an independent full replay, so sweep them in parallel
                // without recording timing samples; this sweep only needs outcomes.
                let ticks = Array(first..<end)
                let failures = NSLock()
                var failed: [String] = []
                DispatchQueue.concurrentPerform(iterations: ticks.count) { index in
                    let tick = ticks[index]
                    let failure: String?
                    do {
                        let (engine, accepted) = try playToOutcome(level, planTaps: script.planTaps, liveTapNodeID: node,
                                                                   liveTapTime: Double(tick) * tuning.stepDuration, tuning: tuning)
                        failure = accepted && engine.outcome == .win && engine.changeCount == level.parChanges ? nil
                            : "tick \(tick): tap accepted \(accepted), \(String(describing: engine.outcome)), changes \(engine.changeCount)"
                    } catch {
                        failure = "tick \(tick): \(error.localizedDescription)"
                    }
                    if let failure { failures.withLock { failed.append(failure) } }
                }
                XCTAssertEqual(failed.sorted(), [], "\(level.id) must win at par on every tick in [\(first), \(end))")
                for tick in [first - 1, end] {
                    let engine = try MultiVanEngine(level: level, tuning: tuning)
                    for node in script.planTaps { XCTAssertEqual(engine.tapSwitch(nodeID: node), .accepted) }
                    engine.go()
                    engine.advance(by: Double(tick) * tuning.stepDuration)
                    let count = engine.changeCount
                    let edge = engine.runtimeGraph.nodesByID[node]?.activeOutgoingEdgeID
                    XCTAssertEqual(engine.tapSwitch(nodeID: node), .rejectedLocked)
                    XCTAssertEqual(engine.changeCount, count)
                    XCTAssertEqual(engine.runtimeGraph.nodesByID[node]?.activeOutgoingEdgeID, edge)
                }
                print("MV46 speed=\(tuning.vanSpeed), crash=\(tuning.crashDistance), radius=\(tuning.liveSwitchLockRadius): \(level.id) winning ticks [\(first), \(end)), duration=\(Double(end - first) * tuning.stepDuration)s")
            }
        }
    }
    #endif

    private struct TimingSample {
        let time: TimeInterval
        let vans: [MultiVanVanState]
        let locked: Set<String>
    }

    private func trace(_ level: MultiVanLevel, script: PrototypeSolutionScript, tuning: MultiVanTuning = .default) throws
        -> (engine: MultiVanEngine, samples: [TimingSample]) {
        let engine = try MultiVanEngine(level: level, tuning: tuning)
        for nodeID in script.planTaps { XCTAssertEqual(engine.tapSwitch(nodeID: nodeID), .accepted) }
        engine.go()
        var samples: [TimingSample] = []
        var nextTap = 0
        for _ in 0..<Int(120 / engine.tuning.stepDuration) {
            samples.append(TimingSample(time: engine.runTime, vans: engine.vans, locked: engine.lockedSwitchNodeIDs))
            if engine.outcome != nil { break }
            while nextTap < script.liveTaps.count, script.liveTaps[nextTap].atTime <= engine.runTime {
                XCTAssertEqual(engine.tapSwitch(nodeID: script.liveTaps[nextTap].nodeID), .accepted)
                nextTap += 1
            }
            engine.advance(by: engine.tuning.stepDuration)
        }
        XCTAssertEqual(nextTap, script.liveTaps.count)
        return (engine, samples)
    }

    /// Mirrors `trace` (plan, Go, fixed steps, live tap once due) without
    /// keeping per-step samples. `liveTapAccepted` is false if the tap was
    /// rejected or never became due.
    private func playToOutcome(_ level: MultiVanLevel, planTaps: [String], liveTapNodeID: String,
                               liveTapTime: TimeInterval, tuning: MultiVanTuning) throws
        -> (engine: MultiVanEngine, liveTapAccepted: Bool) {
        let engine = try MultiVanEngine(level: level, tuning: tuning)
        for nodeID in planTaps where engine.tapSwitch(nodeID: nodeID) != .accepted { return (engine, false) }
        engine.go()
        var tapped = false
        for _ in 0..<Int(120 / engine.tuning.stepDuration) {
            if engine.outcome != nil { break }
            if !tapped, liveTapTime <= engine.runTime {
                guard engine.tapSwitch(nodeID: liveTapNodeID) == .accepted else { return (engine, false) }
                tapped = true
            }
            engine.advance(by: engine.tuning.stepDuration)
        }
        return (engine, tapped)
    }

    private func minimumSeparation(_ samples: [TimingSample]) -> Double {
        samples.filter { $0.vans.allSatisfy { $0.status == .driving } }.map {
            let a = $0.vans[0].position, b = $0.vans[1].position
            return hypot(a.x - b.x, a.y - b.y)
        }.min() ?? .infinity
    }

    func testLevelSevenCorrectPreviewsStillCrashAndDetourSeparatesTheMerge() throws {
        let level = try level("level_007")
        let initial = try MultiVanEngine(level: level)
        XCTAssertEqual(initial.previewRoutes.map(\.ending), [.matchingHouse, .matchingHouse])
        let crash = try PrototypeSolutionRunner.run(level: level, script: .init())
        guard case let .failCrash(vanIDs, point) = crash.outcome else { return XCTFail("Merge must crash untouched") }
        XCTAssertEqual(vanIDs, ["red", "blue"])
        XCTAssertEqual(crash.vans.map(\.status), [.crashed, .crashed])
        XCTAssertEqual(crash.lastFailPoint, point)
        let a = crash.vans[0].position, b = crash.vans[1].position
        XCTAssertEqual(point, RoadPoint(x: (a.x + b.x) / 2, y: (a.y + b.y) / 2))
        XCTAssertTrue((1.8...2.3).contains(point.x) && (3.7...4.1).contains(point.y), "Crash must read at the merge")
        XCTAssertTrue(hypot(a.x - b.x, a.y - b.y) < crash.tuning.crashDistance)
        for _ in 0..<3 {
            let repeated = try PrototypeSolutionRunner.run(level: level, script: .init())
            XCTAssertEqual(repeated.outcome, crash.outcome)
            XCTAssertEqual(repeated.runTime, crash.runTime)
            XCTAssertEqual(repeated.vans.map(\.position), crash.vans.map(\.position))
        }

        let script = try PrototypeSolutionScript.load(levelID: level.id)
        XCTAssertEqual(script.planTaps, ["route_switch"])
        XCTAssertTrue(script.liveTaps.isEmpty)
        XCTAssertEqual(level.parChanges, 1)
        let run = try trace(level, script: script)
        XCTAssertEqual(run.engine.outcome, .win)
        XCTAssertEqual(run.engine.changeCount, level.parChanges)
        XCTAssertNil(run.engine.lastFailPoint)
        XCTAssertTrue(minimumSeparation(run.samples) > run.engine.tuning.crashDistance)
        let lengths = initial.runtimeGraph.edgesByID.mapValues { $0.roadPath.totalLength }
        // Red's separately traced exit and Blue's exit physically share the
        // x=2 stem above y=4, then bend toward their respective houses.
        let shortArrival = (try XCTUnwrap(lengths["red_approach"]) + XCTUnwrap(lengths["short"]) + 1) / initial.tuning.vanSpeed
        let blueArrival = try XCTUnwrap(lengths["blue_approach"]) / initial.tuning.vanSpeed
        let longArrival = (try XCTUnwrap(lengths["red_approach"]) + XCTUnwrap(lengths["long"])
            + XCTUnwrap(lengths["detour_up"]) + XCTUnwrap(lengths["detour_back"]) + 1) / initial.tuning.vanSpeed
        XCTAssertTrue(abs(shortArrival - blueArrival) < initial.tuning.crashDistance / initial.tuning.vanSpeed)
        XCTAssertTrue(longArrival - blueArrival >= 1)
        XCTAssertTrue(try XCTUnwrap(lengths["blue_approach"]) < 4, "Use curved RoadPath length, not Manhattan distance")
        let redAtMerge = try XCTUnwrap(run.samples.first { $0.vans[0].position.y >= 4 })
        let blueAtMerge = try XCTUnwrap(run.samples.first { $0.vans[1].currentEdgeID == "blue_exit" })
        XCTAssertEqual(redAtMerge.time, longArrival, accuracy: initial.tuning.stepDuration + 1e-9)
        XCTAssertEqual(blueAtMerge.time, blueArrival, accuracy: initial.tuning.stepDuration + 1e-9)
        XCTAssertTrue(redAtMerge.time - blueAtMerge.time >= 1)
        print("MV-29 Merge: crash \(crash.runTime)s at \(point); merge arrivals short=\(shortArrival), blue=\(blueArrival), long=\(longArrival); minimum safe separation=\(minimumSeparation(run.samples))")
    }

    func testLevelEightLoopReleaseHasComfortableWindowAndRequiresLiveInput() throws {
        let level = try level("level_008")
        let script = try PrototypeSolutionScript.load(levelID: level.id)
        XCTAssertEqual(script.planTaps, ["entry_switch"])
        XCTAssertEqual(script.liveTaps.map(\.nodeID), ["loop_switch"])
        XCTAssertEqual(script.liveTaps.map(\.atTime), [5])
        XCTAssertEqual(level.parChanges, 2)
        let run = try trace(level, script: script)
        XCTAssertEqual(run.engine.outcome, .win)
        XCTAssertEqual(run.engine.changeCount, level.parChanges)
        XCTAssertTrue(minimumSeparation(run.samples) > run.engine.tuning.crashDistance)
        let hold = try XCTUnwrap(run.samples.first { $0.vans[0].currentEdgeID == "hold" })
        let release = try XCTUnwrap(run.samples.first { $0.vans[0].currentEdgeID == "release" })
        XCTAssertEqual(hold.time, 10.0 / 3, accuracy: run.engine.tuning.stepDuration + 1e-9)
        XCTAssertEqual(release.time, 26.0 / 3, accuracy: run.engine.tuning.stepDuration + 1e-9)
        let unlocked = try XCTUnwrap(run.samples.first { $0.time > hold.time && !$0.locked.contains("loop_switch") })
        let relocked = try XCTUnwrap(run.samples.first { $0.time > unlocked.time && $0.locked.contains("loop_switch") })
        XCTAssertTrue(relocked.time - unlocked.time >= 1)
        XCTAssertTrue(unlocked.time <= script.liveTaps[0].atTime && script.liveTaps[0].atTime < relocked.time)
        let before = try MultiVanEngine(level: level)
        XCTAssertEqual(before.tapSwitch(nodeID: "entry_switch"), .accepted)
        before.go(); before.advance(by: unlocked.time - before.tuning.stepDuration)
        XCTAssertEqual(before.tapSwitch(nodeID: "loop_switch"), .rejectedLocked)
        XCTAssertEqual(before.runtimeGraph.nodesByID["loop_switch"]?.activeOutgoingEdgeID, "hold")
        before.advance(by: before.tuning.stepDuration)
        XCTAssertEqual(before.tapSwitch(nodeID: "loop_switch"), .accepted)
        XCTAssertEqual(before.runtimeGraph.nodesByID["loop_switch"]?.activeOutgoingEdgeID, "release")
        XCTAssertEqual(before.previewRoutes[0].ending, .matchingHouse)
        // Sweep the human interaction window, using the same MV-18 runner.
        for tick in 36...84 {
            _ = try PrototypeSolutionRunner.verify(level: level, script: .init(planTaps: script.planTaps,
                liveTaps: [.init(atTime: Double(tick) / 10, nodeID: "loop_switch")]))
        }
        let early = try PrototypeSolutionRunner.run(level: level, script: .init(planTaps: script.planTaps,
            liveTaps: [.init(atTime: 2.75, nodeID: "loop_switch")]))
        guard case .failCrash = early.outcome else { return XCTFail("Releasing Red on its first pass must crash") }
        let held = try trace(level, script: .init(planTaps: script.planTaps))
        XCTAssertNil(held.engine.outcome)
        XCTAssertEqual(held.engine.runTime, 120)
        XCTAssertEqual(held.engine.vans.map(\.status), [.driving, .parked])
        XCTAssertEqual(held.engine.previewRoutes[0].ending, .loopLimit)
        XCTAssertTrue(held.samples.filter { $0.vans[0].currentEdgeID == "hold" }.count > 100)
        XCTAssertTrue(minimumSeparation(held.samples) > held.engine.tuning.crashDistance)
        print("MV-29 Loop: unlocked [\(unlocked.time), \(relocked.time))s; hold=\(hold.time), release=\(release.time); minimum separation=\(minimumSeparation(run.samples))")
    }

    func testLevelNineRedAndBlueUseDistinctExitsWithAnUnlockedGap() throws {
        let level = try level("level_009")
        let script = try PrototypeSolutionScript.load(levelID: level.id)
        XCTAssertEqual(script.planTaps, ["entry_switch"])
        XCTAssertEqual(script.liveTaps.map(\.nodeID), ["switch"])
        XCTAssertEqual(script.liveTaps.map(\.atTime), [2.25])
        XCTAssertEqual(level.parChanges, 2)
        let run = try trace(level, script: script)
        let red = try XCTUnwrap(run.samples.first { $0.vans[0].currentEdgeID == "red_exit" })
        let blue = try XCTUnwrap(run.samples.first { $0.vans[1].currentEdgeID == "blue_exit" })
        XCTAssertTrue(blue.time - red.time >= 1)
        let unlocked = try XCTUnwrap(run.samples.first { $0.time > red.time && !$0.locked.contains("switch") })
        let relocked = try XCTUnwrap(run.samples.first { $0.time > unlocked.time && $0.locked.contains("switch") })
        XCTAssertTrue(relocked.time - unlocked.time >= 1)
        let tap = try XCTUnwrap(run.samples.first { $0.time >= script.liveTaps[0].atTime })
        XCTAssertEqual(tap.vans.map(\.currentEdgeID), ["red_exit", "blue_approach"])
        XCTAssertFalse(tap.locked.contains("switch"))
        for van in tap.vans {
            XCTAssertTrue(hypot(van.position.x - 2, van.position.y - 3) > run.engine.tuning.liveSwitchLockRadius)
        }
        XCTAssertTrue(run.samples.filter { $0.time >= red.time }.allSatisfy { $0.vans[0].currentEdgeID == "red_exit" })
        XCTAssertTrue(run.samples.filter { $0.time >= blue.time }.allSatisfy { $0.vans[1].currentEdgeID == "blue_exit" })
        XCTAssertEqual(run.engine.outcome, .win)
        XCTAssertEqual(run.engine.changeCount, level.parChanges)
        XCTAssertEqual(run.engine.vans.map(\.status), [.parked, .parked])
        XCTAssertTrue(minimumSeparation(run.samples) > run.engine.tuning.crashDistance)
        for time in [red.time, relocked.time] {
            let engine = try MultiVanEngine(level: level)
            XCTAssertEqual(engine.tapSwitch(nodeID: "entry_switch"), .accepted)
            engine.go(); engine.advance(by: time)
            XCTAssertEqual(engine.tapSwitch(nodeID: "switch"), .rejectedLocked)
            XCTAssertEqual(engine.changeCount, 1)
        }
        for tick in 16...30 {
            _ = try PrototypeSolutionRunner.verify(level: level, script: .init(planTaps: script.planTaps,
                liveTaps: [.init(atTime: Double(tick) / 10, nodeID: "switch")]))
        }
        for taps in [[], script.planTaps] {
            let frozen = try PrototypeSolutionRunner.run(level: level, script: .init(planTaps: taps))
            XCTAssertNotEqual(frozen.outcome, .win)
        }
        print("MV-29 Split: Red=\(red.time), Blue=\(blue.time); unlocked [\(unlocked.time), \(relocked.time))s; minimum separation=\(minimumSeparation(run.samples))")
    }

    func testLevelsEightAndNineCannotWinWithAnyStaticConfiguration() throws {
        for id in ["level_008", "level_009"] {
            let level = try level(id)
            let liveSwitch = try XCTUnwrap(level.liveSwitchNodeIDs.first)
            for taps in [[], ["entry_switch"], [liveSwitch], ["entry_switch", liveSwitch]] {
                let run = try trace(level, script: .init(planTaps: taps))
                XCTAssertNotEqual(run.engine.outcome, .win, "\(id): static settings \(taps) bypassed the live lesson")
            }
        }
    }

    func testTimingLevelSolutionsRemainIdenticalAcrossFramePartitions() throws {
        for id in ["level_007", "level_008", "level_009", "level_010", "level_011", "level_012"] {
            let level = try level(id)
            let script = try PrototypeSolutionScript.load(levelID: id)
            let reference = try PrototypeSolutionRunner.verify(level: level, script: script)
            for frames in [[0.25], [1.0 / 60], [0.004, 0.030], [0.003, 0.017, 0.31, 0.67]] {
                for _ in 0..<2 {
                    let replay = try replay(level, script: script, frames: frames, duration: 20)
                    assertSameState(replay.engine, reference)
                    XCTAssertEqual(replay.engine.changeCount, level.parChanges)
                }
            }
        }
    }

    // MV-30: compare authoritative state exactly. Each engine executes the same
    // fixed-step arithmetic, so no floating-point tolerance is needed here.
    private func assertSameState(_ actual: MultiVanEngine, _ expected: MultiVanEngine,
                                 file: StaticString = #filePath, line: UInt = #line) {
        XCTAssertEqual(actual.outcome, expected.outcome, file: file, line: line)
        XCTAssertEqual(actual.phase, expected.phase, file: file, line: line)
        XCTAssertEqual(actual.runTime, expected.runTime, file: file, line: line)
        XCTAssertEqual(actual.vans.map(\.id), expected.vans.map(\.id), file: file, line: line)
        XCTAssertEqual(actual.vans.map(\.status), expected.vans.map(\.status), file: file, line: line)
        XCTAssertEqual(actual.vans.map(\.position), expected.vans.map(\.position), file: file, line: line)
        XCTAssertEqual(actual.vans.map(\.currentEdgeID), expected.vans.map(\.currentEdgeID), file: file, line: line)
        XCTAssertEqual(actual.vans.map(\.distanceAlongEdge), expected.vans.map(\.distanceAlongEdge), file: file, line: line)
        let switches = actual.level.graph.nodes.filter { (2...4).contains($0.outgoingEdgeIDs.count) }.map(\.id)
        XCTAssertEqual(switches.map { actual.runtimeGraph.nodesByID[$0]?.activeOutgoingEdgeID },
                       switches.map { expected.runtimeGraph.nodesByID[$0]?.activeOutgoingEdgeID }, file: file, line: line)
        XCTAssertEqual(actual.changeCount, expected.changeCount, file: file, line: line)
        XCTAssertEqual(actual.lastFailPoint, expected.lastFailPoint, file: file, line: line)
    }

    private struct ReplayTap: Equatable {
        let scriptIndex: Int
        let time: TimeInterval
        let vanEdges: [String?]
    }

    private func replay(_ level: MultiVanLevel, script: PrototypeSolutionScript = .init(),
                        frames: [TimeInterval], duration: TimeInterval, playbackSpeeds: [Bool]? = nil,
                        tuning: MultiVanTuning = .default) throws
        -> (engine: MultiVanEngine, taps: [ReplayTap], events: [MultiVanEvent]) {
        guard !frames.isEmpty, frames.allSatisfy({ $0.isFinite && $0 > 0 }),
              duration.isFinite, duration >= 0 else {
            throw PrototypeSolutionError("Invalid replay frame partition or duration")
        }
        let engine = try MultiVanEngine(level: level, tuning: tuning)
        XCTAssertEqual(engine.phase, .plan)
        XCTAssertNil(engine.outcome)
        XCTAssertEqual(engine.runTime, 0)
        XCTAssertEqual(engine.changeCount, 0)
        for node in script.planTaps { XCTAssertEqual(engine.tapSwitch(nodeID: node), .accepted) }
        engine.go()
        let driver = MultiVanFrameDriver()
        var wallTime = 0.0
        var events = engine.drainEvents()
        driver.advance(at: Date(timeIntervalSinceReferenceDate: wallTime), engine: engine, isActive: true)
        func advance(_ simulationDelta: Double, multiplier: Double) {
            if playbackSpeeds != nil {
                // Split only to respect MV-15's raw wall-clock cap. Action
                // boundaries still land at the exact established simulation time.
                var remaining = simulationDelta / multiplier
                while remaining > 1e-12 {
                    let delta = min(remaining, 0.25)
                    wallTime += delta
                    driver.advance(at: Date(timeIntervalSinceReferenceDate: wallTime), engine: engine, isActive: true)
                    events += engine.drainEvents()
                    remaining -= delta
                }
            } else {
                engine.advance(by: simulationDelta)
                events += engine.drainEvents()
            }
        }
        // Match MV-18/MV-21: chronological order, script order for ties, and
        // non-grid timestamps applied at the next fixed-step boundary.
        let taps = script.liveTaps.enumerated().sorted {
            $0.element.atTime == $1.element.atTime ? $0.offset < $1.offset : $0.element.atTime < $1.element.atTime
        }
        let boundaries = taps.map { ceil($0.element.atTime / engine.tuning.stepDuration) * engine.tuning.stepDuration }
        var elapsed = 0.0, frame = 0, nextTap = 0
        var applied: [ReplayTap] = []
        while elapsed < duration {
            let held = playbackSpeeds.map { $0[frame % $0.count] } ?? false
            let multiplier = held ? engine.tuning.fastForwardMultiplier : 1
            if playbackSpeeds != nil {
                driver.setFastForwarding(held, at: Date(timeIntervalSinceReferenceDate: wallTime), engine: engine, isActive: true)
                events += engine.drainEvents()
            }
            let frameEnd = min(elapsed + frames[frame % frames.count] * multiplier, duration)
            while nextTap < taps.count, boundaries[nextTap] <= frameEnd {
                let boundary = boundaries[nextTap]
                advance(boundary - elapsed, multiplier: multiplier)
                elapsed = boundary
                // The accumulator has consumed exactly the steps preceding the
                // event. Never wait for a render frame to overshoot its time.
                XCTAssertEqual(engine.runTime, boundary)
                let tap = taps[nextTap]
                applied.append(ReplayTap(scriptIndex: tap.offset, time: engine.runTime,
                                         vanEdges: engine.vans.map(\.currentEdgeID)))
                XCTAssertEqual(engine.tapSwitch(nodeID: tap.element.nodeID), .accepted)
                events += engine.drainEvents()
                nextTap += 1
            }
            advance(frameEnd - elapsed, multiplier: multiplier)
            elapsed = frameEnd // Keep the unused portion of a split frame.
            frame += 1
        }
        // Supply the same total elapsed time even after a terminal outcome;
        // stopping on whichever render frame finishes would hide unequal totals.
        XCTAssertEqual(elapsed, duration)
        XCTAssertEqual(nextTap, taps.count)
        return (engine, applied, events)
    }

    func testMV38AllSolutionsAndCrashMatchAcrossPlaybackSpeedsAndFramePartitions() throws {
        for number in 1...12 {
            let level = try level(String(format: "level_%03d", number))
            let script = try PrototypeSolutionScript.load(levelID: level.id)
            let reference = try replay(level, script: script, frames: [1.0 / 60], duration: 20)
            XCTAssertEqual(reference.engine.outcome, .win)
            XCTAssertEqual(reference.engine.changeCount, level.parChanges)
            if number == 5 {
                XCTAssertEqual(reference.engine.changeCount, 2)
                XCTAssertEqual(reference.engine.vans.map(\.status), [.parked, .parked])
            }
            for frames in [[1.0 / 60], [0.004, 0.030]] {
                for speeds in [[false], [true], [false, true, true, false]] {
                    let run = try replay(level, script: script, frames: frames, duration: 20, playbackSpeeds: speeds)
                    assertSameState(run.engine, reference.engine)
                    XCTAssertEqual(run.taps, reference.taps)
                    XCTAssertEqual(run.events, reference.events)
                    XCTAssertEqual(run.events.last, .allDelivered)
                }
            }
        }
        let level = try level("level_007")
        let reference = try replay(level, frames: [1.0 / 60], duration: 20)
        guard case .failCrash = reference.engine.outcome else { return XCTFail("Expected crash") }
        for frames in [[1.0 / 60], [0.004, 0.030]] {
            for speeds in [[false], [true], [false, true, true, false]] {
                let run = try replay(level, frames: frames, duration: 20, playbackSpeeds: speeds)
                assertSameState(run.engine, reference.engine)
                XCTAssertEqual(run.events, reference.events)
                XCTAssertEqual(run.events.last, .crashed(point: try XCTUnwrap(reference.engine.lastFailPoint)))
            }
        }
    }

    func testMV38EquivalentPartialBudgetsExecuteEveryFixedStep() throws {
        let level = try level("level_007")
        for budget in [1.0, 1.0 + MultiVanTuning.default.stepDuration] {
            let reference = try replay(level, frames: [1.0 / 60], duration: budget)
            XCTAssertEqual(reference.engine.runTime, budget)
            for frames in [[1.0 / 60], [0.004, 0.030]] {
                for speeds in [[false], [true], [false, true]] {
                    let run = try replay(level, frames: frames, duration: budget, playbackSpeeds: speeds)
                    assertSameState(run.engine, reference.engine)
                    XCTAssertEqual(run.events, reference.events)
                }
            }
        }
    }

    func testLevelSevenUntouchedCrashReplaysAcrossRegularAndUnevenFrames() throws {
        let level = try level("level_007")
        let initial = try MultiVanEngine(level: level)
        XCTAssertEqual(initial.previewRoutes.map(\.ending), [.matchingHouse, .matchingHouse])
        let reference = try PrototypeSolutionRunner.run(level: level, script: .init())
        guard case let .failCrash(ids, point) = reference.outcome else { return XCTFail("Expected merge crash") }
        XCTAssertEqual(ids, ["red", "blue"])
        XCTAssertEqual(reference.lastFailPoint, point)
        for frames in [[1.0 / 60], [0.004, 0.030]] {
            for _ in 0..<2 {
                let run = try replay(level, frames: frames, duration: 20)
                assertSameState(run.engine, reference)
                XCTAssertEqual(run.engine.vans.map(\.status), [.crashed, .crashed])
                XCTAssertEqual(run.engine.changeCount, 0)
            }
        }
    }

    func testLevelNineReplaySplitsFramesBeforeTheTimedSwitchStep() throws {
        let level = try level("level_009")
        let script = try PrototypeSolutionScript.load(levelID: level.id)
        XCTAssertEqual(script.planTaps, ["entry_switch"])
        XCTAssertEqual(script.liveTaps.map(\.nodeID), ["switch"])
        XCTAssertEqual(script.liveTaps.map(\.atTime), [2.25])
        // Inspect the action boundary as well as the terminal state: a late tap
        // can still win this level and would otherwise escape a final-only check.
        let regular = try replay(level, script: script, frames: [1.0 / 60], duration: 2.25)
        let uneven = try replay(level, script: script, frames: [0.004, 0.030], duration: 2.25)
        assertSameState(uneven.engine, regular.engine)
        XCTAssertEqual(regular.engine.phase, .run)
        XCTAssertEqual(regular.engine.runTime, 2.25)
        XCTAssertEqual(regular.taps, [ReplayTap(scriptIndex: 0, time: 2.25,
                                             vanEdges: ["red_exit", "blue_approach"])])
        XCTAssertEqual(uneven.taps, regular.taps)
        XCTAssertEqual(regular.engine.runtimeGraph.nodesByID["switch"]?.activeOutgoingEdgeID, "blue_exit")
        let reference = try PrototypeSolutionRunner.verify(level: level, script: script)
        XCTAssertEqual(reference.vans.map(\.currentEdgeID), ["red_exit", "blue_exit"])
        for frames in [[1.0 / 60], [0.004, 0.030]] {
            for _ in 0..<2 {
                let run = try replay(level, script: script, frames: frames, duration: 20)
                XCTAssertEqual(run.taps, regular.taps)
                assertSameState(run.engine, reference)
            }
        }
    }

    func testReplayPreservesChronologicalAndSameTimeScriptOrder() throws {
        let level = try MultiVanLiveSwitchTests.fixture()
        let script = PrototypeSolutionScript(planTaps: ["switch"], liveTaps: [
            .init(atTime: 1, nodeID: "switch"), .init(atTime: 0, nodeID: "switch"),
            .init(atTime: 1, nodeID: "switch"), .init(atTime: 1, nodeID: "switch")
        ])
        let reference = try PrototypeSolutionRunner.verify(level: level, script: script)
        for frames in [[1.0 / 60], [0.004, 0.030]] {
            let run = try replay(level, script: script, frames: frames, duration: 10)
            XCTAssertEqual(run.taps.map(\.scriptIndex), [1, 0, 2, 3])
            XCTAssertEqual(run.taps.map(\.time), [0, 1, 1, 1])
            assertSameState(run.engine, reference)
        }
    }

    func testReplayRejectsInvalidPartitionsAndDistinguishesUnequalDurations() throws {
        let level = try level("level_007")
        for frames: [Double] in [[], [0], [-0.004, 0.030], [.nan], [.infinity]] {
            assertDiagnostic(["Invalid replay"]) { _ = try replay(level, frames: frames, duration: 1) }
        }
        let regular = try replay(level, frames: [1.0 / 60], duration: 1)
        let uneven = try replay(level, frames: [0.004, 0.030], duration: 1)
        assertSameState(uneven.engine, regular.engine)
        XCTAssertEqual(regular.engine.phase, .run)
        let extraStep = try replay(level, frames: [0.004, 0.030], duration: 1 + regular.engine.tuning.stepDuration)
        XCTAssertEqual(extraStep.engine.runTime, regular.engine.runTime + regular.engine.tuning.stepDuration)
        XCTAssertNotEqual(extraStep.engine.vans.map(\.position), regular.engine.vans.map(\.position))
    }
}

extension PrototypeSolutionTests {
    func testMV37TimedSwitchAppearanceTracksMovementWithoutChangingSolutions() throws {
        for (id, tapTime) in [("level_006", 2.75), ("level_008", 5.0), ("level_009", 2.25)] {
            let level = try level(id)
            let script = try PrototypeSolutionScript.load(levelID: id)
            let tap = try XCTUnwrap(script.liveTaps.first)
            XCTAssertEqual(tap.atTime, tapTime)
            let run = try MultiVanEngine(level: level)
            for node in script.planTaps { run.tapSwitch(nodeID: node) }
            run.go()
            var sawLocked = false
            var sawUnlock = false
            var wasLocked = false
            while run.runTime < tapTime {
                let state = MultiVanSwitchAppearance(engine: run, nodeID: tap.nodeID)
                XCTAssertEqual(state.showsLock, run.lockedSwitchNodeIDs.contains(tap.nodeID), id)
                if wasLocked && state.isAvailable { sawUnlock = true }
                wasLocked = state.showsLock
                sawLocked = sawLocked || state.showsLock
                run.advance(by: run.tuning.stepDuration)
            }
            XCTAssertTrue(sawLocked, id)
            XCTAssertTrue(sawUnlock, id)
            XCTAssertTrue(MultiVanSwitchAppearance(engine: run, nodeID: tap.nodeID).pulses, id)
            let before = run.runtimeGraph.nodesByID[tap.nodeID]?.activeOutgoingEdgeID
            XCTAssertEqual(run.tapSwitch(nodeID: tap.nodeID), .accepted, id)
            let after = run.runtimeGraph.nodesByID[tap.nodeID]?.activeOutgoingEdgeID
            XCTAssertNotEqual(before, after, id)
            var blueUsedExit = false
            while run.outcome == nil && run.runTime < 120 {
                run.advance(by: run.tuning.stepDuration)
                if run.vans.contains(where: { $0.color == .blue && $0.currentEdgeID == after }) {
                    blueUsedExit = true
                }
            }
            if id == "level_009" { XCTAssertTrue(blueUsedExit) }
            let reference = try PrototypeSolutionRunner.verify(level: level, script: script)
            XCTAssertEqual(run.outcome, .win, id)
            XCTAssertEqual(run.changeCount, level.parChanges, id)
            XCTAssertEqual(run.runTime, reference.runTime, id)
            XCTAssertEqual(run.vans.map(\.position), reference.vans.map(\.position), id)
            run.retry()
            XCTAssertTrue(MultiVanSwitchAppearance(engine: run, nodeID: tap.nodeID).isAvailable)
            XCTAssertFalse(MultiVanSwitchAppearance(engine: run, nodeID: tap.nodeID).pulses)
        }
    }
}

// MV-42: authoring checks reuse MV-18's scripts and MV-29's actual engine samples.
extension PrototypeSolutionTests {
    func testMV42LevelTenRequiresAllThreeIndependentColourDecisions() throws {
        let level = try level("level_010")
        let script = try PrototypeSolutionScript.load(levelID: level.id)
        XCTAssertEqual(level.name, "Three's Company")
        XCTAssertEqual(level.vans.map(\.color), [.red, .blue, .yellow])
        XCTAssertEqual(script.planTaps, ["red_switch", "blue_switch", "yellow_switch"])
        XCTAssertTrue(script.liveTaps.isEmpty)
        XCTAssertTrue(level.liveSwitchNodeIDs.isEmpty)
        XCTAssertEqual(try MultiVanEngine(level: level).previewRoutes.map(\.ending), [.wrongHouse, .wrongHouse, .deadEnd])
        // Every static configuration, including each missing planning decision.
        for mask in 0..<8 {
            let taps = script.planTaps.enumerated().filter { mask & (1 << $0.offset) != 0 }.map(\.element)
            let run = try PrototypeSolutionRunner.run(level: level, script: .init(planTaps: taps))
            XCTAssertEqual(run.changeCount, taps.count)
            XCTAssertEqual(run.outcome == .win, mask == 7)
            if taps.count == 2 {
                switch script.planTaps.first(where: { !taps.contains($0) }) {
                case "red_switch": XCTAssertEqual(run.outcome, .failWrongHouse(vanID: "red", houseNodeID: "blue_house"))
                case "blue_switch": XCTAssertEqual(run.outcome, .failWrongHouse(vanID: "blue", houseNodeID: "red_house"))
                default: XCTAssertEqual(run.outcome, .failStuck(vanID: "yellow", nodeID: "barrier"))
                }
            }
        }
    }

    /// Exhaust the small authored configuration space, using actual exit order.
    private func planningConfigurations(_ level: MultiVanLevel) -> [[String]] {
        level.graph.nodes.filter { $0.outgoingEdgeIDs.count > 1 && !level.liveSwitchNodeIDs.contains($0.id) }
            .reduce([[]]) { plans, node in
                plans.flatMap { plan in
                    (0..<node.outgoingEdgeIDs.count).map { plan + Array(repeating: node.id, count: $0) }
                }
            }
    }

    /// Negative variants can finish before the scheduled tap, or loop for 120 s.
    /// Keep those inspectable without weakening MV-18's strict winning runner.
    private func variant(_ level: MultiVanLevel, plan: [String], liveTime: Double? = nil) throws -> MultiVanEngine {
        let engine = try MultiVanEngine(level: level)
        for node in plan { XCTAssertEqual(engine.tapSwitch(nodeID: node), .accepted) }
        engine.go()
        var tapped = false
        while engine.outcome == nil && engine.runTime < 120 {
            if let liveTime, !tapped, engine.runTime >= liveTime {
                XCTAssertEqual(engine.tapSwitch(nodeID: "split_switch"), .accepted)
                tapped = true
            }
            engine.advance(by: engine.tuning.stepDuration)
        }
        return engine
    }

    func testRushBlueDetourStaysSeparateFromTheRoadHome() throws {
        let engine = try MultiVanEngine(level: level("level_011"))
        let home = try XCTUnwrap(engine.runtimeGraph.edgesByID["blue_exit"]).roadPath
        for id in ["long", "detour_left_road", "detour_down", "detour_join"] {
            let detour = try XCTUnwrap(engine.runtimeGraph.edgesByID[id]).roadPath
            var clearance = Double.infinity
            for distance in stride(from: 0.0, through: detour.totalLength, by: 0.05) {
                let point = detour.point(atDistance: distance)
                for homeDistance in stride(from: 0.0, through: home.totalLength, by: 0.05) {
                    let other = home.point(atDistance: homeDistance)
                    clearance = min(clearance, hypot(point.x - other.x, point.y - other.y))
                }
            }
            XCTAssertGreaterThan(clearance, 0.75, "\(id) must not look connected to Blue's road home")
        }
    }

    func testMV42RushAndFinalParAreMinimumAndStaticSettingsCannotWin() throws {
        for id in ["level_011", "level_012"] {
            let level = try level(id)
            let script = try PrototypeSolutionScript.load(levelID: id)
            XCTAssertEqual(level.name, id == "level_011" ? "Rush" : "Big Delivery")
            XCTAssertEqual(level.vans.map(\.color), id == "level_011" ? [.red, .blue, .yellow] : [.red, .blue, .yellow, .green])
            XCTAssertEqual(level.graph.nodes.filter { $0.outgoingEdgeIDs.count > 1 }.count, id == "level_011" ? 3 : 5)
            XCTAssertEqual(level.liveSwitchNodeIDs, ["split_switch"])
            XCTAssertEqual(script.liveTaps.map(\.atTime), [id == "level_011" ? 4.95 : 5.25])
            XCTAssertEqual(script.liveTaps.map(\.nodeID), ["split_switch"])
            let configurations = planningConfigurations(level)
            XCTAssertEqual(configurations.count, id == "level_011" ? 6 : 24)
            var wins = 0
            for plan in configurations {
                for livePlan in [[], ["split_switch"]] {
                    let staticRun = try variant(level, plan: plan + livePlan)
                    XCTAssertNotEqual(staticRun.outcome, .win, "\(id): static \(plan + livePlan)")
                }
                let run = try variant(level, plan: plan + ["split_switch"], liveTime: script.liveTaps.first?.atTime)
                if run.outcome == .win {
                    wins += 1
                    XCTAssertEqual(plan.count, level.parChanges)
                    XCTAssertEqual(run.changeCount, level.parChanges)
                    XCTAssertEqual(run.runtimeGraph.nodesByID["split_switch"]?.activeOutgoingEdgeID,
                                   level.initialSwitchEdges["split_switch"])
                }
            }
            XCTAssertEqual(wins, 1, "\(id): exactly one normal-switch configuration can win")
            let run = try PrototypeSolutionRunner.verify(level: level, script: script)
            XCTAssertEqual(run.changeCount, id == "level_011" ? 3 : 5)
            XCTAssertEqual(script.planTaps.count, level.parChanges + 1)
        }
    }

    func testMV42FinalLoopHoldsAndShortcutCrashesDeterministically() throws {
        let level = try level("level_012")
        let script = try PrototypeSolutionScript.load(levelID: level.id)
        let hold = script.planTaps.filter { $0 != "route_switch" }
        let engine = try MultiVanEngine(level: level)
        for node in hold { XCTAssertEqual(engine.tapSwitch(nodeID: node), .accepted) }
        XCTAssertEqual(engine.previewRoutes[1].ending, .loopLimit)
        let loop = try variant(level, plan: hold)
        XCTAssertNil(loop.outcome)
        XCTAssertEqual(loop.runTime, 120)
        XCTAssertEqual(loop.vans.map(\.status), [.parked, .driving, .parked, .parked])
        let short = PrototypeSolutionScript(planTaps: hold + ["route_switch"])
        let reference = try PrototypeSolutionRunner.run(level: level, script: short)
        guard case let .failCrash(ids, point) = reference.outcome else { return XCTFail("Short road must crash at the merge") }
        XCTAssertEqual(ids, ["red", "blue"])
        XCTAssertTrue(hypot(point.x - 2, point.y - 3) < 0.5)
        for frames in [[1.0 / 60], [0.004, 0.030]] {
            for _ in 0..<2 {
                assertSameState(try replay(level, script: short, frames: frames, duration: 20).engine, reference)
            }
        }
    }

    func testMV42LiveWindowsClearanceAndEveryAcceptedStepWinAtPar() throws {
        for (id, blueMerge, blueExit, relock, unlock) in [
            ("level_011", 4.0, 640.0 / 120, 609.0 / 120, 672.0 / 120),
            ("level_012", 5.95, 794.0 / 120, 6.35, 826 * MultiVanTuning.default.stepDuration)
        ] {
            let level = try level(id)
            let script = try PrototypeSolutionScript.load(levelID: id)
            let run = try trace(level, script: script)
            XCTAssertEqual(run.engine.outcome, .win)
            let redMerge = try XCTUnwrap(run.samples.first { $0.vans[0].currentEdgeID == "shared_stem" })
            let blueAtMerge = try XCTUnwrap(run.samples.first { $0.vans[1].currentEdgeID == "shared_stem" })
            XCTAssertEqual(redMerge.time, (id == "level_011" ? 314.0 : 394.0) / 120)
            XCTAssertEqual(blueAtMerge.time, blueMerge)
            XCTAssertGreaterThan(blueAtMerge.time - redMerge.time, id == "level_011" ? 1.3 : 2.5)
            XCTAssertEqual(run.samples.first { $0.vans[0].currentEdgeID == "red_exit" }?.time, 474 * MultiVanTuning.default.stepDuration)
            XCTAssertEqual(run.samples.first { $0.vans[1].currentEdgeID == "blue_exit" }?.time, blueExit)
            var locks: [Double] = []
            var wasLocked = false
            for sample in run.samples {
                let locked = sample.locked.contains("split_switch")
                if locked != wasLocked { locks.append(sample.time) }
                wasLocked = locked
            }
            XCTAssertEqual(locks, [442.0 / 120, 506.0 / 120, relock, unlock])
            let start = locks[1], end = locks[2]
            XCTAssertGreaterThan(end - start, id == "level_011" ? 0.8 : 2)
            let tapTime = try XCTUnwrap(script.liveTaps.first?.atTime)
            XCTAssertGreaterThan(tapTime - start, id == "level_011" ? 0.1 : 1)
            XCTAssertGreaterThan(end - tapTime, id == "level_011" ? 0.1 : 1)
            // Every fixed-step boundary in the entire inter-van unlocked gap.
            for tick in Int((start * 120).rounded())..<Int((end * 120).rounded()) {
                _ = try PrototypeSolutionRunner.verify(level: level, script: .init(planTaps: script.planTaps,
                    liveTaps: [.init(atTime: Double(tick) / 120, nodeID: "split_switch")]))
            }
            var clearance = Double.infinity
            for sample in run.samples {
                let driving = sample.vans.filter { $0.status == .driving }
                for a in driving.indices {
                    for b in driving.indices where b > a {
                        clearance = min(clearance, hypot(driving[a].position.x - driving[b].position.x,
                                                         driving[a].position.y - driving[b].position.y))
                    }
                }
            }
            XCTAssertGreaterThan(clearance, run.engine.tuning.crashDistance)
            print("MV42 \(id): merge Red=\(redMerge.time), Blue=\(blueMerge); split Red=\(474 * MultiVanTuning.default.stepDuration), Blue=\(blueExit); locks=\(locks); accepted [\(start), \(end)) duration=\(end - start); minimum driving clearance=\(clearance); win=\(run.engine.runTime); count=\(run.engine.changeCount)")
        }
    }

    func testMV42MissingEarlyLateAndLockedLiveTaps() throws {
        for id in ["level_011", "level_012"] {
            let level = try level(id)
            let script = try PrototypeSolutionScript.load(levelID: id)
            let missing = try PrototypeSolutionRunner.run(level: level, script: .init(planTaps: script.planTaps))
            XCTAssertEqual(missing.outcome, .failWrongHouse(vanID: "blue", houseNodeID: "red_house"))
            let early = try PrototypeSolutionRunner.run(level: level, script: .init(planTaps: script.planTaps,
                liveTaps: [.init(atTime: 0, nodeID: "split_switch")]))
            if id == "level_011" {
                XCTAssertEqual(early.outcome, .failWrongHouse(vanID: "red", houseNodeID: "blue_house"))
            } else {
                // Big Delivery's east exit crosses Blue's detour while Blue is there.
                guard case let .failCrash(earlyIDs, _) = early.outcome else { return XCTFail("Early split must crash") }
                XCTAssertEqual(earlyIDs, ["red", "blue"])
            }
            let late = try PrototypeSolutionRunner.run(level: level, script: .init(planTaps: script.planTaps,
                liveTaps: [.init(atTime: 7, nodeID: "split_switch")]))
            XCTAssertEqual(late.outcome, .failWrongHouse(vanID: "blue", houseNodeID: "red_house"))
            let missingPlan = try variant(level, plan: script.planTaps.filter { $0 != "split_switch" }, liveTime: script.liveTaps.first?.atTime)
            if id == "level_011" {
                XCTAssertEqual(missingPlan.outcome, .failWrongHouse(vanID: "red", houseNodeID: "blue_house"))
            } else {
                guard case let .failCrash(missingPlanIDs, _) = missingPlan.outcome else { return XCTFail("Missing Red selection must crash") }
                XCTAssertEqual(missingPlanIDs, ["red", "blue"])
            }
            for time in [474 * MultiVanTuning.default.stepDuration, id == "level_011" ? 609.0 / 120 : 6.35] {
                let engine = try MultiVanEngine(level: level)
                for node in script.planTaps { XCTAssertEqual(engine.tapSwitch(nodeID: node), .accepted) }
                engine.go(); engine.advance(by: time)
                let before = engine.changeCount
                XCTAssertEqual(engine.tapSwitch(nodeID: "split_switch"), .rejectedLocked)
                XCTAssertEqual(engine.changeCount, before)
                XCTAssertEqual(engine.runtimeGraph.nodesByID["split_switch"]?.activeOutgoingEdgeID, "red_exit")
            }
            if id == "level_011" {
                let short = try variant(level, plan: script.planTaps.filter { $0 != "route_switch" })
                guard case let .failCrash(ids, _) = short.outcome else { return XCTFail("Rush shortcut must crash") }
                XCTAssertEqual(ids, ["red", "blue"])
                for frames in [[1.0 / 60], [0.004, 0.030]] {
                    assertSameState(try replay(level, script: .init(planTaps: script.planTaps.filter { $0 != "route_switch" }),
                                               frames: frames, duration: 20).engine, short)
                }
            }
        }
    }

    func testMV42EveryVanMustDeliverBeforeVictory() throws {
        for id in ["level_010", "level_011", "level_012"] {
            let level = try level(id)
            let script = try PrototypeSolutionScript.load(levelID: id)
            let reference = try PrototypeSolutionRunner.verify(level: level, script: script)
            let run = try replay(level, script: script, frames: [0.004, 0.030],
                                 duration: reference.runTime - reference.tuning.stepDuration)
            XCTAssertNil(run.engine.outcome)
            XCTAssertFalse(run.events.contains(.allDelivered))
            XCTAssertTrue(run.engine.vans.contains { $0.status == .driving })
            run.engine.advance(by: run.engine.tuning.stepDuration)
            XCTAssertEqual(run.engine.outcome, .win)
            XCTAssertTrue(run.engine.vans.allSatisfy { $0.status == .parked })
            XCTAssertEqual(run.engine.drainEvents().filter { $0 == .allDelivered }.count, 1)
        }
    }

    func testMV42AuthoredLastLevelsNavigateInOrderThenReturnToList() throws {
        let levels = try levels()
        XCTAssertEqual(levels.map(\.id), (1...12).map { String(format: "level_%03d", $0) })
        var session = MultiVanPrototypeSession()
        try session.open(try level("level_010"))
        for id in ["level_011", "level_012"] {
            let previous = try XCTUnwrap(session.engine)
            try session.next(in: levels)
            let next = try XCTUnwrap(session.engine)
            XCTAssertEqual(next.level.id, id)
            XCTAssertFalse(next === previous)
            XCTAssertEqual(next.phase, .plan)
            XCTAssertEqual(next.changeCount, 0)
        }
        try session.next(in: levels)
        XCTAssertNil(session.engine, "Final Next returns to the list; there is no Level 13")
    }
}
