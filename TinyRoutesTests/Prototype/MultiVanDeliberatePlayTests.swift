import XCTest
@testable import TinyRoutes

/// Pause, inspect, change, resume: the run freezes without becoming planning,
/// and the help ladder gives one step at a time from the recorded solutions.
final class MultiVanDeliberatePlayTests: XCTestCase {
    private typealias Boards = MultiVanTestBoards

    /// The app's own copies of the recorded solutions: what help reads in play.
    private let solutions = MultiVanTestBoards.appBundle

    private func campaign(_ id: String) throws -> MultiVanLevel {
        try XCTUnwrap(MultiVanLevelRepository(bundle: Boards.appBundle).loadAllLevels().first { $0.id == id })
    }

    // MARK: - Pause

    func testPauseFreezesEveryClockAndResumeLosesNoTime() throws {
        let level = try campaign("level_011")
        let script = try PrototypeSolutionScript.load(levelID: level.id)
        let reference = try PrototypeSolutionRunner.verify(level: level, script: script)

        let engine = try MultiVanEngine(level: level)
        script.planTaps.forEach { engine.tapSwitch(nodeID: $0) }
        engine.pause()
        XCTAssertFalse(engine.isPaused, "nothing to pause while planning")
        engine.go()
        _ = engine.drainEvents()
        var pending = script.liveTaps.sorted { $0.atTime < $1.atTime }
        var pauses = 0
        while engine.phase == .run {
            // Pause every half second of simulation, and wait there "for a minute".
            if engine.tick > 0, engine.tick % 60 == 0, !engine.isPaused {
                let before = (engine.tick, engine.runTime, engine.vans.map(\.position), engine.lockedSwitchNodeIDs)
                engine.pause()
                XCTAssertTrue(engine.isPaused)
                engine.advance(by: 60)
                XCTAssertEqual(engine.tick, before.0)
                XCTAssertEqual(engine.runTime, before.1)
                XCTAssertEqual(engine.vans.map(\.position), before.2)
                XCTAssertEqual(engine.lockedSwitchNodeIDs, before.3, "pausing unlocks nothing")
                XCTAssertEqual(engine.phase, .run)
                // A due live change can be made while paused, like any other legal tap.
                if let tap = pending.first, tap.atTime <= engine.runTime {
                    XCTAssertEqual(engine.tapSwitch(nodeID: tap.nodeID), .accepted)
                    pending.removeFirst()
                }
                engine.resume()
                pauses += 1
                XCTAssertEqual(engine.drainEvents().filter { $0 == .paused(tick: before.0) || $0 == .resumed(tick: before.0) }.count, 2)
            }
            if let tap = pending.first, tap.atTime <= engine.runTime {
                XCTAssertEqual(engine.tapSwitch(nodeID: tap.nodeID), .accepted)
                pending.removeFirst()
            }
            engine.advance(by: engine.tuning.stepDuration)
        }
        XCTAssertGreaterThan(pauses, 5)
        XCTAssertEqual(engine.outcome, .win)
        XCTAssertEqual(engine.runTime, reference.runTime, accuracy: 1e-9)
        XCTAssertEqual(engine.vans.map(\.position), reference.vans.map(\.position))
        // Equal stars: a pause is not a route change.
        XCTAssertEqual(engine.changeCount, reference.changeCount)
        XCTAssertEqual(MultiVanStars.rating(changes: engine.changeCount, par: level.parChanges), 3)
    }

