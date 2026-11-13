import XCTest
@testable import TinyRoutes

/// Automatic signals, the drawbridge that runs on the same schedule, and icy
/// roads: the engine's contract and the experiment boards built on it.
final class MultiVanSignalTests: XCTestCase {
    private typealias Boards = MultiVanTestBoards

    private func light(_ level: MultiVanLevel) throws -> MultiVanSignal { try XCTUnwrap(level.signals.first) }

    private func outcomes(_ id: String, switchID: String = "blue_fork") throws -> [String: MultiVanTestBoards.Run] {
        let level = try Boards.experiment(id)
        var results: [String: MultiVanTestBoards.Run] = [:]
        for configuration in Boards.configurations(of: level) {
            let engine = try Boards.engine(level, selections: configuration)
            results[try XCTUnwrap(configuration[switchID])] = Boards.run(engine)
        }
        return results
    }

    // MARK: - Schedule

    func testScheduleIsFixedInTicksAndStartsWhereAuthored() throws {
        let signal = try light(Boards.experiment("experiment_signal_a"))
        XCTAssertEqual(signal.cycleTicks, 692)
        // Blue's road, all held, Red's road, all held.
        for (tick, group) in [(0, 0), (289, 0), (290, nil), (345, nil), (346, 1), (635, 1), (636, nil), (691, nil), (692, 0)] as [(Int, Int?)] {
            XCTAssertEqual(signal.nominalGroup(atTick: tick), group, "tick \(tick)")
        }
        XCTAssertEqual(signal.ticksUntilChange(atTick: 0), 290)
        XCTAssertEqual(signal.ticksUntilChange(atTick: 289), 1)
        XCTAssertEqual(signal.ticksUntilChange(atTick: 290), 56)
        // The other board starts the same cycle on Red's green.
        let shifted = try light(Boards.experiment("experiment_signal_b"))
        XCTAssertEqual(shifted.phases, signal.phases)
        XCTAssertEqual(shifted.nominalGroup(atTick: 0), 1)
        // A green is refused while another group is still inside, and never moved later.
        XCTAssertTrue(signal.admits(group: 0, atTick: 0, occupiedBy: []))
        XCTAssertTrue(signal.admits(group: 0, atTick: 0, occupiedBy: [0]))
        XCTAssertFalse(signal.admits(group: 0, atTick: 0, occupiedBy: [1]))
        XCTAssertFalse(signal.admits(group: 1, atTick: 0, occupiedBy: []))
    }

