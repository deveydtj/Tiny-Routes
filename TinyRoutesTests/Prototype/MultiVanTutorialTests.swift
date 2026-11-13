import XCTest
@testable import TinyRoutes

final class MultiVanTutorialTests: XCTestCase {
    private var defaults: UserDefaults!
    private var suiteName: String!

    override func setUp() {
        super.setUp()
        suiteName = "MultiVanTutorialTests.\(UUID().uuidString)"
        defaults = UserDefaults(suiteName: suiteName)
    }

    override func tearDown() {
        defaults.removePersistentDomain(forName: suiteName)
        defaults = nil
        super.tearDown()
    }

    private var progress: MultiVanTutorialProgress { MultiVanTutorialProgress(defaults: defaults) }

    private func level(_ id: String) throws -> MultiVanLevel {
        let levels = try MultiVanLevelRepository(bundle: Bundle(for: MultiVanEngine.self)).loadAllLevels()
        return try XCTUnwrap(levels.first { $0.id == id }, "\(id) is missing")
    }

    private func decode(_ tutorial: String) throws -> MultiVanLevel {
        let json = """
        {
          "id": "level_tip", "name": "Tip",
          "graph": {
            "nodes": [
              { "id": "start", "x": 0, "y": 0, "outgoingEdgeIDs": ["road"] },
              { "id": "house", "x": 0, "y": 2, "outgoingEdgeIDs": [] }
            ],
            "edges": [{ "id": "road", "fromNodeID": "start", "toNodeID": "house", "roadShape": "verticalFirst" }]
          },
          "vans": [{ "id": "red", "color": "red", "startNodeID": "start" }],
          "houses": [{ "nodeID": "house", "color": "red" }],
          "initialSwitchEdges": {}, "parChanges": 0\(tutorial)
        }
        """
        return try JSONDecoder().decode(MultiVanLevel.self, from: Data(json.utf8))
    }