    func testPausedTapsFollowRunRulesAndStopOrAFinishEndThePause() throws {
        let level = try campaign("level_011")
        let engine = try MultiVanEngine(level: level)
        let ordinary = try XCTUnwrap(level.graph.nodes.first { $0.outgoingEdgeIDs.count > 1 && !level.liveSwitchNodeIDs.contains($0.id) }?.id)
        let live = try XCTUnwrap(level.liveSwitchNodeIDs.first)
        engine.go()
        engine.pause()
        _ = engine.drainEvents()
        // Paused is not planning: an ordinary switch stays frozen.
        XCTAssertEqual(engine.tapSwitch(nodeID: ordinary), .rejectedFrozen)
        XCTAssertEqual(engine.drainEvents(), [.tapRejected(nodeID: ordinary)])
        XCTAssertEqual(engine.tapSwitch(nodeID: live), .accepted, "no van is near the live switch yet")
        XCTAssertEqual(engine.tapSwitch(nodeID: live), .accepted)
        // Step on until a van locks the live switch, then pause on the lock.
        engine.resume()
        while engine.vansLocking(switchNodeID: live).isEmpty, engine.phase == .run { engine.advance(by: engine.tuning.stepDuration) }
        engine.pause()
        XCTAssertEqual(engine.tapSwitch(nodeID: live), .rejectedLocked)
        let blocker = try XCTUnwrap(engine.vansLocking(switchNodeID: live).first)
        let color = try XCTUnwrap(level.vans.first { $0.id == blocker }).color.displayName
        XCTAssertEqual(MultiVanPauseCopy.note(forRejectedTapAt: live, engine: engine),
                       "\(color) is too close to that switch. Resume, let it pass, then pause again.")

        // Stop is still its own action, and leaves nothing paused behind.
        engine.stop()
        XCTAssertEqual(engine.phase, .plan)
        XCTAssertFalse(engine.isPaused)
        engine.resume()
        XCTAssertFalse(engine.isPaused)
        // A run that finishes is no longer paused, and a finished run cannot be.
        engine.go()
        while engine.phase == .run { engine.advance(by: 0.1) }
        engine.pause()
        XCTAssertFalse(engine.isPaused)
        // Go after a pause starts clean.
        engine.retry()
        engine.go()
        engine.pause()
        engine.stop()
        engine.go()
        XCTAssertFalse(engine.isPaused)
        engine.advance(by: 0.5)
        XCTAssertEqual(engine.tick, 60)
    }

    func testFrameDriverTakesNoWallTimeAcrossAPauseAndComesBackAtNormalSpeed() throws {
        let engine = try MultiVanEngine(level: campaign("level_011"))
        let driver = MultiVanFrameDriver()
        let start = Date(timeIntervalSinceReferenceDate: 1_000)
        engine.go()
        driver.advance(at: start, engine: engine, isActive: true)
        driver.setFastForwarding(true, at: start.addingTimeInterval(0.1), engine: engine, isActive: true)
        XCTAssertTrue(driver.isFastForwarding)
        driver.advance(at: start.addingTimeInterval(0.2), engine: engine, isActive: true)
        let ticks = engine.tick
        XCTAssertEqual(ticks, 12 + 24, "0.1 s at 1×, then 0.1 s at 2×")

        engine.pause()
        // Frames keep arriving for a minute; none of that time reaches the engine.
        for second in 1...60 {
            driver.advance(at: start.addingTimeInterval(0.2 + Double(second)), engine: engine, isActive: true)
        }
        XCTAssertEqual(engine.tick, ticks)
        XCTAssertFalse(driver.isFastForwarding, "pausing drops fast-forward")

        engine.resume()
        // The first frame back only starts a new interval: no catch-up.
        driver.advance(at: start.addingTimeInterval(100), engine: engine, isActive: true)
        XCTAssertEqual(engine.tick, ticks)
        driver.advance(at: start.addingTimeInterval(100.1), engine: engine, isActive: true)
        XCTAssertEqual(engine.tick, ticks + 12, "and it runs at 1×")
    }