    func testEngineRefusesSignalsItCouldNotRun() throws {
        func reason(_ mutate: (inout [String: Any]) -> Void, zones: [[String: Any]]? = nil) throws -> String? {
            var json = try Boards.json("experiment_signal_a")
            var signal = try XCTUnwrap((json["signals"] as? [[String: Any]])?.first)
            mutate(&signal)
            json["signals"] = [signal]
            if let zones { json["roadZones"] = zones }
            do {
                _ = try MultiVanEngine(level: Boards.level(json))
                return nil
            } catch {
                return error.localizedDescription
            }
        }
        XCTAssertNil(try reason { _ in })
        XCTAssertTrue(try XCTUnwrap(reason { $0["approaches"] = [] }).contains("no approaches"))
        XCTAssertTrue(try XCTUnwrap(reason { $0["phases"] = [["group": 0, "ticks": 0]] }).contains("positive length"))
        XCTAssertTrue(try XCTUnwrap(reason { $0["phases"] = [["group": 0, "ticks": 10]] }).contains("group 1 is never let in"))
        XCTAssertTrue(try XCTUnwrap(reason { $0["phases"] = [["group": 0, "ticks": 5], ["group": 1, "ticks": 5], ["group": 7, "ticks": 5]] })
            .contains("opens group 7"))
        XCTAssertTrue(try XCTUnwrap(reason { $0["area"] = ["x": 1, "y": 3, "radius": 0] }).contains("positive radius"))
        XCTAssertTrue(try XCTUnwrap(reason { $0["area"] = ["x": 4, "y": 0, "radius": 0.3] }).contains("never enters"))
        let line = { (edge: String, distance: Double) -> [String: Any] in ["edgeID": edge, "stopDistance": distance, "group": 0] }
        XCTAssertTrue(try XCTUnwrap(reason { $0["approaches"] = [line("ghost", 1)]; $0["phases"] = [["group": 0, "ticks": 5]] }).contains("does not exist"))
        XCTAssertTrue(try XCTUnwrap(reason { $0["approaches"] = [line("blue_short", 0)]; $0["phases"] = [["group": 0, "ticks": 5]] })
            .contains("must sit along the road"))
        XCTAssertTrue(try XCTUnwrap(reason { $0["approaches"] = [line("blue_short", 1.3), line("blue_short", 1.2)]; $0["phases"] = [["group": 0, "ticks": 5]] })
            .contains("already has a stop line"))
        // A van cannot stop on ice, so ice cannot carry a stop line.
        let ice: [[String: Any]] = [["id": "ice", "kind": "ice", "edgeIDs": ["blue_short"]]]
        XCTAssertTrue(try XCTUnwrap(reason({ _ in }, zones: ice)).contains("icy"))
        // Signals and zones need their schema version.
        var json = try Boards.json("experiment_signal_a")
        json["schemaVersion"] = 2
        XCTAssertThrowsError(try Boards.level(json)) { XCTAssertTrue("\($0)".contains("signals need schemaVersion 3")) }
    }

    // MARK: - Wait or Wander

    func testTheLightFlipsWhichRoadIsSafeAgainstItsMatchedControl() throws {
        let withLight = try outcomes("experiment_signal_a")
        let otherPhase = try outcomes("experiment_signal_b")
        let noLight = try outcomes("experiment_signal_c")
        XCTAssertEqual(withLight.mapValues { Boards.name($0.engine.outcome) }, ["blue_short": "win", "blue_bypass": "crash"])
        XCTAssertEqual(otherPhase.mapValues { Boards.name($0.engine.outcome) }, ["blue_short": "win", "blue_bypass": "win"])
        XCTAssertEqual(noLight.mapValues { Boards.name($0.engine.outcome) }, ["blue_short": "crash", "blue_bypass": "win"])

        // The same streets on all three boards.
        let boards = try ["experiment_signal_a", "experiment_signal_b", "experiment_signal_c"].map(Boards.experiment)
        for board in boards.dropFirst() {
            XCTAssertEqual(board.graph.edges.map(\.id), boards[0].graph.edges.map(\.id))
            XCTAssertEqual(board.vans.map(\.startNodeID), boards[0].vans.map(\.startNodeID))
            XCTAssertEqual(board.initialSwitchEdges, boards[0].initialSwitchEdges)
        }
        XCTAssertTrue(boards[2].signals.isEmpty)

        // Without the light the vans reach the square together.
        guard case let .failCrash(_, square) = noLight["blue_short"]?.engine.outcome else { return XCTFail("expected a crash") }
        XCTAssertEqual(square.x, 1, accuracy: 0.3)
        XCTAssertEqual(square.y, 3, accuracy: 0.3)
        // With it, the crash moves to the ordinary crossing further on: green
        // protects the marked square and nothing after it.
        guard case let .failCrash(_, later) = withLight["blue_bypass"]?.engine.outcome else { return XCTFail("expected a crash") }
        XCTAssertEqual(later.y, 5, accuracy: 0.3)
        let signal = try light(boards[0])
        XCTAssertGreaterThan(hypot(later.x - signal.area.x, later.y - signal.area.y), signal.area.radius + 1)

        // The winning wait is no near miss: Blue passes a full van clear of held Red.
        XCTAssertGreaterThan(try XCTUnwrap(withLight["blue_short"]).closestApproach, 0.6)
        XCTAssertGreaterThan(try XCTUnwrap(noLight["blue_bypass"]).closestApproach, 1.0)
        // Red waits in one, Blue in the other: the phase changes who goes first.
        func held(_ run: MultiVanTestBoards.Run) -> [String] {
            run.events.compactMap { if case let .held(vanID, _, _) = $0 { vanID } else { nil } }
        }
        XCTAssertEqual(held(try XCTUnwrap(withLight["blue_short"])), ["red"])
        XCTAssertEqual(held(try XCTUnwrap(otherPhase["blue_short"])), ["blue"])
        XCTAssertEqual(held(try XCTUnwrap(otherPhase["blue_bypass"])), [])
    }