    func testTutorialIsOptionalAndFocusDefaultsToNothing() throws {
        XCTAssertEqual(try decode("").tutorial, [])
        let level = try decode(#", "tutorial": [{ "trigger": "crash", "title": "T", "body": "B" }]"#)
        XCTAssertEqual(level.tutorial, [MultiVanTutorialTip(trigger: .crash, title: "T", body: "B")])
        XCTAssertNil(level.tutorialTip(for: .start))
        XCTAssertThrowsError(try decode(#", "tutorial": [{ "trigger": "later", "title": "T", "body": "B" }]"#))
    }

    func testEachNewMechanicHasATipAndMergeKeepsItsCrashASurprise() throws {
        // Go, switches, Stop, three-way cycling, matching, live switches, holding.
        for id in ["level_001", "level_002", "level_003", "level_004", "level_005", "level_006", "level_009"] {
            XCTAssertNotNil(try level(id).tutorialTip(for: .start), "\(id) introduces a mechanic")
        }
        let merge = try level("level_008")
        XCTAssertEqual(merge.name, "Merge")
        XCTAssertNil(merge.tutorialTip(for: .start), "Merge must let the first crash happen untold")
        XCTAssertNotNil(merge.tutorialTip(for: .crash))
        // Later levels reuse what the tips taught; they rely on their hints.
        for id in ["level_007", "level_010", "level_011", "level_012", "level_013", "level_014"] {
            XCTAssertTrue(try level(id).tutorial.isEmpty, id)
            XCTAssertNotNil(try level(id).hint, id)
        }
    }

    func testRoutePracticeUsesRealSwitchesAndReopensAfterCompletion() throws {
        let level = try level("level_004")
        let engine = try MultiVanEngine(level: level)
        let tutorial = MultiVanTutorialPresentation()
        tutorial.begin(level: level, progress: progress)
        XCTAssertEqual(tutorial.cue(engine: engine)?.target, .switches)

        for expected in [MultiVanTutorialPresentation.Cue.Target.switches, .go] {
            let before = try XCTUnwrap(engine.runtimeGraph.nodesByID["switch"])
            let control = try XCTUnwrap(MultiVanSwitchControl(node: before, engine: engine, graph: engine.runtimeGraph))
            XCTAssertEqual(engine.tapSwitch(nodeID: "switch"), .accepted)
            let after = try XCTUnwrap(engine.runtimeGraph.nodesByID["switch"])
            let selected = try XCTUnwrap(MultiVanSwitchControl(node: after, engine: engine, graph: engine.runtimeGraph))
            XCTAssertEqual(control.nextAngle, selected.activeAngle)
            XCTAssertEqual(tutorial.cue(engine: engine)?.target, expected)
        }
        XCTAssertFalse(progress.hasSeen(.start, levelID: level.id))

        tutorial.go(engine: engine, progress: progress)
        engine.go()
        XCTAssertNil(tutorial.cue(engine: engine))
        engine.advance(by: 20)
        XCTAssertEqual(engine.outcome, .win)
        tutorial.complete(level: level, progress: progress)
        tutorial.begin(level: level, progress: progress)
        XCTAssertNil(tutorial.activeTip)
        tutorial.reopen(level: level)
        XCTAssertNotNil(tutorial.activeTip)
    }

    func testStopPracticePointsBackToTheSwitchesAfterStopping() throws {
        let level = try level("level_003")
        let engine = try MultiVanEngine(level: level)
        let tutorial = MultiVanTutorialPresentation()
        tutorial.begin(level: level, progress: progress)
        XCTAssertEqual(tutorial.cue(engine: engine)?.target, .go)
        tutorial.go(engine: engine, progress: progress)
        engine.go()
        XCTAssertEqual(tutorial.cue(engine: engine)?.target, .watch)
        engine.advance(by: 2)
        tutorial.observeRun(engine: engine)
        XCTAssertEqual(tutorial.cue(engine: engine)?.target, .stop)

        engine.stop()
        tutorial.stopped()
        let cue = tutorial.cue(engine: engine)
        XCTAssertEqual(cue?.target, .switches)
        XCTAssertEqual(tutorial.spotlightNodeIDs(engine: engine, cue: cue), ["loop_switch", "house_switch"])
    }

    func testLivePracticeWaitsForTheTurnAndAnUnlockedSwitch() throws {
        for (id, nodeID, before, after) in [
            ("level_006", "switch", 1.4, 1.1),
            ("level_009", "loop_switch", 3.0, 2.0)
        ] {
            let level = try level(id)
            let engine = try MultiVanEngine(level: level)
            let tutorial = MultiVanTutorialPresentation()
            tutorial.begin(level: level, progress: progress)
            XCTAssertEqual(tutorial.cue(engine: engine)?.target, .go)
            tutorial.go(engine: engine, progress: progress)
            engine.go()
            engine.advance(by: before)
            tutorial.observeRun(engine: engine)
            XCTAssertEqual(tutorial.cue(engine: engine)?.target, .watch, id)

            engine.advance(by: after)
            tutorial.observeRun(engine: engine)
            let cue = tutorial.cue(engine: engine)
            XCTAssertEqual(cue?.target, .switches, id)
            XCTAssertEqual(tutorial.spotlightNodeIDs(engine: engine, cue: cue), [nodeID], id)

            XCTAssertEqual(engine.tapSwitch(nodeID: nodeID), .accepted, id)
            XCTAssertEqual(tutorial.cue(engine: engine)?.text, "Watch the vans head home.", id)
        }
    }

    func testFirstCrashExplainsTimingThenRepeatedFailuresOfferTheHint() throws {
        let level = try level("level_008")
        let tutorial = MultiVanTutorialPresentation()
        tutorial.begin(level: level, progress: progress)
        XCTAssertNil(tutorial.activeTip)
        let crash = MultiVanEngine.Outcome.failCrash(vanIDs: ["red", "blue"], point: RoadPoint(x: 2, y: 4))

        tutorial.failed(crash, level: level, progress: progress)
        XCTAssertEqual(tutorial.failureTip, level.tutorialTip(for: .crash))
        XCTAssertNil(tutorial.failureHint)
        XCTAssertTrue(progress.hasSeen(.crash, levelID: level.id))
        tutorial.retried()
        XCTAssertNil(tutorial.failureTip)

        tutorial.failed(crash, level: level, progress: progress)
        XCTAssertNil(tutorial.failureTip, "The crash tip shows once")
        XCTAssertEqual(tutorial.failureHint, level.hint)
        XCTAssertEqual(tutorial.failureCount, 2)

        tutorial.go(engine: try MultiVanEngine(level: level), progress: progress)
        XCTAssertNil(tutorial.failureHint)
        tutorial.begin(level: level, progress: progress)
        XCTAssertEqual(tutorial.failureCount, 0, "Each visit to a level starts counting again")
        tutorial.failed(crash, level: level, progress: progress)
        XCTAssertNil(tutorial.failureTip)
        XCTAssertNil(tutorial.failureHint, "One failure isn't enough for a hint")
    }

    func testOtherFailuresDoNotUseTheCrashTip() throws {
        let level = try level("level_008")
        let tutorial = MultiVanTutorialPresentation()
        tutorial.failed(.failWrongHouse(vanID: "red", houseNodeID: "blue_house"), level: level, progress: progress)
        XCTAssertNil(tutorial.failureTip)
        XCTAssertFalse(progress.hasSeen(.crash, levelID: level.id))
    }

    func testTwoFailuresBringBackACompletedEarlyTutorial() throws {
        let level = try level("level_002")
        let engine = try MultiVanEngine(level: level)
        let tutorial = MultiVanTutorialPresentation()
        progress.markSeen(.start, levelID: level.id)
        tutorial.begin(level: level, progress: progress)
        XCTAssertNil(tutorial.cue(engine: engine))

        for attempt in 1...2 {
            engine.go()
            engine.advance(by: 20)
            let outcome = try XCTUnwrap(engine.outcome)
            tutorial.failed(outcome, level: level, progress: progress)
            XCTAssertEqual(tutorial.isReminding, attempt == 2)
            XCTAssertEqual(tutorial.failureHint != nil, attempt == 2)
            tutorial.retried()
            engine.retry()
        }

        let cue = tutorial.cue(engine: engine)
        XCTAssertEqual(cue?.target, .switches)
        XCTAssertEqual(tutorial.spotlightNodeIDs(engine: engine, cue: cue), ["switch"])
    }

    func testTimedReminderRequiresMissesAndOnlyAppearsOncePerVisit() throws {
        let level = try level("level_004")
        let engine = try MultiVanEngine(level: level)
        let tutorial = MultiVanTutorialPresentation()
        progress.markSeen(.start, levelID: level.id)
        tutorial.begin(level: level, progress: progress)
        for _ in 0..<3 { tutorial.missedTap(engine: engine) }
        XCTAssertNil(tutorial.cue(engine: engine), "Taps alone don't trigger a reminder")

        tutorial.usedControl()
        for _ in 0..<20 { tutorial.playedSecond(engine: engine) }
        XCTAssertNil(tutorial.cue(engine: engine), "A successful control clears earlier misses")
        for _ in 0..<2 { tutorial.missedTap(engine: engine) }
        XCTAssertNil(tutorial.cue(engine: engine))
        tutorial.missedTap(engine: engine)
        XCTAssertEqual(tutorial.cue(engine: engine)?.target, .switches)

        tutorial.complete(level: level, progress: progress)
        for _ in 0..<3 { tutorial.missedTap(engine: engine) }
        XCTAssertNil(tutorial.cue(engine: engine), "Dismissing the reminder keeps it closed")
    }

    func testProgressIsPerLevelAndTriggerAndResets() {
        let progress = progress
        progress.markSeen(.start, levelID: "level_002")
        XCTAssertTrue(progress.hasSeen(.start, levelID: "level_002"))
        XCTAssertFalse(progress.hasSeen(.crash, levelID: "level_002"))
        XCTAssertFalse(progress.hasSeen(.start, levelID: "level_004"))
        progress.markSeen(.start, levelID: "level_002")
        XCTAssertEqual(defaults.stringArray(forKey: MultiVanTutorialProgress.storageKey), ["level_002:start"])
        progress.reset()
        XCTAssertFalse(progress.hasSeen(.start, levelID: "level_002"))
    }
}