    func testPauseIsOfferedWhereSomethingCanChangeMidRun() throws {
        let screen = try String(contentsOf: URL(fileURLWithPath: #filePath).deletingLastPathComponent()
            .deletingLastPathComponent().deletingLastPathComponent()
            .appendingPathComponent("TinyRoutes/Prototype/MultiVanGameplayScreen.swift"), encoding: .utf8)
        XCTAssertTrue(screen.contains("!engine.level.liveSwitchNodeIDs.isEmpty || !engine.level.signals.isEmpty"))
        XCTAssertTrue(screen.contains("TimelineView(.animation(paused: engine.phase != .run || !isActive || engine.isPaused))"))
        for title in ["Pause", "Resume", "Show me one step"] { XCTAssertTrue(screen.contains("\"\(title)\""), title) }
        XCTAssertTrue(screen.contains("if tutorial.canOfferNudge, solution != nil"), "no step is offered without a recorded solution")
        XCTAssertEqual(MultiVanAnnouncer.announcement(for: .paused(tick: 3), level: try campaign("level_001")), "Paused.")
        XCTAssertEqual(MultiVanHaptic.feedback(for: .paused(tick: 3)), .selection)
        XCTAssertNil(MultiVanHaptic.feedback(for: .held(vanID: "a", signalID: "b", tick: 1)))
        XCTAssertNil(MultiVanSound.sound(for: .released(vanID: "a", signalID: "b", tick: 1)))
        XCTAssertEqual(MultiVanSound.sound(for: .pickedUp(vanID: "a", packageID: "b", tick: 1)), .click)
        XCTAssertEqual(MultiVanSound.sound(for: .missingPackage(vanID: "a", packageID: "b")), .nopeHorn)
    }

    // MARK: - Help ladder

    func testNudgesLeadToEveryRecordedSolutionOneStepAtATime() throws {
        let repository = MultiVanLevelRepository(bundle: Boards.appBundle)
        let levels = try repository.loadAllLevels() + repository.loadExperimentLevels()
        XCTAssertEqual(levels.count, 32)
        for level in levels {
            let solution = try XCTUnwrap(MultiVanSolution.load(levelID: level.id, bundle: solutions), "\(level.id): no recorded solution")
            let script = try PrototypeSolutionScript.load(levelID: level.id)
            // The app ships exactly what the tests prove.
            XCTAssertEqual(solution.planTaps, script.planTaps, level.id)
            XCTAssertEqual(solution.liveTaps.map(\.nodeID), script.liveTaps.map(\.nodeID), level.id)
            XCTAssertEqual(solution.liveTaps.map(\.atTime), script.liveTaps.map(\.atTime), level.id)

            // Follow the nudges from the authored settings.
            let engine = try MultiVanEngine(level: level)
            var steps = 0
            while true {
                let nudge = MultiVanAssistance.nudge(engine: engine, solution: solution)
                guard let nodeID = nudge.nodeID, let edgeID = nudge.edgeID else {
                    // Planning is done: the step left is the run's first tap, or Go.
                    if let first = solution.liveTaps.min(by: { $0.atTime < $1.atTime }) {
                        XCTAssertEqual(nudge.nodeID, first.nodeID, level.id)
                        XCTAssertTrue(nudge.text.contains("Press Go, then tap the glowing ⚡ switch"), nudge.text)
                    } else {
                        XCTAssertEqual(nudge.text, "Your switches match a working plan. Press Go.", level.id)
                    }
                    break
                }
                // One switch at a time, counted in taps.
                let node = try XCTUnwrap(engine.runtimeGraph.nodesByID[nodeID])
                var taps = 0
                while engine.runtimeGraph.nodesByID[nodeID]?.activeOutgoingEdgeID != edgeID {
                    XCTAssertEqual(engine.tapSwitch(nodeID: nodeID), .accepted)
                    taps += 1
                    XCTAssertLessThan(taps, node.outgoingEdgeIDs.count, level.id)
                }
                let times = taps == 1 ? "once" : taps == 2 ? "twice" : "\(taps) times"
                XCTAssertEqual(nudge.text, "Tap the glowing switch \(times).", level.id)
                steps += 1
                XCTAssertLessThanOrEqual(steps, 10, level.id)
            }
            XCTAssertEqual(steps, Set(script.planTaps).count, "\(level.id): one nudge per switch the plan changes")
            let planned = try MultiVanEngine(level: level)
            script.planTaps.forEach { planned.tapSwitch(nodeID: $0) }
            XCTAssertEqual(engine.changeCount, planned.changeCount, level.id)
            XCTAssertEqual(engine.runtimeGraph.nodesByID.mapValues(\.activeOutgoingEdgeID),
                           planned.runtimeGraph.nodesByID.mapValues(\.activeOutgoingEdgeID), level.id)
            // The nudged plan, with the script's live taps, is the proven win.
            engine.go()
            var pending = script.liveTaps.sorted { $0.atTime < $1.atTime }
            while engine.phase == .run {
                if let tap = pending.first, tap.atTime <= engine.runTime {
                    XCTAssertEqual(engine.tapSwitch(nodeID: tap.nodeID), .accepted, level.id)
                    pending.removeFirst()
                }
                engine.advance(by: engine.tuning.stepDuration)
            }
            XCTAssertEqual(engine.outcome, .win, level.id)
        }
        XCTAssertNil(MultiVanSolution.load(levelID: "level_999", bundle: solutions))
        // The app carries one solution per level and nothing else beside them.
        let bundled = solutions.urls(forResourcesWithExtension: "json", subdirectory: "PrototypeSolutions") ?? []
        XCTAssertEqual(Set(bundled.map(\.lastPathComponent)), Set(levels.map { "\($0.id).solution.json" }))
    }

    func testANudgeAlsoCorrectsASwitchThePlanShouldLeaveAlone() throws {
        let level = try Boards.experiment("experiment_pair_b")
        let solution = try XCTUnwrap(MultiVanSolution.load(levelID: level.id, bundle: solutions))
        XCTAssertEqual(MultiVanAssistance.plannedSelections(level: level, solution: solution),
                       ["fork": "to_east", "west_switch": "west_home", "east_switch": "east_to_west"])
        // The player has flipped a switch the solution never touches.
        let engine = try Boards.engine(level, selections: ["fork": "to_east", "east_switch": "east_to_west", "west_switch": "west_to_east"])
        let nudge = MultiVanAssistance.nudge(engine: engine, solution: solution)
        XCTAssertEqual(nudge.nodeID, "west_switch")
        XCTAssertEqual(nudge.edgeID, "west_home")
    }

    func testLadderGoesHintThenSpotlightThenOneStepAndNeverCostsStars() throws {
        // A later board: a hint, focus switches and no practice tip.
        let level = try Boards.experiment("experiment_pickup_b")
        let solution = MultiVanSolution.load(levelID: level.id, bundle: solutions)
        let suite = "MultiVanDeliberatePlayTests.\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suite))
        defer { defaults.removePersistentDomain(forName: suite) }
        let progress = MultiVanTutorialProgress(defaults: defaults)
        XCTAssertTrue(MultiVanTutorialPresentation.supportsReminders(level: level))
        XCTAssertFalse(MultiVanTutorialPresentation.remindsEarly(level: level))
        XCTAssertEqual(MultiVanTutorialPresentation.failuresBeforeReminder(level: level), 4)

        let engine = try MultiVanEngine(level: level)
        let tutorial = MultiVanTutorialPresentation()
        tutorial.begin(level: level, progress: progress)
        func fail() throws {
            Boards.run(engine)
            tutorial.failed(try XCTUnwrap(engine.outcome), level: level, progress: progress)
            tutorial.retried()
            engine.retry()
            tutorial.prepareNudge(engine: engine, solution: solution)
        }

        try fail()
        XCTAssertEqual(tutorial.highestStep, .none)
        XCTAssertFalse(tutorial.canOfferNudge)
        XCTAssertNil(tutorial.cue(engine: engine))

        // Step 1: the hint on the failure card.
        Boards.run(engine)
        tutorial.failed(try XCTUnwrap(engine.outcome), level: level, progress: progress)
        XCTAssertEqual(tutorial.failureHint, level.hint)
        XCTAssertTrue(tutorial.canOfferNudge)
        XCTAssertEqual(tutorial.highestStep, .hint)
        XCTAssertFalse(tutorial.isReminding)
        tutorial.retried()
        engine.retry()
        tutorial.prepareNudge(engine: engine, solution: solution)
        XCTAssertNil(tutorial.nudge, "no step until it is asked for or earned")
        XCTAssertEqual(tutorial.spotlightNodeIDs(engine: engine, cue: tutorial.cue(engine: engine)), [])

        // Step 2: the hint in the HUD and its switches ringed.
        try fail()
        XCTAssertFalse(tutorial.isReminding)
        try fail()
        XCTAssertTrue(tutorial.isReminding)
        XCTAssertEqual(tutorial.highestStep, .spotlight)
        XCTAssertEqual(tutorial.cue(engine: engine), .init(text: try XCTUnwrap(level.hint), target: .hint))
        XCTAssertEqual(tutorial.spotlightNodeIDs(engine: engine, cue: tutorial.cue(engine: engine)), ["red_fork", "blue_fork"])
        XCTAssertNil(tutorial.nudge)

        // Step 3: after six failures, one switch and what to do with it.
        try fail()
        XCTAssertNil(tutorial.nudge)
        try fail()
        XCTAssertEqual(tutorial.failureCount, 6)
        XCTAssertEqual(tutorial.highestStep, .nudge)
        XCTAssertEqual(tutorial.nudge, .init(nodeID: "red_fork", edgeID: "red_tour", text: "Tap the glowing switch once."))
        XCTAssertEqual(tutorial.cue(engine: engine), .init(text: "Tap the glowing switch once.", target: .hint))
        XCTAssertEqual(tutorial.spotlightNodeIDs(engine: engine, cue: tutorial.cue(engine: engine)), ["red_fork"])
        // Making the step ends the nudge: one step, not the whole answer.
        engine.tapSwitch(nodeID: "blue_fork")
        tutorial.switchChanged(engine: engine)
        XCTAssertNotNil(tutorial.nudge)
        engine.tapSwitch(nodeID: "red_fork")
        tutorial.switchChanged(engine: engine)
        XCTAssertNil(tutorial.nudge)
        XCTAssertEqual(tutorial.cue(engine: engine)?.target, .hint, "the hint is back, with its switches")

        // The nudged plan wins with full stars.
        XCTAssertEqual(Boards.run(engine).engine.outcome, .win)
        XCTAssertEqual(MultiVanStars.rating(changes: engine.changeCount, par: level.parChanges), 3)
        tutorial.reset()
        XCTAssertEqual(tutorial.highestStep, .none)
    }

    func testADeliberateAskGivesAStepEarlyAndNothingIsGuessedWithoutASolution() throws {
        let level = try campaign("level_012")
        let suite = "MultiVanDeliberatePlayTests.\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suite))
        defer { defaults.removePersistentDomain(forName: suite) }
        let progress = MultiVanTutorialProgress(defaults: defaults)
        let engine = try MultiVanEngine(level: level)
        let tutorial = MultiVanTutorialPresentation()
        tutorial.begin(level: level, progress: progress)
        // The teaching levels keep their early reminder; this later one does not.
        XCTAssertTrue(MultiVanTutorialPresentation.remindsEarly(level: try campaign("level_009")))
        XCTAssertFalse(MultiVanTutorialPresentation.remindsEarly(level: level))

        tutorial.requestNudge()
        tutorial.prepareNudge(engine: engine, solution: nil)
        XCTAssertNil(tutorial.nudge, "no solution, no step")
        tutorial.prepareNudge(engine: engine, solution: MultiVanSolution.load(levelID: level.id, bundle: solutions))
        let nudge = try XCTUnwrap(tutorial.nudge)
        XCTAssertEqual(nudge.nodeID, try PrototypeSolutionScript.load(levelID: level.id).planTaps.first)
        XCTAssertEqual(tutorial.highestStep, .nudge)
        // A nudge shows only while planning, and Go clears it.
        engine.go()
        XCTAssertNotEqual(tutorial.cue(engine: engine)?.text, nudge.text)
        engine.stop()
        tutorial.go(engine: engine, progress: progress)
        XCTAssertNil(tutorial.nudge)
    }
}