    func testAHeldVanStopsOnItsLineGainsNoDistanceAndLeavesOnGreen() throws {
        let level = try Boards.experiment("experiment_signal_a")
        let signal = try light(level)
        let engine = try Boards.engine(level, selections: ["blue_fork": "blue_short"])
        let redLine = try XCTUnwrap(signal.approaches.first { $0.edgeID == "red_approach" }).stopDistance
        // While planning the boards show the schedule's first step: Blue's road is open.
        XCTAssertEqual(engine.signalStates, [MultiVanSignalState(signalID: signal.id, openGroup: 0, isOccupied: false)])

        engine.go()
        var events = engine.drainEvents()
        var heldSteps = 0
        var occupiedWhileHeld = false
        while engine.phase == .run, engine.tick < 346 {
            engine.advance(by: engine.tuning.stepDuration)
            events += engine.drainEvents()
            let red = engine.vans[0]
            if red.isHeld {
                heldSteps += 1
                XCTAssertEqual(red.status, .driving, "a held van is still on the road")
                XCTAssertEqual(red.distanceAlongEdge, redLine, "it never creeps past its line")
                XCTAssertEqual(red.position.x, 1, accuracy: 1e-9)
                XCTAssertEqual(red.position.y, redLine, accuracy: 1e-9)
            }
            occupiedWhileHeld = occupiedWhileHeld || (red.isHeld && engine.signalStates[0].isOccupied)
        }
        // Red reaches its line after 2.3 units and waits there until its green.
        let arrival = redLine / (engine.tuning.vanSpeed * engine.tuning.stepDuration)
        let heldTicks = events.compactMap { event -> Int? in
            if case let .held(vanID, signalID, tick) = event, vanID == "red", signalID == signal.id { tick } else { nil }
        }
        XCTAssertEqual(heldTicks.count, 1)
        XCTAssertEqual(Double(try XCTUnwrap(heldTicks.first)), arrival, accuracy: 1.5)
        XCTAssertGreaterThan(heldSteps, 150)
        XCTAssertTrue(occupiedWhileHeld, "Blue crossed while Red waited")
        XCTAssertTrue(engine.vans[0].isHeld)
        XCTAssertEqual(engine.signalStates[0].openGroup, 1)

        // On green Red pulls away from the line: the wait bought no distance.
        engine.advance(by: engine.tuning.stepDuration)
        events += engine.drainEvents()
        XCTAssertTrue(events.contains(.released(vanID: "red", signalID: signal.id, tick: 347)))
        XCTAssertFalse(engine.vans[0].isHeld)
        XCTAssertEqual(engine.vans[0].distanceAlongEdge, redLine + engine.tuning.vanSpeed * engine.tuning.stepDuration, accuracy: 1e-9)
        while engine.phase == .run { engine.advance(by: 0.1) }
        XCTAssertEqual(engine.outcome, .win)
        events += engine.drainEvents()
        XCTAssertEqual(events.filter { if case .held = $0 { true } else { false } }.count, 1, "held is reported once, not every step")
    }

    func testAVanLetInFinishesClearingAndBlocksTheNextGreenUntilItHas() throws {
        // The green ends the step Blue crosses its line: Blue carries on, and
        // Red's green is refused until Blue has left the square.
        var json = try Boards.json("experiment_signal_a")
        var signal = try XCTUnwrap((json["signals"] as? [[String: Any]])?.first)
        signal["phases"] = [["group": 0, "ticks": 188], ["group": 1, "ticks": 500]]
        json["signals"] = [signal]
        let level = try Boards.level(json)
        let engine = try Boards.engine(level, selections: ["blue_fork": "blue_short"])
        engine.go()
        var refusedGreens = 0
        while engine.phase == .run {
            engine.advance(by: engine.tuning.stepDuration)
            guard engine.phase == .run else { break }
            let state = engine.signalStates[0]
            let nominal = try light(level).nominalGroup(atTick: engine.tick)
            if nominal == 1, state.openGroup == nil {
                refusedGreens += 1
                XCTAssertTrue(state.isOccupied)
                XCTAssertTrue(engine.vans[0].isHeld, "Red stays on its line while Blue is still inside")
                XCTAssertEqual(engine.vans[1].status, .driving, "Blue was let in and keeps going")
            }
        }
        XCTAssertEqual(engine.outcome, .win)
        XCTAssertGreaterThan(refusedGreens, 20, "the boards show the light as closed, not a green that lets no one in")
    }

    func testHeldVansCanBeHitAndLockNearbySwitches() throws {
        // Blue follows Red up to a light that never opens: a queue is a crash.
        let level = try Boards.board(
            nodes: [("rs", 0, 0), ("rh", 0, 4), ("bs", 0, 1), ("sh", 2, 2)],
            edges: [("road", "rs", "rh"), ("blue_in", "bs", "rh")],
            vans: [["id": "red", "color": "red", "startNodeID": "bs"], ["id": "blue", "color": "blue", "startNodeID": "rs", "departDelay": 1]],
            houses: [("rh", "red"), ("sh", "blue")],
            extra: ["schemaVersion": 3, "signals": [[
                "id": "light", "approaches": [["edgeID": "blue_in", "stopDistance": 1.5, "group": 0]],
                "phases": [["ticks": 100_000], ["group": 0, "ticks": 1]],
                "area": ["x": 0, "y": 3, "radius": 0.45],
            ]]]
        )
        let run = Boards.run(try MultiVanEngine(level: level), seconds: 20)
        guard case let .failCrash(vanIDs, point) = run.engine.outcome else { return XCTFail("\(String(describing: run.engine.outcome))") }
        XCTAssertEqual(Set(vanIDs), ["red", "blue"])
        XCTAssertEqual(point.y, 2.5, accuracy: 0.3, "the moving van ran into the one held at its line")

        // A van held within a live switch's reach keeps that switch locked.
        let locked = try Boards.board(
            nodes: [("s", 0, 0), ("fork", 0, 2), ("a", 0, 5), ("b", 2, 5)],
            edges: [("in", "s", "fork"), ("up", "fork", "a"), ("over", "fork", "b")],
            vans: [["id": "red", "color": "red", "startNodeID": "s"]], houses: [("a", "red")],
            initial: ["fork": "up"], live: ["fork"],
            extra: ["schemaVersion": 3, "signals": [[
                "id": "light", "approaches": [["edgeID": "up", "stopDistance": 0.3, "group": 0]],
                "phases": [["ticks": 600], ["group": 0, "ticks": 600]],
                "area": ["x": 0, "y": 3, "radius": 0.5],
            ]]]
        )
        // Policy keeps stop lines off switches; the engine still locks correctly.
        XCTAssertTrue(MultiVanLevelRules.authoringIssues(in: locked).contains { $0.contains("too close to switch fork") })
        let engine = try MultiVanEngine(level: locked)
        engine.go()
        engine.advance(by: 3)
        XCTAssertTrue(engine.vans[0].isHeld)
        XCTAssertEqual(engine.lockedSwitchNodeIDs, ["fork"])
        XCTAssertEqual(engine.vansLocking(switchNodeID: "fork"), ["red"])
        XCTAssertEqual(engine.tapSwitch(nodeID: "fork"), .rejectedLocked)
    }

    func testStopAndRetryResetTheScheduleHeldVansAndOccupancy() throws {
        let level = try Boards.experiment("experiment_signal_a")
        let engine = try Boards.engine(level, selections: ["blue_fork": "blue_short"])
        let resting = engine.signalStates
        for finishes in [false, true] {
            engine.go()
            engine.advance(by: 1.9)
            XCTAssertTrue(engine.vans[0].isHeld)
            if finishes {
                while engine.phase == .run { engine.advance(by: 0.1) }
                engine.retry()
            } else {
                engine.stop()
            }
            XCTAssertEqual(engine.phase, .plan)
            XCTAssertEqual(engine.signalStates, resting)
            XCTAssertTrue(engine.vans.allSatisfy { !$0.isHeld && $0.status == .waiting })
            XCTAssertEqual(engine.tick, 0)
        }
        // The same run every time, whatever happened before it.
        _ = engine.drainEvents()
        let first = Boards.run(engine)
        engine.retry()
        let second = Boards.run(engine, frame: 1.0 / 43)
        XCTAssertEqual(first.events, second.events)
        XCTAssertEqual(first.engine.runTime, second.engine.runTime)
    }

    func testSignalRunsMatchAcrossFramePartitionsAndAPause() throws {
        for id in ["experiment_signal_a", "experiment_signal_b", "experiment_drawbridge_a"] {
            let level = try Boards.experiment(id)
            for configuration in Boards.configurations(of: level) {
                let reference = Boards.run(try Boards.engine(level, selections: configuration))
                for frame in [1.0 / 60, 1.0 / 30, 0.019, 0.25] {
                    let run = Boards.run(try Boards.engine(level, selections: configuration), frame: frame)
                    XCTAssertEqual(run.engine.outcome, reference.engine.outcome, "\(id) \(configuration) \(frame)")
                    XCTAssertEqual(run.events, reference.events, "\(id) \(configuration) \(frame)")
                }
                // A pause stops the signal's clock with everything else.
                let paused = try Boards.engine(level, selections: configuration)
                paused.go()
                paused.advance(by: 1.7)
                paused.pause()
                paused.advance(by: 30)
                paused.resume()
                while paused.phase == .run { paused.advance(by: paused.tuning.stepDuration) }
                XCTAssertEqual(paused.outcome, reference.engine.outcome, "\(id) \(configuration)")
                XCTAssertEqual(paused.runTime, reference.engine.runTime, accuracy: 1e-9, "\(id) \(configuration)")
            }
        }
    }

    func testPreviewNamesTheWaitWithoutPromisingItsLength() throws {
        let level = try Boards.experiment("experiment_signal_a")
        let engine = try Boards.engine(level, selections: ["blue_fork": "blue_short"])
        XCTAssertEqual(engine.previewRoutes.map(\.signalIDs), [["square_light"], ["square_light"]])
        XCTAssertEqual(MultiVanRoutePreview.summary(for: level.vans[1], route: engine.previewRoutes[1], level: level),
                       "Blue van reaches its house. It waits at a signal on the way.")
        engine.resetSwitches()
        XCTAssertEqual(engine.previewRoutes.map(\.signalIDs), [["square_light"], []])
        // Both boards read the lamps from the same engine state.
        let frame = MultiVanDioramaFrame(engine: engine, systemReduceMotion: false, reducesExtraAnimations: false)
        XCTAssertEqual(frame.signalApproaches, MultiVanSignalApproach.approaches(engine: engine))
        XCTAssertEqual(frame.signalApproaches.map(\.isOpen), [true, false])
        XCTAssertEqual(frame.signalApproaches[0].stopPoint.x, 1.7, accuracy: 1e-9)
        XCTAssertEqual(frame.signalApproaches[0].stopPoint.y, 3, accuracy: 1e-9)
        XCTAssertEqual(frame.signalApproaches[1].stopPoint.y, 2.3, accuracy: 1e-9)
        XCTAssertEqual(MultiVanSignalLampView.accessibilityValue(kind: .trafficLight, isOpen: false), "Stop. Vans on this road wait at the line")
        XCTAssertEqual(MultiVanAnnouncer.announcement(for: .held(vanID: "red", signalID: "square_light", tick: 3), level: level),
                       "Red van is waiting at the light.")
    }

    // MARK: - Drawbridge

    func testTheDrawbridgeIsOneGroupOnTheSameScheduleAndFlipsItsControl() throws {
        let level = try Boards.experiment("experiment_drawbridge_a")
        let bridge = try light(level)
        XCTAssertEqual(bridge.kind, .drawbridge)
        XCTAssertEqual(Set(bridge.approaches.map(\.group)), [0])
        XCTAssertEqual(level.biome, .harbor)
        XCTAssertNil(bridge.nominalGroup(atTick: 0), "the bridge starts up")
        XCTAssertEqual(bridge.nominalGroup(atTick: 220), 0)

        let withBridge = try outcomes(level.id)
        let noBridge = try outcomes("experiment_drawbridge_c")
        XCTAssertEqual(withBridge.mapValues { Boards.name($0.engine.outcome) }, ["blue_short": "win", "blue_long": "crash"])
        XCTAssertEqual(noBridge.mapValues { Boards.name($0.engine.outcome) }, ["blue_short": "crash", "blue_long": "win"])
        XCTAssertGreaterThan(try XCTUnwrap(withBridge["blue_short"]).closestApproach, 1.0)
        XCTAssertGreaterThan(try XCTUnwrap(noBridge["blue_long"]).closestApproach, 1.0)

        // Red waits at the raised bridge and crosses once it is down.
        let events = try XCTUnwrap(withBridge["blue_short"]).events
        let held = events.compactMap { if case let .held(vanID, _, tick) = $0 { "\(vanID)@\(tick)" } else { nil } }
        let released = events.compactMap { if case let .released(vanID, _, tick) = $0 { "\(vanID)@\(tick)" } else { nil } }
        XCTAssertTrue(["red@72", "red@73"].contains(held.first ?? ""), "\(held)")
        XCTAssertEqual(held.count, 1)
        XCTAssertEqual(released, ["red@221"])
        XCTAssertEqual(MultiVanAnnouncer.announcement(for: .held(vanID: "red", signalID: bridge.id, tick: 72), level: level),
                       "Red van is waiting at the bridge.")
        XCTAssertEqual(MultiVanSignalLampView.accessibilityValue(kind: .drawbridge, isOpen: false), "Bridge up. Vans wait at the line")
        XCTAssertEqual(MultiVanExperimentKind.kind(of: level), .signal)
    }

    // MARK: - Ice

    private func tapOutcome(_ level: MultiVanLevel, fork: String, atTick tick: Int) throws -> (MultiVanTapResult, MultiVanEngine.Outcome?) {
        let engine = try Boards.engine(level, selections: ["blue_fork": fork])
        engine.go()
        for _ in 0..<tick { engine.advance(by: engine.tuning.stepDuration) }
        guard engine.phase == .run else { return (.rejectedFrozen, engine.outcome) }
        let result = engine.tapSwitch(nodeID: "split")
        while engine.phase == .run { engine.advance(by: 0.05) }
        return (result, engine.outcome)
    }

    func testIceLocksTheSwitchForTheWholeRoadSoOnlyTheLongWayLeavesAGap() throws {
        let icy = try Boards.experiment("experiment_ice_a")
        let clear = try Boards.experiment("experiment_ice_c")
        XCTAssertEqual(icy.roadZones.map(\.edgeIDs), [["stem"]])
        XCTAssertEqual(clear.graph.edges.map(\.id), icy.graph.edges.map(\.id))
        XCTAssertTrue(clear.roadZones.isEmpty)

        func window(_ level: MultiVanLevel, fork: String) throws -> [Int] {
            try stride(from: 0, through: 840, by: 4).filter { tick in
                let (result, outcome) = try tapOutcome(level, fork: fork, atTick: tick)
                return result == .accepted && outcome == .win
            }
        }
        // On ice the short way has no legal moment at all: Blue is on the ice
        // before Red has cleared the switch.
        XCTAssertEqual(try window(icy, fork: "blue_short"), [])
        // The long way opens one unbroken gap of over two seconds.
        let long = try window(icy, fork: "blue_long")
        XCTAssertEqual(long, Array(stride(from: try XCTUnwrap(long.first), through: try XCTUnwrap(long.last), by: 4)))
        XCTAssertGreaterThan(Double(try XCTUnwrap(long.last) - long[0]) / 120, 2.0)
        // Without ice the short way works, in a much tighter gap; the long way is wider still.
        let clearShort = try window(clear, fork: "blue_short")
        XCTAssertFalse(clearShort.isEmpty)
        XCTAssertLessThan(Double(try XCTUnwrap(clearShort.last) - clearShort[0]) / 120, 1.0)
        XCTAssertGreaterThan(try window(clear, fork: "blue_long").count, long.count)
        // No static plan wins either board: the switch has to change mid-run.
        for level in [icy, clear] {
            for configuration in Boards.configurations(of: level) {
                XCTAssertNotEqual(Boards.run(try Boards.engine(level, selections: configuration), seconds: 30).engine.outcome, .win)
            }
        }
    }

    func testIceLockStartsWhenAVanDrivesOnAndIsExplainedWhilePaused() throws {
        let level = try Boards.experiment("experiment_ice_a")
        let engine = try Boards.engine(level, selections: ["blue_fork": "blue_long"])
        engine.go()
        // Red is still on its approach: the switch two units ahead is free.
        engine.advance(by: 1.0)
        XCTAssertEqual(engine.vans[0].currentEdgeID, "red_approach")
        XCTAssertEqual(engine.lockedSwitchNodeIDs, ["blue_fork"], "only the ordinary fork is frozen")
        // The moment Red is on the ice, the far switch locks, well outside the usual reach.
        engine.advance(by: 0.5)
        XCTAssertEqual(engine.vans[0].currentEdgeID, "stem")
        XCTAssertGreaterThan(hypot(engine.vans[0].position.x - 2, engine.vans[0].position.y - 4), 1.5)
        XCTAssertTrue(engine.lockedSwitchNodeIDs.contains("split"))
        XCTAssertEqual(engine.vansLocking(switchNodeID: "split"), ["red"])
        engine.pause()
        XCTAssertEqual(engine.tapSwitch(nodeID: "split"), .rejectedLocked)
        XCTAssertEqual(MultiVanPauseCopy.note(forRejectedTapAt: "split", engine: engine),
                       "Red is on the ice and cannot be re-routed. Resume, let it pass, then pause again.")
        XCTAssertEqual(MultiVanPauseCopy.note(forRejectedTapAt: "blue_fork", engine: engine),
                       "That switch only changes while planning. Stop to plan again.")
        // Once Red is off the ice and clear, the paused player can make the change.
        engine.resume()
        engine.advance(by: 1.6)
        engine.pause()
        XCTAssertEqual(engine.vansLocking(switchNodeID: "split"), [])
        XCTAssertEqual(engine.tapSwitch(nodeID: "split"), .accepted)
        engine.resume()
        while engine.phase == .run { engine.advance(by: 0.05) }
        XCTAssertEqual(engine.outcome, .win)
        XCTAssertEqual(MultiVanStars.rating(changes: engine.changeCount, par: level.parChanges), 3, "pausing costs no stars")
    }
}
