import XCTest
import Observation
import os
import SwiftUI
@testable import TinyRoutes

final class MultiVanGameplayTests: XCTestCase {
    func testHapticMappingAndPreferenceSuppression() {
        let cases: [(MultiVanEvent, MultiVanHaptic)] = [
            (.switchTapped, .selection),
            (.tapRejected(nodeID: "switch"), .lightImpact),
            (.go, .mediumImpact),
            (.delivered(vanID: "red", comboIndex: 1), .success),
            (.allDelivered, .success),
            (.crashed(point: RoadPoint(x: 0, y: 0)), .error),
            (.wrongHouse(vanID: "red"), .warning)
        ]

        for (event, haptic) in cases {
            XCTAssertEqual(MultiVanHaptic.feedback(for: event), haptic)
            XCTAssertNil(MultiVanHaptic.feedback(for: event, hapticsEnabled: false))
        }
        XCTAssertEqual(MultiVanHaptic.feedback(for: .go, hapticsEnabled: true), .mediumImpact)
    }

    private func engine(_ id: String = "proto_01") throws -> MultiVanEngine {
        let url = URL(fileURLWithPath: #filePath)
            .deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent()
            .appendingPathComponent("TinyRoutes/Resources/PrototypeLevels/\(id).json")
        return try MultiVanEngine(level: JSONDecoder().decode(MultiVanLevel.self, from: Data(contentsOf: url)))
    }

    private func frame(_ driver: MultiVanFrameDriver, _ engine: MultiVanEngine, _ seconds: Double, active: Bool = true) {
        driver.advance(at: Date(timeIntervalSinceReferenceDate: seconds), engine: engine, isActive: active)
    }

    func testFramesAdvanceOnlyWhileRunningAndIgnoreDuplicateOrOlderDates() throws {
        let engine = try engine()
        let driver = MultiVanFrameDriver()
        frame(driver, engine, 0)
        frame(driver, engine, 1)
        XCTAssertEqual(engine.runTime, 0)
        engine.go()
        XCTAssertEqual(engine.phase, .run)
        frame(driver, engine, 2)
        XCTAssertEqual(engine.runTime, 0)
        let start = engine.vans[0].position
        frame(driver, engine, 2.125)
        XCTAssertEqual(engine.runTime, 0.125, accuracy: 1e-9)
        XCTAssertFalse(engine.vans[0].position == start)
        let position = engine.vans[0].position
        frame(driver, engine, 2.125)
        frame(driver, engine, 2)
        XCTAssertEqual(engine.vans[0].position, position)
        frame(driver, engine, 2.25)
        XCTAssertEqual(engine.runTime, 0.25, accuracy: 1e-9)
        engine.stop()
        frame(driver, engine, 3)
        XCTAssertEqual(engine.phase, .plan)
        XCTAssertEqual(engine.runTime, 0)
        XCTAssertEqual(engine.vans[0].position, start)
    }

    func testInterruptionPreservesPositionAndDiscardsBackgroundTime() throws {
        let engine = try engine()
        let driver = MultiVanFrameDriver()
        engine.go()
        frame(driver, engine, 0)
        frame(driver, engine, 0.125)
        let position = engine.vans[0].position
        frame(driver, engine, 100, active: false)
        XCTAssertEqual(engine.vans[0].position, position)
        XCTAssertEqual(engine.phase, .run)
        frame(driver, engine, 200)
        XCTAssertEqual(engine.vans[0].position, position)
        frame(driver, engine, 200.125)
        XCTAssertEqual(engine.runTime, 0.25, accuracy: 1e-9)

        // Scene/disappearance callbacks also reset when no inactive tick arrives.
        driver.reset()
        frame(driver, engine, 400)
        XCTAssertEqual(engine.runTime, 0.25, accuracy: 1e-9)
        frame(driver, engine, 400.125)
        XCTAssertEqual(engine.runTime, 0.375, accuracy: 1e-9)
    }

    func testLongUIStallIsCappedAndNewRunStartsWithFreshTimestamp() throws {
        let engine = try engine()
        let driver = MultiVanFrameDriver()
        engine.go()
        frame(driver, engine, 0)
        frame(driver, engine, 100)
        XCTAssertEqual(engine.runTime, 0.25, accuracy: 1e-9)
        frame(driver, engine, 100.125)
        XCTAssertEqual(engine.runTime, 0.375, accuracy: 1e-9)
        engine.stop()
        driver.reset()
        engine.go()
        frame(driver, engine, 200)
        XCTAssertEqual(engine.runTime, 0)
        frame(driver, engine, 200.125)
        XCTAssertEqual(engine.runTime, 0.125, accuracy: 1e-9)
    }

    func testMV38HoldReleaseScalesOnlyCappedWallTimeAndPreservesFractionalSteps() throws {
        let engine = try engine()
        let driver = MultiVanFrameDriver()
        XCTAssertEqual(engine.tuning.stepDuration, 1.0 / 120)
        XCTAssertEqual(engine.tuning.fastForwardMultiplier, 2)
        XCTAssertFalse(driver.isFastForwarding)
        engine.go()
        frame(driver, engine, 0)
        // Input between frames settles the preceding interval at the old speed.
        driver.setFastForwarding(true, at: Date(timeIntervalSinceReferenceDate: 0.004), engine: engine, isActive: true)
        XCTAssertEqual(engine.runTime, 0)
        frame(driver, engine, 0.006)
        XCTAssertEqual(engine.runTime, 0)
        driver.setFastForwarding(false, at: Date(timeIntervalSinceReferenceDate: 0.007), engine: engine, isActive: true)
        XCTAssertEqual(engine.runTime, engine.tuning.stepDuration)
        frame(driver, engine, 0.022)
        XCTAssertEqual(engine.runTime, 3 * engine.tuning.stepDuration)
        XCTAssertFalse(driver.isFastForwarding)
        XCTAssertEqual(driver.fastForwardUseCount, 1)
        driver.setFastForwarding(true, at: Date(timeIntervalSinceReferenceDate: 0.022), engine: engine, isActive: true)
        frame(driver, engine, 100)
        XCTAssertEqual(engine.runTime, 0.525, accuracy: 1e-12)
        driver.reset()
        XCTAssertFalse(driver.isFastForwarding)
        XCTAssertEqual(driver.fastForwardUseCount, 2)
        driver.reset(clearUsage: true)
        XCTAssertEqual(driver.fastForwardUseCount, 0)
    }

    func testMV38StopRetryReplayAndInterruptionRestoreNormalSpeed() throws {
        for id in ["proto_01", "proto_02"] {
            let engine = try engine(id)
            let driver = MultiVanFrameDriver()
            engine.go()
            frame(driver, engine, 0)
            driver.setFastForwarding(true, at: Date(timeIntervalSinceReferenceDate: 0), engine: engine, isActive: true)
            frame(driver, engine, 0.125)
            XCTAssertEqual(engine.runTime, 0.25)
            engine.stop()
            driver.reset() // Same synchronous reset as the Stop action.
            XCTAssertFalse(driver.isFastForwarding)
            engine.go()
            frame(driver, engine, 1)
            frame(driver, engine, 1.125)
            XCTAssertEqual(engine.runTime, 0.125)
            driver.setFastForwarding(true, at: Date(timeIntervalSinceReferenceDate: 1.125), engine: engine, isActive: true)
            frame(driver, engine, 2, active: false)
            XCTAssertFalse(driver.isFastForwarding)
            frame(driver, engine, 3)
            driver.setFastForwarding(true, at: Date(timeIntervalSinceReferenceDate: 3), engine: engine, isActive: true)
            for index in 1...100 { frame(driver, engine, 3 + Double(index) / 8) }
            XCTAssertEqual(engine.phase, .finished)
            XCTAssertFalse(driver.isFastForwarding)
            let positions = engine.vans.map(\.position)
            let time = engine.runTime
            frame(driver, engine, 100)
            XCTAssertEqual(engine.vans.map(\.position), positions)
            XCTAssertEqual(engine.runTime, time)
            engine.retry() // Retry and Replay share this path.
            driver.reset()
            engine.go()
            frame(driver, engine, 200)
            frame(driver, engine, 200.125)
            XCTAssertEqual(engine.runTime, 0.125)
            XCTAssertFalse(driver.isFastForwarding)
        }
    }

    func testLevelOneAndCorrectedLevelTwoWinAndStayFinished() throws {
        for id in ["proto_01", "proto_02"] {
            let engine = try engine(id)
            let driver = MultiVanFrameDriver()
            if id == "proto_02" { engine.tapSwitch(nodeID: "switch") }
            XCTAssertEqual(engine.previewRoutes.first?.ending, .matchingHouse)
            XCTAssertEqual(engine.changeCount, engine.level.parChanges)
            engine.go()
            for index in 0...120 { frame(driver, engine, Double(index) / 8) }
            XCTAssertEqual(engine.phase, .finished)
            XCTAssertEqual(engine.outcome, .win)
            XCTAssertEqual(engine.vans[0].status, .parked)
            let time = engine.runTime
            let position = engine.vans[0].position
            driver.reset()
            frame(driver, engine, 500)
            frame(driver, engine, 501)
            XCTAssertEqual(engine.runTime, time)
            XCTAssertEqual(engine.vans[0].position, position)
            engine.retry() // Replay uses the same engine action.
            XCTAssertEqual(engine.phase, .plan)
            XCTAssertNil(engine.outcome)
            XCTAssertEqual(engine.changeCount, engine.level.parChanges)
        }
    }

    func testLevelTwoFailureRetryStopAndResetPreserveEngineSemantics() throws {
        let engine = try engine("proto_02")
        let driver = MultiVanFrameDriver()
        XCTAssertEqual(engine.previewRoutes.first?.ending, .deadEnd)
        engine.go()
        for index in 0...80 { frame(driver, engine, Double(index) / 8) }
        XCTAssertEqual(engine.outcome, .failStuck(vanID: "red", nodeID: "barrier"))
        let failPoint = engine.lastFailPoint
        let switches = engine.runtimeGraph.nodesByID["switch"]?.activeOutgoingEdgeID
        engine.retry()
        driver.reset()
        XCTAssertEqual(engine.phase, .plan)
        XCTAssertNil(engine.outcome)
        XCTAssertEqual(engine.lastFailPoint, failPoint)
        XCTAssertEqual(engine.runtimeGraph.nodesByID["switch"]?.activeOutgoingEdgeID, switches)
        XCTAssertEqual(engine.changeCount, 0)
        XCTAssertEqual(engine.vans[0].position, RoadPoint(x: 0, y: 0))
        engine.tapSwitch(nodeID: "switch")
        engine.go()
        frame(driver, engine, 20)
        frame(driver, engine, 20.125)
        engine.stop()
        driver.reset()
        XCTAssertEqual(engine.phase, .plan)
        XCTAssertEqual(engine.changeCount, 1)
        XCTAssertEqual(engine.previewRoutes.first?.ending, .matchingHouse)
        engine.resetSwitches()
        XCTAssertEqual(engine.changeCount, 0)
        XCTAssertEqual(engine.previewRoutes.first?.ending, .deadEnd)
        XCTAssertEqual(engine.runtimeGraph.nodesByID["switch"]?.activeOutgoingEdgeID, "to_barrier")
    }

    @MainActor
    func testConstructingScreenRepeatedlyDoesNotAdvanceOrReplaceEngine() throws {
        let engine = try engine()
        engine.go()
        engine.advance(by: 0.125)
        let position = engine.vans[0].position
        let settingsService = UserSettingsService()
        for _ in 0..<10 {
            let screen = MultiVanGameplayScreen(engine: engine, settingsService: settingsService)
            XCTAssertTrue(screen.engine === engine)
            XCTAssertNil(screen.onNext)
            _ = screen.body
        }
        XCTAssertEqual(engine.drainEvents(), [.go])
        XCTAssertEqual(engine.vans[0].position, position)
        XCTAssertEqual(engine.runTime, 0.125, accuracy: 1e-9)
    }

    #if DEBUG
    func testPrototypeNextUsesFreshEngineThenReturnsToList() throws {
        let levels = try [engine().level, engine("proto_02").level]
        var session = MultiVanPrototypeSession()
        XCTAssertNil(session.engine)
        try session.open(levels[0])
        let first = try XCTUnwrap(session.engine)
        first.go()
        first.advance(by: 20)
        XCTAssertEqual(first.outcome, .win)

        try session.next(in: levels)
        let second = try XCTUnwrap(session.engine)
        XCTAssertFalse(first === second)
        XCTAssertEqual(second.level.id, "proto_02")
        XCTAssertEqual(second.level.name, "Pick a Lane")
        XCTAssertEqual(Set(second.runtimeGraph.nodesByID.keys), Set(levels[1].graph.nodes.map(\.id)))
        XCTAssertEqual(second.phase, .plan)
        XCTAssertNil(second.outcome)
        XCTAssertEqual(second.runTime, 0)
        XCTAssertEqual(second.changeCount, 0)
        XCTAssertEqual(second.vans[0].position, RoadPoint(x: 0, y: 0))
        XCTAssertEqual(second.vans[0].status, .waiting)
        XCTAssertEqual(second.runtimeGraph.nodesByID["switch"]?.activeOutgoingEdgeID, "to_barrier")
        XCTAssertEqual(second.previewRoutes.first?.ending, .deadEnd)

        second.tapSwitch(nodeID: "switch")
        second.go()
        second.advance(by: 20)
        XCTAssertEqual(second.outcome, .win)
        try session.next(in: levels)
        XCTAssertNil(session.engine)
    }

    func testPrototypeDirectSelectionAndReopeningDiscardRunAndSwitchState() throws {
        let level = try engine("proto_02").level
        var session = MultiVanPrototypeSession()
        try session.open(level)
        let previous = try XCTUnwrap(session.engine)
        previous.tapSwitch(nodeID: "switch")
        previous.go()
        previous.advance(by: 0.25)
        session.returnToList()
        XCTAssertNil(session.engine)

        try session.open(level)
        let reopened = try XCTUnwrap(session.engine)
        XCTAssertFalse(previous === reopened)
        XCTAssertEqual(reopened.phase, .plan)
        XCTAssertEqual(reopened.changeCount, 0)
        XCTAssertEqual(reopened.runTime, 0)
        XCTAssertEqual(reopened.vans[0].position, RoadPoint(x: 0, y: 0))
        XCTAssertEqual(reopened.runtimeGraph.nodesByID["switch"]?.activeOutgoingEdgeID, "to_barrier")
        XCTAssertEqual(reopened.previewRoutes.first?.ending, .deadEnd)

        // An empty repository or absent selection also ends at the list.
        try session.next(in: [])
        XCTAssertNil(session.engine)
        try session.next(in: [level])
        XCTAssertNil(session.engine)
    }
    #endif
}

final class MultiVanEngineTests: XCTestCase {
    private func makeLevel(initial: [String: String] = ["two": "two_1"]) throws -> MultiVanLevel {
        let exits = [("two", 2), ("three", 3), ("four", 4), ("pass", 1), ("leaf", 0), ("five", 5)]
        let nodes: [[String: Any]] = exits.enumerated().map { index, entry in
            ["id": entry.0, "x": index, "y": 0,
             "outgoingEdgeIDs": (0..<entry.1).map { "\(entry.0)_\($0)" }]
        }
        let edges: [[String: Any]] = exits.flatMap { id, count in
            (0..<count).map { ["id": "\(id)_\($0)", "fromNodeID": id, "toNodeID": "leaf"] }
        }
        let json: [String: Any] = [
            "id": "switch_fixture", "name": "Switch fixture",
            // Edge storage order must not determine switch cycling order.
            "graph": ["nodes": nodes, "edges": Array(edges.reversed())],
            "vans": [], "houses": [], "initialSwitchEdges": initial, "parChanges": 2
        ]
        return try JSONDecoder().decode(MultiVanLevel.self, from: JSONSerialization.data(withJSONObject: json))
    }

    func testStartsInPlanWithNoChanges() throws {
        let engine = try MultiVanEngine(level: makeLevel())
        XCTAssertEqual(engine.phase, .plan)
        XCTAssertEqual(engine.changeCount, 0)
    }

    func testBoardOffersSwitchesOnlyForTwoThroughFourExits() throws {
        let engine = try MultiVanEngine(level: makeLevel())
        XCTAssertEqual(MultiVanBoardView.switchNodes(in: engine.runtimeGraph).map(\.id), ["four", "three", "two"])
        XCTAssertEqual(engine.tapSwitch(nodeID: "five"), .notASwitch)
    }

    func testAppliesInitialSwitchSelections() throws {
        let engine = try MultiVanEngine(level: makeLevel(initial: ["two": "two_1", "three": "three_2"]))
        XCTAssertEqual(engine.runtimeGraph.nodesByID["two"]?.activeOutgoingEdgeID, "two_1")
        XCTAssertEqual(engine.runtimeGraph.nodesByID["three"]?.activeOutgoingEdgeID, "three_2")
        XCTAssertEqual(engine.changeCount, 0)
    }

    func testUnspecifiedNodesDefaultToFirstExitAndLeavesHaveNone() throws {
        let engine = try MultiVanEngine(level: makeLevel(initial: [:]))
        for id in ["two", "three", "four", "pass"] {
            XCTAssertEqual(engine.runtimeGraph.nodesByID[id]?.activeOutgoingEdgeID, "\(id)_0")
        }
        XCTAssertNil(engine.runtimeGraph.nodesByID["leaf"]?.activeOutgoingEdgeID)
    }

    func testTwoWaySwitchCyclesFromConfiguredExit() throws {
        let engine = try MultiVanEngine(level: makeLevel())
        XCTAssertEqual(engine.tapSwitch(nodeID: "two"), .accepted)
        XCTAssertEqual(engine.runtimeGraph.nodesByID["two"]?.activeOutgoingEdgeID, "two_0")
        XCTAssertEqual(engine.changeCount, 1)
        XCTAssertEqual(engine.tapSwitch(nodeID: "two"), .accepted)
        XCTAssertEqual(engine.runtimeGraph.nodesByID["two"]?.activeOutgoingEdgeID, "two_1")
        XCTAssertEqual(engine.changeCount, 0)
    }

    func testThreeWaySwitchWrapsToStartingSettingAndZeroChanges() throws {
        let engine = try MultiVanEngine(level: makeLevel(initial: ["three": "three_1"]))
        for (edge, changes) in [("three_2", 1), ("three_0", 2), ("three_1", 0)] {
            XCTAssertEqual(engine.tapSwitch(nodeID: "three"), .accepted)
            XCTAssertEqual(engine.runtimeGraph.nodesByID["three"]?.activeOutgoingEdgeID, edge)
            XCTAssertEqual(engine.changeCount, changes)
        }
    }

    func testFourWaySwitchCountsEachForwardStepAndWraps() throws {
        let engine = try MultiVanEngine(level: makeLevel())
        for index in 1...4 {
            XCTAssertEqual(engine.tapSwitch(nodeID: "four"), .accepted)
            XCTAssertEqual(engine.runtimeGraph.nodesByID["four"]?.activeOutgoingEdgeID, "four_\(index % 4)")
            XCTAssertEqual(engine.changeCount, index % 4)
        }
    }

    func testNonSwitchAndUnknownNodesAreRejected() throws {
        let engine = try MultiVanEngine(level: makeLevel())
        for id in ["pass", "leaf", "unknown"] {
            XCTAssertEqual(engine.tapSwitch(nodeID: id), .notASwitch)
        }
        XCTAssertEqual(engine.runtimeGraph.nodesByID["pass"]?.activeOutgoingEdgeID, "pass_0")
        XCTAssertNil(engine.runtimeGraph.nodesByID["leaf"]?.activeOutgoingEdgeID)
    }

    func testRejectedTapsDoNotChangeCounter() throws {
        let engine = try MultiVanEngine(level: makeLevel())
        engine.tapSwitch(nodeID: "two")
        for id in ["pass", "leaf", "unknown"] {
            XCTAssertEqual(engine.tapSwitch(nodeID: id), .notASwitch)
            XCTAssertEqual(engine.changeCount, 1)
        }
    }

    func testResetRestoresConfiguredAndDefaultSelections() throws {
        let engine = try MultiVanEngine(level: makeLevel())
        for id in ["two", "three", "four"] { engine.tapSwitch(nodeID: id) }
        engine.resetSwitches()
        XCTAssertEqual(engine.runtimeGraph.nodesByID["two"]?.activeOutgoingEdgeID, "two_1")
        XCTAssertEqual(engine.runtimeGraph.nodesByID["three"]?.activeOutgoingEdgeID, "three_0")
        XCTAssertEqual(engine.runtimeGraph.nodesByID["four"]?.activeOutgoingEdgeID, "four_0")
    }

    func testResetReturnsChangeCountToZeroWithoutChangingPhase() throws {
        let engine = try MultiVanEngine(level: makeLevel())
        engine.tapSwitch(nodeID: "two")
        engine.tapSwitch(nodeID: "three")
        XCTAssertEqual(engine.changeCount, 2)
        engine.resetSwitches()
        XCTAssertEqual(engine.changeCount, 0)
        XCTAssertEqual(engine.phase, .plan)
        engine.resetSwitches()
        XCTAssertEqual(engine.changeCount, 0)
    }

    func testSelectionsAreIndependentAndChangesSumAcrossSwitches() throws {
        let engine = try MultiVanEngine(level: makeLevel())
        engine.tapSwitch(nodeID: "two")
        engine.tapSwitch(nodeID: "three")
        engine.tapSwitch(nodeID: "three")
        XCTAssertEqual(engine.runtimeGraph.nodesByID["two"]?.activeOutgoingEdgeID, "two_0")
        XCTAssertEqual(engine.runtimeGraph.nodesByID["three"]?.activeOutgoingEdgeID, "three_2")
        XCTAssertEqual(engine.runtimeGraph.nodesByID["four"]?.activeOutgoingEdgeID, "four_0")
        XCTAssertEqual(engine.changeCount, 3)
        engine.tapSwitch(nodeID: "two")
        XCTAssertEqual(engine.changeCount, 2)
    }

    func testInjectedTuningIsCopiedPerEngine() throws {
        var tuning = MultiVanTuning.default
        tuning.vanSpeed = 3
        tuning.stepDuration = 0.02
        tuning.liveSwitchLockRadius = 0.8
        let level = try makeLevel()
        let custom = try MultiVanEngine(level: level, tuning: tuning)
        tuning.vanSpeed = 9
        let standard = try MultiVanEngine(level: level)
        XCTAssertEqual(custom.tuning.vanSpeed, 3)
        XCTAssertEqual(custom.tuning.stepDuration, 0.02)
        XCTAssertEqual(custom.tuning.liveSwitchLockRadius, 0.8)
        XCTAssertEqual(standard.tuning.vanSpeed, MultiVanTuning.default.vanSpeed)
        custom.tapSwitch(nodeID: "two")
        XCTAssertEqual(standard.changeCount, 0)
    }

    func testInvalidInitialSelectionFallsBackToFirstExit() throws {
        let engine = try MultiVanEngine(level: makeLevel(initial: ["two": "missing", "leaf": "two_0"]))
        XCTAssertEqual(engine.runtimeGraph.nodesByID["two"]?.activeOutgoingEdgeID, "two_0")
        XCTAssertNil(engine.runtimeGraph.nodesByID["leaf"]?.activeOutgoingEdgeID)
        XCTAssertEqual(engine.changeCount, 0)
    }
}

final class MultiVanRoutePreviewTests: XCTestCase {
    private func makeLevel(
        nodes: [RouteNode], edges: [RouteEdge],
        vans: [[String: Any]]? = nil,
        houses: [[String: String]], initial: [String: String] = [:], edgeLimit: Int = 40
    ) throws -> MultiVanEngine {
        let graph = try JSONSerialization.jsonObject(with: JSONEncoder().encode(RouteGraph(nodes: nodes, edges: edges)))
        let json: [String: Any] = [
            "id": "preview", "name": "Preview", "graph": graph,
            "vans": vans ?? [["id": "van", "color": "red", "startNodeID": nodes.first?.id ?? "start"]],
            "houses": houses, "initialSwitchEdges": initial, "parChanges": 0
        ]
        let level = try JSONDecoder().decode(MultiVanLevel.self, from: JSONSerialization.data(withJSONObject: json))
        var tuning = MultiVanTuning.default
        tuning.previewEdgeLimit = edgeLimit
        return try MultiVanEngine(level: level, tuning: tuning)
    }

    private func chain(_ count: Int, terminal: String = "house") -> ([RouteNode], [RouteEdge]) {
        let nodes = (0...count).map { index in
            RouteNode(id: index == count ? terminal : "n\(index)", x: Double(index), y: 0,
                      outgoingEdgeIDs: index == count ? [] : ["e\(index)"])
        }
        let edges = (0..<count).map { index in
            RouteEdge(id: "e\(index)", fromNodeID: "n\(index)",
                      toNodeID: index + 1 == count ? terminal : "n\(index + 1)")
        }
        return (nodes, edges)
    }

    func testMatchingWrongAndDeadEndAndFinalEdgeTerminal() throws {
        let (nodes, edges) = chain(2)
        let match = try makeLevel(nodes: nodes, edges: edges,
                                  houses: [["nodeID": "house", "color": "red"]], edgeLimit: 2)
        XCTAssertEqual(match.previewRoutes[0], MultiVanPreviewRoute(edgeIDs: ["e0", "e1"], ending: .matchingHouse))
        let wrong = try makeLevel(nodes: nodes, edges: edges, houses: [["nodeID": "house", "color": "blue"]])
        XCTAssertEqual(wrong.previewRoutes[0].ending, .wrongHouse)
        let dead = try makeLevel(nodes: nodes, edges: edges, houses: [])
        XCTAssertEqual(dead.previewRoutes[0].ending, .deadEnd)
        let finalEdge = try makeLevel(nodes: nodes, edges: edges, houses: [], edgeLimit: 2)
        XCTAssertEqual(finalEdge.previewRoutes[0].ending, .deadEnd)
    }

    func testLoopLimitAndEdgeOrder() throws {
        let nodes = [
            RouteNode(id: "start", x: 0, y: 0, outgoingEdgeIDs: ["first"]),
            RouteNode(id: "middle", x: 1, y: 0, outgoingEdgeIDs: ["second"])
        ]
        let edges = [
            RouteEdge(id: "first", fromNodeID: "start", toNodeID: "middle"),
            RouteEdge(id: "second", fromNodeID: "middle", toNodeID: "start")
        ]
        let engine = try makeLevel(nodes: nodes, edges: edges, houses: [], edgeLimit: 3)
        XCTAssertEqual(engine.previewRoutes[0], MultiVanPreviewRoute(edgeIDs: ["first", "second", "first"], ending: .loopLimit))
    }

    func testSwitchUpdatesPreviewRejectedTapDoesNotAndResetRestoresIt() throws {
        let nodes = [
            RouteNode(id: "start", x: 0, y: 0, outgoingEdgeIDs: ["toSwitch"]),
            RouteNode(id: "switch", x: 1, y: 0, outgoingEdgeIDs: ["wrong", "right"]),
            RouteNode(id: "bad", x: 2, y: 0, outgoingEdgeIDs: []),
            RouteNode(id: "house", x: 2, y: 1, outgoingEdgeIDs: [])
        ]
        let edges = [
            RouteEdge(id: "toSwitch", fromNodeID: "start", toNodeID: "switch"),
            RouteEdge(id: "wrong", fromNodeID: "switch", toNodeID: "bad"),
            RouteEdge(id: "right", fromNodeID: "switch", toNodeID: "house")
        ]
        let engine = try makeLevel(nodes: nodes, edges: edges,
                                   houses: [["nodeID": "house", "color": "red"]],
                                   initial: ["switch": "wrong"])
        let original = engine.previewRoutes
        XCTAssertEqual(original[0].ending, .deadEnd)
        XCTAssertEqual(engine.tapSwitch(nodeID: "switch"), .accepted)
        XCTAssertEqual(engine.previewRoutes[0].edgeIDs, ["toSwitch", "right"])
        let updated = engine.previewRoutes
        XCTAssertEqual(engine.tapSwitch(nodeID: "bad"), .notASwitch)
        XCTAssertEqual(engine.previewRoutes, updated)
        engine.go()
        XCTAssertEqual(engine.tapSwitch(nodeID: "switch"), .rejectedFrozen)
        XCTAssertEqual(engine.previewRoutes, updated)
        engine.stop()
        engine.resetSwitches()
        XCTAssertEqual(engine.previewRoutes, original)
    }

    func testMultipleVansHaveIndependentOrderedPreviewsWithoutMutatingGraph() throws {
        let (nodes, edges) = chain(1)
        let engine = try makeLevel(nodes: nodes, edges: edges, vans: [
            ["id": "redVan", "color": "red", "startNodeID": "n0"],
            ["id": "blueVan", "color": "blue", "startNodeID": "n0"]
        ], houses: [["nodeID": "house", "color": "red"]])
        let graphBefore = engine.runtimeGraph
        XCTAssertEqual(engine.previewRoutes.map(\.ending), [.matchingHouse, .wrongHouse])
        XCTAssertEqual(engine.previewRoutes.map(\.edgeIDs), [["e0"], ["e0"]])
        XCTAssertEqual(engine.runtimeGraph.nodesByID["n0"]?.activeOutgoingEdgeID,
                       graphBefore.nodesByID["n0"]?.activeOutgoingEdgeID)
        XCTAssertEqual(engine.runtimeGraph.edgeUsageCounts, graphBefore.edgeUsageCounts)
    }

    func testThreeWaySwitchUpdatesArrowAndPreviewInDeclaredOrder() throws {
        let nodes = [
            RouteNode(id: "start", x: 0, y: 1, outgoingEdgeIDs: ["toSwitch"]),
            RouteNode(id: "switch", x: 1, y: 1, outgoingEdgeIDs: ["south", "east", "north"]),
            RouteNode(id: "dead", x: 1, y: 0, outgoingEdgeIDs: []),
            RouteNode(id: "wrong", x: 2, y: 1, outgoingEdgeIDs: []),
            RouteNode(id: "right", x: 1, y: 2, outgoingEdgeIDs: [])
        ]
        let edges = [
            RouteEdge(id: "north", fromNodeID: "switch", toNodeID: "right"),
            RouteEdge(id: "east", fromNodeID: "switch", toNodeID: "wrong"),
            RouteEdge(id: "south", fromNodeID: "switch", toNodeID: "dead"),
            RouteEdge(id: "toSwitch", fromNodeID: "start", toNodeID: "switch")
        ]
        let engine = try makeLevel(nodes: nodes, edges: edges, houses: [
            ["nodeID": "wrong", "color": "blue"], ["nodeID": "right", "color": "red"]
        ])
        XCTAssertEqual(engine.previewRoutes[0].ending, .deadEnd)
        let expected: [(String, Double, MultiVanPreviewEnding, Int)] = [
            ("east", 0, .wrongHouse, 1), ("north", -.pi / 2, .matchingHouse, 2), ("south", .pi / 2, .deadEnd, 0)
        ]
        for (edgeID, angle, ending, changes) in expected {
            XCTAssertEqual(engine.tapSwitch(nodeID: "switch"), .accepted)
            let node = try XCTUnwrap(engine.runtimeGraph.nodesByID["switch"])
            XCTAssertEqual(node.activeOutgoingEdgeID, edgeID)
            let edge = try XCTUnwrap(engine.runtimeGraph.edgesByID[edgeID])
            XCTAssertEqual(SwitchArrowDirectionResolver.directionAngle(for: edge, from: node, in: engine.runtimeGraph),
                           angle, accuracy: 1e-9)
            XCTAssertEqual(engine.previewRoutes[0], MultiVanPreviewRoute(edgeIDs: ["toSwitch", edgeID], ending: ending))
            XCTAssertEqual(engine.changeCount, changes)
        }
    }
}

final class MultiVanMovementTests: XCTestCase {
    private func makeLevel(
        nodes: [RouteNode] = [
            RouteNode(id: "start", x: 0, y: 0, outgoingEdgeIDs: ["road"]),
            RouteNode(id: "end", x: 3, y: 0, outgoingEdgeIDs: [])
        ],
        edges: [RouteEdge] = [RouteEdge(id: "road", fromNodeID: "start", toNodeID: "end")],
        houses: [String] = ["end"],
        initial: [String: String] = [:],
        departDelay: Double = 0
    ) throws -> MultiVanLevel {
        let graph = try JSONSerialization.jsonObject(with: JSONEncoder().encode(RouteGraph(nodes: nodes, edges: edges)))
        let json: [String: Any] = [
            "id": "movement", "name": "Movement", "graph": graph,
            "vans": [["id": "van", "color": "red", "startNodeID": "start", "departDelay": departDelay]],
            "houses": houses.map { ["nodeID": $0, "color": "red"] },
            "initialSwitchEdges": initial, "parChanges": 0
        ]
        return try JSONDecoder().decode(MultiVanLevel.self, from: JSONSerialization.data(withJSONObject: json))
    }

    private func switchLevel(houses: [String] = ["end", "other"]) throws -> MultiVanLevel {
        try makeLevel(nodes: [
            RouteNode(id: "start", x: 0, y: 0, outgoingEdgeIDs: ["incoming"]),
            RouteNode(id: "switch", x: 1, y: 0, outgoingEdgeIDs: ["straight", "turn"]),
            RouteNode(id: "end", x: 3, y: 0, outgoingEdgeIDs: []),
            RouteNode(id: "other", x: 1, y: 3, outgoingEdgeIDs: [])
        ], edges: [
            RouteEdge(id: "incoming", fromNodeID: "start", toNodeID: "switch"),
            RouteEdge(id: "straight", fromNodeID: "switch", toNodeID: "end"),
            RouteEdge(id: "turn", fromNodeID: "switch", toNodeID: "other")
        ], houses: houses)
    }

    func testStopResetsMovementAndKeepsPlan() throws {
        let engine = try MultiVanEngine(level: switchLevel())
        engine.tapSwitch(nodeID: "switch")
        engine.go()
        engine.advance(by: 0.5 + engine.tuning.stepDuration / 2)
        engine.stop()
        XCTAssertEqual(engine.phase, .plan)
        XCTAssertEqual(engine.runTime, 0)
        XCTAssertEqual(engine.vans[0].status, .waiting)
        XCTAssertEqual(engine.vans[0].position, RoadPoint(x: 0, y: 0))
        XCTAssertNil(engine.vans[0].currentEdgeID)
        XCTAssertEqual(engine.vans[0].distanceAlongEdge, 0)
        XCTAssertEqual(engine.runtimeGraph.nodesByID["switch"]?.activeOutgoingEdgeID, "turn")
        XCTAssertEqual(engine.changeCount, 1)
        XCTAssertNil(engine.lastFailPoint)
        engine.go()
        engine.advance(by: engine.tuning.stepDuration / 2)
        XCTAssertEqual(engine.runTime, 0)
        XCTAssertEqual(engine.vans[0].distanceAlongEdge, 0)
    }

    func testStopRestartsDepartureDelay() throws {
        let engine = try MultiVanEngine(level: makeLevel(departDelay: 0.5))
        engine.go()
        engine.advance(by: 1)
        engine.stop()
        engine.go()
        engine.advance(by: 0.5)
        XCTAssertEqual(engine.vans[0].status, .waiting)
        engine.advance(by: 0.5)
        XCTAssertEqual(engine.vans[0].distanceAlongEdge, 0.75, accuracy: 1e-12)
    }

    func testRetryKeepsChangedSwitchAndReplaysDeterministically() throws {
        let engine = try MultiVanEngine(level: switchLevel(houses: []))
        engine.tapSwitch(nodeID: "switch")
        engine.go()
        engine.advance(by: 1)
        let position = engine.vans[0].position
        engine.advance(by: 10)
        let outcome = engine.outcome
        let time = engine.runTime
        engine.retry()
        XCTAssertEqual(engine.phase, .plan)
        XCTAssertNil(engine.outcome)
        XCTAssertEqual(engine.runTime, 0)
        XCTAssertEqual(engine.vans[0].status, .waiting)
        XCTAssertNil(engine.vans[0].currentEdgeID)
        XCTAssertEqual(engine.vans[0].distanceAlongEdge, 0)
        XCTAssertEqual(engine.vans[0].position, RoadPoint(x: 0, y: 0))
        XCTAssertEqual(engine.runtimeGraph.nodesByID["switch"]?.activeOutgoingEdgeID, "turn")
        XCTAssertEqual(engine.changeCount, 1)
        XCTAssertEqual(engine.lastFailPoint, RoadPoint(x: 1, y: 3))
        engine.go()
        engine.advance(by: 1)
        XCTAssertEqual(engine.vans[0].position, position)
        engine.advance(by: 10)
        XCTAssertEqual(engine.outcome, outcome)
        XCTAssertEqual(engine.runTime, time)
    }

    func testInitialVanWaitsAtStartAndPlanDoesNotAdvance() throws {
        let engine = try MultiVanEngine(level: makeLevel())
        XCTAssertEqual(engine.vans.count, 1)
        XCTAssertEqual(engine.vans[0].id, "van")
        XCTAssertEqual(engine.vans[0].color, .red)
        XCTAssertEqual(engine.vans[0].status, .waiting)
        XCTAssertNil(engine.vans[0].currentEdgeID)
        XCTAssertEqual(engine.vans[0].distanceAlongEdge, 0)
        XCTAssertEqual(engine.vans[0].position, RoadPoint(x: 0, y: 0))
        engine.advance(by: 1)
        XCTAssertEqual(engine.vans[0].status, .waiting)
        XCTAssertEqual(engine.runTime, 0)
    }

    func testGoEntersRunWithoutChangingSwitchConfiguration() throws {
        let engine = try MultiVanEngine(level: switchLevel())
        engine.tapSwitch(nodeID: "switch")
        engine.go()
        XCTAssertEqual(engine.phase, .run)
        XCTAssertEqual(engine.vans[0].status, .driving)
        XCTAssertEqual(engine.vans[0].currentEdgeID, "incoming")
        XCTAssertEqual(engine.vans[0].distanceAlongEdge, 0)
        XCTAssertEqual(engine.runTime, 0)
        XCTAssertEqual(engine.runtimeGraph.nodesByID["switch"]?.activeOutgoingEdgeID, "turn")
        XCTAssertEqual(engine.changeCount, 1)
        XCTAssertEqual(engine.tapSwitch(nodeID: "switch"), .rejectedFrozen)
        XCTAssertEqual(engine.changeCount, 1)
    }

    func testRepeatedGoDoesNotRestartRun() throws {
        let engine = try MultiVanEngine(level: makeLevel())
        engine.go()
        engine.advance(by: 0.5)
        let position = engine.vans[0].position
        engine.go()
        XCTAssertEqual(engine.vans[0].position, position)
        XCTAssertEqual(engine.runTime, 0.5)
    }

    func testDefaultSpeedIsOneAndAHalfUnitsPerSecond() throws {
        let engine = try MultiVanEngine(level: makeLevel())
        engine.go()
        engine.advance(by: 1)
        XCTAssertEqual(engine.vans[0].distanceAlongEdge, 1.5, accuracy: 1e-12)
        XCTAssertEqual(engine.vans[0].position.x, 1.5, accuracy: 1e-12)
        XCTAssertEqual(engine.vans[0].position.y, 0)
        XCTAssertEqual(engine.runTime, 1)
    }

    func testThreeUnitRoadParksAtTwoSeconds() throws {
        let engine = try MultiVanEngine(level: makeLevel())
        engine.go()
        engine.advance(by: 2 - engine.tuning.stepDuration)
        XCTAssertEqual(engine.vans[0].status, .driving)
        engine.advance(by: engine.tuning.stepDuration)
        XCTAssertEqual(engine.vans[0].status, .parked)
        XCTAssertEqual(engine.vans[0].distanceAlongEdge, 3)
        XCTAssertEqual(engine.vans[0].position, RoadPoint(x: 3, y: 0))
        XCTAssertEqual(engine.phase, .finished)
    }

    func testFramePartitionsProduceIdenticalSimulationResults() throws {
        let frames: [[Double]] = [
            [1], Array(repeating: 0.1, count: 10), Array(repeating: 0.25, count: 4),
            Array(repeating: 0.05, count: 20), Array(repeating: 1.0 / 60, count: 60),
            [0.13, 0.007, 0.3, 0.563]
        ]
        let reference = try MultiVanEngine(level: switchLevel())
        reference.go()
        reference.advance(by: 1)
        for partition in frames {
            let engine = try MultiVanEngine(level: switchLevel())
            engine.go()
            for frame in partition { engine.advance(by: frame) }
            XCTAssertEqual(engine.runTime, reference.runTime)
            XCTAssertEqual(engine.vans[0].currentEdgeID, reference.vans[0].currentEdgeID)
            XCTAssertEqual(engine.vans[0].status, reference.vans[0].status)
            XCTAssertEqual(engine.vans[0].distanceAlongEdge, reference.vans[0].distanceAlongEdge)
            XCTAssertEqual(engine.vans[0].position, reference.vans[0].position)
            // A fractional remainder must also behave identically on the next step.
            engine.advance(by: engine.tuning.stepDuration)
            XCTAssertEqual(engine.runTime, 1 + engine.tuning.stepDuration)
        }
    }

    func testFractionalTimeIsPreservedUntilACompleteStep() throws {
        let engine = try MultiVanEngine(level: makeLevel())
        engine.go()
        engine.advance(by: engine.tuning.stepDuration * 0.4)
        XCTAssertEqual(engine.runTime, 0)
        XCTAssertEqual(engine.vans[0].distanceAlongEdge, 0)
        engine.advance(by: engine.tuning.stepDuration * 0.6)
        XCTAssertEqual(engine.runTime, engine.tuning.stepDuration)
        XCTAssertEqual(engine.vans[0].distanceAlongEdge, 1.5 * engine.tuning.stepDuration)
    }

    func testVanFollowsSelectedSwitchExit() throws {
        let engine = try MultiVanEngine(level: switchLevel())
        engine.tapSwitch(nodeID: "switch")
        engine.go()
        engine.advance(by: 1)
        XCTAssertEqual(engine.vans[0].currentEdgeID, "turn")
        XCTAssertEqual(engine.vans[0].position.x, 1, accuracy: 1e-12)
        XCTAssertEqual(engine.vans[0].position.y, 0.5, accuracy: 1e-12)
    }

    func testSwitchSelectionIsReadOnArrival() throws {
        let engine = try MultiVanEngine(level: switchLevel())
        engine.tapSwitch(nodeID: "switch")
        engine.go()
        engine.advance(by: 0.5)
        XCTAssertEqual(engine.vans[0].currentEdgeID, "incoming")
        // Exercise shared state changes through the existing reset API, without live taps.
        engine.resetSwitches()
        engine.advance(by: 0.5)
        XCTAssertEqual(engine.vans[0].currentEdgeID, "straight")
        XCTAssertEqual(engine.vans[0].position.x, 1.5, accuracy: 1e-12)
    }

    func testDeadEndBecomesStuckAndStopsMoving() throws {
        let engine = try MultiVanEngine(level: makeLevel(houses: []))
        engine.go()
        engine.advance(by: 2)
        XCTAssertEqual(engine.vans[0].status, .stuck)
        XCTAssertEqual(engine.vans[0].position, RoadPoint(x: 3, y: 0))
        engine.advance(by: 1)
        XCTAssertEqual(engine.vans[0].status, .stuck)
        XCTAssertEqual(engine.vans[0].distanceAlongEdge, 3)
        XCTAssertEqual(engine.phase, .finished)
    }

    func testParkedVanDoesNotContinueEvenWhenHouseHasAnExit() throws {
        let engine = try MultiVanEngine(level: makeLevel(nodes: [
            RouteNode(id: "start", x: 0, y: 0, outgoingEdgeIDs: ["road"]),
            RouteNode(id: "end", x: 1, y: 0, outgoingEdgeIDs: ["return"])
        ], edges: [
            RouteEdge(id: "road", fromNodeID: "start", toNodeID: "end"),
            RouteEdge(id: "return", fromNodeID: "end", toNodeID: "start")
        ]))
        engine.go()
        engine.advance(by: 1)
        XCTAssertEqual(engine.vans[0].status, .parked)
        engine.advance(by: 1)
        XCTAssertEqual(engine.vans[0].currentEdgeID, "road")
        XCTAssertEqual(engine.vans[0].distanceAlongEdge, 1)
        XCTAssertEqual(engine.vans[0].position, RoadPoint(x: 1, y: 0))
    }

    func testOneDefaultStepCrossesTwoEdgesAndCarriesAllLeftoverDistance() throws {
        let engine = try MultiVanEngine(level: makeLevel(nodes: [
            RouteNode(id: "start", x: 0, y: 0, outgoingEdgeIDs: ["a"]),
            RouteNode(id: "middle", x: 0.003, y: 0, outgoingEdgeIDs: ["b"]),
            RouteNode(id: "next", x: 0.007, y: 0, outgoingEdgeIDs: ["c"]),
            RouteNode(id: "end", x: 3, y: 0, outgoingEdgeIDs: [])
        ], edges: [
            RouteEdge(id: "a", fromNodeID: "start", toNodeID: "middle"),
            RouteEdge(id: "b", fromNodeID: "middle", toNodeID: "next"),
            RouteEdge(id: "c", fromNodeID: "next", toNodeID: "end")
        ]))
        engine.go()
        engine.advance(by: engine.tuning.stepDuration)
        XCTAssertEqual(engine.vans[0].currentEdgeID, "c")
        XCTAssertEqual(engine.vans[0].distanceAlongEdge, 0.0055, accuracy: 1e-12)
        XCTAssertEqual(engine.vans[0].position.x, 0.0125, accuracy: 1e-12)
        engine.advance(by: 2 - engine.tuning.stepDuration)
        XCTAssertEqual(engine.vans[0].status, .parked)
        XCTAssertEqual(engine.vans[0].position, RoadPoint(x: 3, y: 0))
    }

    func testCurvedRoadUsesRuntimePathLengthAndPosition() throws {
        let level = try makeLevel(nodes: [
            RouteNode(id: "start", x: 0, y: 0, outgoingEdgeIDs: ["road"]),
            RouteNode(id: "end", x: 1, y: 1, outgoingEdgeIDs: [])
        ], edges: [RouteEdge(id: "road", fromNodeID: "start", toNodeID: "end", roadShape: .verticalFirst)])
        let engine = try MultiVanEngine(level: level)
        let path = try XCTUnwrap(engine.runtimeGraph.edgesByID["road"]?.roadPath)
        engine.go()
        engine.advance(by: 0.6)
        XCTAssertEqual(engine.vans[0].position, path.point(atDistance: engine.vans[0].distanceAlongEdge))
        XCTAssertEqual(engine.vans[0].distanceAlongEdge, 0.9, accuracy: 1e-12)
        engine.advance(by: path.totalLength / engine.tuning.vanSpeed - 0.6 + engine.tuning.stepDuration)
        XCTAssertEqual(engine.vans[0].status, .parked)
        XCTAssertEqual(engine.vans[0].distanceAlongEdge, path.totalLength)
    }

    func testZeroLengthCycleBecomesStuckWithoutHanging() throws {
        let engine = try MultiVanEngine(level: makeLevel(nodes: [
            RouteNode(id: "start", x: 2, y: 1, outgoingEdgeIDs: ["road"])
        ], edges: [RouteEdge(id: "road", fromNodeID: "start", toNodeID: "start")], houses: []))
        engine.go()
        engine.advance(by: engine.tuning.stepDuration)
        XCTAssertEqual(engine.vans[0].status, .stuck)
        XCTAssertEqual(engine.vans[0].position, RoadPoint(x: 2, y: 1))
    }

    func testZeroLengthEdgeCanContinueOntoARealRoad() throws {
        let engine = try MultiVanEngine(level: makeLevel(nodes: [
            RouteNode(id: "start", x: 0, y: 0, outgoingEdgeIDs: ["zero"]),
            RouteNode(id: "middle", x: 0, y: 0, outgoingEdgeIDs: ["road"]),
            RouteNode(id: "end", x: 3, y: 0, outgoingEdgeIDs: [])
        ], edges: [
            RouteEdge(id: "zero", fromNodeID: "start", toNodeID: "middle"),
            RouteEdge(id: "road", fromNodeID: "middle", toNodeID: "end")
        ]))
        engine.go()
        engine.advance(by: 1)
        XCTAssertEqual(engine.vans[0].status, .driving)
        XCTAssertEqual(engine.vans[0].currentEdgeID, "road")
        XCTAssertEqual(engine.vans[0].distanceAlongEdge, 1.5, accuracy: 1e-12)
    }

    func testInjectedMovementTuningIsUsed() throws {
        var tuning = MultiVanTuning.default
        tuning.stepDuration = 0.1
        tuning.vanSpeed = 2
        let engine = try MultiVanEngine(level: makeLevel(), tuning: tuning)
        engine.go()
        engine.advance(by: 0.25)
        XCTAssertEqual(engine.vans[0].distanceAlongEdge, 0.4, accuracy: 1e-12)
        engine.advance(by: 0.05)
        XCTAssertEqual(engine.vans[0].distanceAlongEdge, 0.6, accuracy: 1e-12)
    }

    func testDelayedVanWaitsUntilEligible() throws {
        let engine = try MultiVanEngine(level: makeLevel(departDelay: 0.5))
        engine.go()
        XCTAssertEqual(engine.vans[0].status, .waiting)
        engine.advance(by: 0.5)
        XCTAssertEqual(engine.vans[0].status, .waiting)
        XCTAssertEqual(engine.vans[0].position, RoadPoint(x: 0, y: 0))
        engine.advance(by: 0.5)
        XCTAssertEqual(engine.vans[0].status, .driving)
        XCTAssertEqual(engine.vans[0].distanceAlongEdge, 0.75, accuracy: 1e-12)
    }

    func testInvalidElapsedTimesPreserveStateAndFractionalRemainder() throws {
        let engine = try MultiVanEngine(level: makeLevel())
        engine.go()
        engine.advance(by: engine.tuning.stepDuration / 2)
        for invalid in [0, -1, Double.nan, Double.infinity, -Double.infinity] {
            engine.advance(by: invalid)
            XCTAssertEqual(engine.runTime, 0)
            XCTAssertEqual(engine.vans[0].distanceAlongEdge, 0)
            XCTAssertEqual(engine.vans[0].status, .driving)
        }
        engine.advance(by: engine.tuning.stepDuration / 2)
        XCTAssertEqual(engine.vans[0].distanceAlongEdge, 0.0125, accuracy: 1e-12)
    }
}

final class MultiVanLevelTests: XCTestCase {
    private let levelJSON = #"""
    {
      "id": "proto_test",
      "name": "Small route",
      "graph": {
        "nodes": [
          { "id": "start", "x": 1, "y": 2, "outgoingEdgeIDs": ["road"] },
          { "id": "house", "x": 1, "y": 3, "outgoingEdgeIDs": [] }
        ],
        "edges": [
          { "id": "road", "fromNodeID": "start", "toNodeID": "house", "roadShape": "horizontalFirst" }
        ]
      },
      "vans": [{ "id": "van_1", "color": "red", "startNodeID": "start" }],
      "houses": [{ "nodeID": "house", "color": "red" }],
      "initialSwitchEdges": { "start": "road" },
      "parChanges": 2
    }
    """#

    private func decode(_ json: String) throws -> MultiVanLevel {
        try JSONDecoder().decode(MultiVanLevel.self, from: Data(json.utf8))
    }

    func testRequiredFieldsAndOmittedDefaults() throws {
        let level = try decode(levelJSON)
        XCTAssertEqual(level.id, "proto_test")
        XCTAssertEqual(level.name, "Small route")
        XCTAssertEqual(level.graph.nodes.count, 2)
        XCTAssertEqual(level.graph.nodes[0].id, "start")
        XCTAssertEqual(level.graph.nodes[0].x, 1)
        XCTAssertEqual(level.graph.nodes[0].y, 2)
        XCTAssertEqual(level.graph.nodes[0].outgoingEdgeIDs, ["road"])
        XCTAssertEqual(level.graph.nodes[1].id, "house")
        XCTAssertEqual(level.graph.edges.count, 1)
        XCTAssertEqual(level.graph.edges[0].id, "road")
        XCTAssertEqual(level.graph.edges[0].fromNodeID, "start")
        XCTAssertEqual(level.graph.edges[0].toNodeID, "house")
        XCTAssertEqual(level.graph.edges[0].roadShape, .horizontalFirst)
        XCTAssertEqual(level.vans.count, 1)
        XCTAssertEqual(level.vans[0].id, "van_1")
        XCTAssertEqual(level.vans[0].color, .red)
        XCTAssertEqual(level.vans[0].startNodeID, "start")
        XCTAssertEqual(level.vans[0].departDelay, 0)
        XCTAssertEqual(level.houses.count, 1)
        XCTAssertEqual(level.houses[0].nodeID, "house")
        XCTAssertEqual(level.houses[0].color, .red)
        XCTAssertEqual(level.initialSwitchEdges, ["start": "road"])
        XCTAssertEqual(level.parChanges, 2)
        XCTAssertEqual(level.liveSwitchNodeIDs, [])
        XCTAssertNil(level.hint)
    }

    func testExplicitOptionalValues() throws {
        let json = levelJSON
            .replacingOccurrences(of: #""startNodeID": "start""#, with: #""startNodeID": "start", "departDelay": 1.25"#)
            .replacingOccurrences(of: #""parChanges": 2"#, with: #""parChanges": 2, "liveSwitchNodeIDs": ["start"], "hint": "Wait at the merge.""#)
        let level = try decode(json)
        XCTAssertEqual(level.vans[0].departDelay, 1.25)
        XCTAssertEqual(level.liveSwitchNodeIDs, ["start"])
        XCTAssertEqual(level.hint, "Wait at the merge.")
    }

    func testEveryColorAndPresentation() throws {
        let colors: [(String, VanColor, String, String)] = [
            ("red", .red, "●", "Red"),
            ("blue", .blue, "▲", "Blue"),
            ("yellow", .yellow, "■", "Yellow"),
            ("green", .green, "★", "Green")
        ]
        for (rawValue, expected, symbol, name) in colors {
            let level = try decode(levelJSON.replacingOccurrences(of: "red", with: rawValue))
            XCTAssertEqual(level.vans[0].color, expected)
            XCTAssertEqual(level.houses[0].color, expected)
            XCTAssertEqual(expected.symbol, symbol)
            XCTAssertEqual(expected.displayName, name)
        }
    }

    func testInvalidColorsThrowDecodingErrors() {
        for field in [#""id": "van_1", "color": "red""#, #""nodeID": "house", "color": "red""#] {
            let json = levelJSON.replacingOccurrences(of: field, with: field.replacingOccurrences(of: "red", with: "purple"))
            XCTAssertThrowsError(try decode(json)) { error in
                guard case DecodingError.dataCorrupted = error else {
                    return XCTFail("Expected invalid color decoding error, got \(error)")
                }
            }
        }
    }

    func testTuningDefaultsAndIndependentConfiguration() {
        let tuning = MultiVanTuning.default
        XCTAssertEqual(tuning.vanSpeed, 1.5)
        XCTAssertEqual(tuning.stepDuration, 1.0 / 120.0)
        XCTAssertEqual(tuning.crashDistance, 0.35)
        XCTAssertEqual(tuning.liveSwitchLockRadius, 0.4)
        XCTAssertEqual(tuning.previewEdgeLimit, 40)
        XCTAssertEqual(tuning.failFreezeDuration, 0.6)
        XCTAssertEqual(tuning.fastForwardMultiplier, 2.0)
        XCTAssertEqual(tuning.gridColumns, 5)
        XCTAssertEqual(tuning.gridRows, 7)

        var custom = tuning
        custom.vanSpeed = 2
        custom.crashDistance = 0.5
        custom.liveSwitchLockRadius = 0.6
        XCTAssertEqual(custom.vanSpeed, 2)
        XCTAssertEqual(custom.crashDistance, 0.5)
        XCTAssertEqual(custom.liveSwitchLockRadius, 0.6)
        XCTAssertEqual(MultiVanTuning.default.vanSpeed, 1.5)
        XCTAssertEqual(MultiVanTuning.default.crashDistance, 0.35)
        XCTAssertEqual(MultiVanTuning.default.liveSwitchLockRadius, 0.4)
    }
}

final class MultiVanOutcomeTests: XCTestCase {
    private func makeEngine(
        houseColor: String? = "red", secondDelay: Double? = nil,
        reverseVans: Bool = false, startAtDestination: Bool = false,
        speed: Double = 4, secondHouse: Bool = true
    ) throws -> MultiVanEngine {
        let graph = RouteGraph(nodes: [
            RouteNode(id: "start", x: 0, y: 0, outgoingEdgeIDs: ["road"]),
            RouteNode(id: "end", x: 1, y: 0, outgoingEdgeIDs: []),
            RouteNode(id: "start2", x: 0, y: 1, outgoingEdgeIDs: ["road2"]),
            RouteNode(id: "end2", x: 3, y: 1, outgoingEdgeIDs: [])
        ], edges: [
            RouteEdge(id: "road", fromNodeID: "start", toNodeID: "end"),
            RouteEdge(id: "road2", fromNodeID: "start2", toNodeID: "end2")
        ])
        var vans: [[String: Any]] = [
            ["id": "first", "color": "red", "startNodeID": startAtDestination ? "end" : "start"]
        ]
        if let secondDelay {
            vans.append(["id": "second", "color": "blue", "startNodeID": "start2", "departDelay": secondDelay])
        }
        if reverseVans { vans.reverse() }
        var houses = secondHouse ? [["nodeID": "end2", "color": "blue"]] : []
        if let houseColor { houses.append(["nodeID": "end", "color": houseColor]) }
        let json: [String: Any] = [
            "id": "outcomes", "name": "Outcomes",
            "graph": try JSONSerialization.jsonObject(with: JSONEncoder().encode(graph)),
            "vans": vans, "houses": houses, "initialSwitchEdges": [:], "parChanges": 0
        ]
        let level = try JSONDecoder().decode(MultiVanLevel.self, from: JSONSerialization.data(withJSONObject: json))
        var tuning = MultiVanTuning.default
        tuning.stepDuration = 0.25
        tuning.vanSpeed = speed
        return try MultiVanEngine(level: level, tuning: tuning)
    }

    func testFailureCardCopyUsesOutcomeAndAuthoredColors() throws {
        let engine = try makeEngine(houseColor: "blue", secondDelay: 1)
        XCTAssertEqual(
            MultiVanFailureCopy.message(for: .failCrash(vanIDs: ["first", "second"], point: RoadPoint(x: 0, y: 0)), level: engine.level),
            "Crash! Red and Blue vans collided."
        )
        XCTAssertEqual(
            MultiVanFailureCopy.message(for: .failWrongHouse(vanID: "first", houseNodeID: "end"), level: engine.level),
            "Red went to the blue house!"
        )
        XCTAssertEqual(
            MultiVanFailureCopy.message(for: .failStuck(vanID: "second", nodeID: "dead-end"), level: engine.level),
            "Blue hit a dead end!"
        )
    }

    func testRetryPreservesFailurePointAndResetsAllVansAndTiming() throws {
        for color: String? in ["blue", nil] {
            let engine = try makeEngine(houseColor: color, secondDelay: 1)
            engine.go()
            engine.advance(by: 0.375)
            XCTAssertEqual(engine.lastFailPoint, RoadPoint(x: 1, y: 0))
            engine.retry()
            XCTAssertEqual(engine.phase, .plan)
            XCTAssertNil(engine.outcome)
            XCTAssertEqual(engine.lastFailPoint, RoadPoint(x: 1, y: 0))
            XCTAssertEqual(engine.runTime, 0)
            XCTAssertEqual(engine.vans.map(\.status), [.waiting, .waiting])
            XCTAssertEqual(engine.vans.map(\.distanceAlongEdge), [0, 0])
            XCTAssertTrue(engine.vans.allSatisfy { $0.currentEdgeID == nil })
            XCTAssertEqual(engine.vans.map(\.position), [RoadPoint(x: 0, y: 0), RoadPoint(x: 0, y: 1)])
            engine.go()
            XCTAssertNil(engine.lastFailPoint)
            engine.advance(by: 0.125)
            XCTAssertEqual(engine.runTime, 0)
            XCTAssertEqual(engine.vans[1].status, .waiting)
            engine.advance(by: 0.125)
            XCTAssertEqual(engine.lastFailPoint, RoadPoint(x: 1, y: 0))
        }
    }

    func testStopAndRetryOutsideAllowedPhasesDoNothing() throws {
        let engine = try makeEngine(houseColor: "blue")
        engine.stop()
        engine.retry()
        XCTAssertEqual(engine.phase, .plan)
        engine.go()
        engine.advance(by: 0.125)
        engine.retry()
        XCTAssertEqual(engine.phase, .run)
        engine.advance(by: 0.125)
        XCTAssertEqual(engine.phase, .finished)
        let outcome = engine.outcome
        engine.stop()
        engine.go()
        XCTAssertEqual(engine.phase, .finished)
        XCTAssertEqual(engine.outcome, outcome)
        XCTAssertEqual(engine.lastFailPoint, RoadPoint(x: 1, y: 0))
        XCTAssertEqual(engine.runTime, 0.25)
    }

    func testTerminalStartRecordsFailurePointOnlyForFailures() throws {
        for color: String? in ["red", "blue", nil] {
            let engine = try makeEngine(houseColor: color, startAtDestination: true)
            engine.go()
            XCTAssertEqual(engine.lastFailPoint, color == "red" ? nil : RoadPoint(x: 1, y: 0))
        }
    }

    func testOutcomeStartsNil() throws {
        let engine = try makeEngine()
        XCTAssertNil(engine.outcome)
        engine.go()
        XCTAssertNil(engine.outcome)
    }

    func testMatchingDeliveryParksAndWins() throws {
        let engine = try makeEngine()
        engine.go()
        engine.advance(by: 0.25)
        XCTAssertEqual(engine.vans[0].status, .parked)
        XCTAssertEqual(engine.vans[0].position, RoadPoint(x: 1, y: 0))
        XCTAssertEqual(engine.outcome, .win)
        XCTAssertEqual(engine.phase, .finished)
    }

    func testWrongHouseFailsImmediatelyWithIDs() throws {
        let engine = try makeEngine(houseColor: "blue", secondDelay: 0)
        engine.go()
        engine.advance(by: 10)
        XCTAssertEqual(engine.outcome, .failWrongHouse(vanID: "first", houseNodeID: "end"))
        XCTAssertEqual(engine.phase, .finished)
        XCTAssertEqual(engine.vans[0].position, RoadPoint(x: 1, y: 0))
        // Every van advances through the terminal step before resolving failure.
        XCTAssertEqual(engine.vans[1].position, RoadPoint(x: 1, y: 1))
        XCTAssertEqual(engine.runTime, 0.25)
    }

    func testDeadEndFailsImmediatelyWithIDs() throws {
        let engine = try makeEngine(houseColor: nil, secondDelay: 0)
        engine.go()
        engine.advance(by: 10)
        XCTAssertEqual(engine.outcome, .failStuck(vanID: "first", nodeID: "end"))
        XCTAssertEqual(engine.phase, .finished)
        XCTAssertEqual(engine.vans[0].status, .stuck)
        XCTAssertEqual(engine.vans[0].position, RoadPoint(x: 1, y: 0))
        XCTAssertEqual(engine.vans[1].position, RoadPoint(x: 1, y: 1))
    }

    func testWaitingOrDrivingVanPreventsVictoryUntilAllDelivered() throws {
        for delay in [0.0, 1.0] {
            let engine = try makeEngine(secondDelay: delay)
            engine.go()
            engine.advance(by: 0.25)
            XCTAssertEqual(engine.vans[0].status, .parked)
            XCTAssertEqual(engine.vans[1].status, delay == 0 ? .driving : .waiting)
            XCTAssertNil(engine.outcome)
            XCTAssertEqual(engine.phase, .run)
            engine.advance(by: 2)
            XCTAssertEqual(engine.vans.map(\.status), [.parked, .parked])
            XCTAssertEqual(engine.outcome, .win)
            XCTAssertEqual(engine.phase, .finished)
        }
    }

    func testAllOutcomesFreezeStateAndAreFramePartitionIndependent() throws {
        let cases: [(String?, MultiVanEngine.Outcome)] = [
            ("red", .win), ("blue", .failWrongHouse(vanID: "first", houseNodeID: "end")),
            (nil, .failStuck(vanID: "first", nodeID: "end"))
        ]
        for (color, expected) in cases {
            for frames in [[2.0], Array(repeating: 0.05, count: 40), [0.13, 0.12, 1.75]] {
                let engine = try makeEngine(houseColor: color)
                engine.go()
                for frame in frames { engine.advance(by: frame) }
                XCTAssertEqual(engine.outcome, expected)
                XCTAssertEqual(engine.phase, .finished)
                XCTAssertEqual(engine.runTime, 0.25)
                let van = engine.vans[0]
                for elapsed in [0.125, 100, Double.infinity] { engine.advance(by: elapsed) }
                engine.go()
                XCTAssertEqual(engine.outcome, expected)
                XCTAssertEqual(engine.phase, .finished)
                XCTAssertEqual(engine.runTime, 0.25)
                XCTAssertEqual(engine.vans[0].position, van.position)
                XCTAssertEqual(engine.vans[0].currentEdgeID, van.currentEdgeID)
                XCTAssertEqual(engine.vans[0].distanceAlongEdge, van.distanceAlongEdge)
                XCTAssertEqual(engine.vans[0].status, van.status)
            }
        }
    }

    func testSimultaneousFailuresUseAuthoredVanOrder() throws {
        for reversed in [false, true] {
            let run = try makeEngine(
                houseColor: "blue", secondDelay: 0, reverseVans: reversed,
                speed: 16, secondHouse: false
            )
            run.go()
            run.advance(by: 1)
            XCTAssertEqual(run.outcome, reversed
                ? .failStuck(vanID: "second", nodeID: "end2")
                : .failWrongHouse(vanID: "first", houseNodeID: "end"))
            XCTAssertEqual(run.phase, .finished)
        }
    }

    func testStartingAtTerminalNodeResolvesDuringGo() throws {
        for color: String? in ["red", "blue", nil] {
            let engine = try makeEngine(houseColor: color, startAtDestination: true)
            engine.go()
            let expected: MultiVanEngine.Outcome = color == "red" ? .win : color == "blue"
                ? .failWrongHouse(vanID: "first", houseNodeID: "end") : .failStuck(vanID: "first", nodeID: "end")
            XCTAssertEqual(engine.outcome, expected)
            XCTAssertEqual(engine.phase, .finished)
            XCTAssertEqual(engine.runTime, 0)
            XCTAssertEqual(engine.vans[0].position, RoadPoint(x: 1, y: 0))
        }
    }
}

final class MultiVanBoardSwitchTests: XCTestCase {
    private func pickALane() throws -> MultiVanEngine {
        // Load the authored acceptance level, independent of the test bundle's resources.
        let url = URL(fileURLWithPath: #filePath)
            .deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent()
            .appendingPathComponent("TinyRoutes/Resources/PrototypeLevels/proto_02.json")
        let level = try JSONDecoder().decode(MultiVanLevel.self, from: Data(contentsOf: url))
        return try MultiVanEngine(level: level)
    }

    private func assertConfiguration(
        _ engine: MultiVanEngine, edgeID: String, angle: Double,
        ending: MultiVanPreviewEnding, changes: Int,
        file: StaticString = #filePath, line: UInt = #line
    ) throws {
        let graph = engine.runtimeGraph
        let node = try XCTUnwrap(graph.nodesByID["switch"], file: file, line: line)
        XCTAssertEqual(node.activeOutgoingEdgeID, edgeID, file: file, line: line)
        let edge = try XCTUnwrap(node.activeOutgoingEdgeID.flatMap { graph.edgesByID[$0] }, file: file, line: line)
        XCTAssertEqual(SwitchArrowDirectionResolver.directionAngle(for: edge, from: node, in: graph),
                       angle, accuracy: 1e-9, file: file, line: line)
        XCTAssertEqual(engine.previewRoutes, [MultiVanPreviewRoute(edgeIDs: ["to_switch", edgeID], ending: ending)],
                       file: file, line: line)
        XCTAssertEqual(engine.changeCount, changes, file: file, line: line)
    }

    func testPickALaneTapCycleAndResetKeepArrowPreviewAndCountTogether() throws {
        let engine = try pickALane()
        XCTAssertEqual(MultiVanBoardView.switchNodes(in: engine.runtimeGraph).map(\.id), ["switch"])
        try assertConfiguration(engine, edgeID: "to_barrier", angle: -.pi / 2, ending: .deadEnd, changes: 0)

        // Track the two reads made by the board body separately. Nested value-type
        // graph mutations must invalidate the arrow, as well as the preview Canvas.
        let graphChanged = OSAllocatedUnfairLock(initialState: false)
        let previewChanged = OSAllocatedUnfairLock(initialState: false)
        withObservationTracking { _ = engine.runtimeGraph } onChange: { graphChanged.withLock { $0 = true } }
        withObservationTracking { _ = engine.previewRoutes } onChange: { previewChanged.withLock { $0 = true } }
        XCTAssertEqual(engine.tapSwitch(nodeID: "switch"), .accepted)
        XCTAssertTrue(graphChanged.withLock { $0 })
        XCTAssertTrue(previewChanged.withLock { $0 })
        try assertConfiguration(engine, edgeID: "to_house", angle: 0, ending: .matchingHouse, changes: 1)
        XCTAssertEqual(engine.level.houses.first?.color, .red)
        XCTAssertEqual(engine.runtimeGraph.edgesByID["to_house"]?.toNodeID, "red_house")

        XCTAssertEqual(engine.tapSwitch(nodeID: "switch"), .accepted)
        try assertConfiguration(engine, edgeID: "to_barrier", angle: -.pi / 2, ending: .deadEnd, changes: 0)
        engine.tapSwitch(nodeID: "switch")
        graphChanged.withLock { $0 = false }
        previewChanged.withLock { $0 = false }
        withObservationTracking { _ = engine.runtimeGraph } onChange: { graphChanged.withLock { $0 = true } }
        withObservationTracking { _ = engine.previewRoutes } onChange: { previewChanged.withLock { $0 = true } }
        engine.resetSwitches()
        XCTAssertTrue(graphChanged.withLock { $0 })
        XCTAssertTrue(previewChanged.withLock { $0 })
        try assertConfiguration(engine, edgeID: "to_barrier", angle: -.pi / 2, ending: .deadEnd, changes: 0)
    }

    func testRejectedTapsLeaveGraphPreviewsAndObservationUnchanged() throws {
        let engine = try pickALane()
        engine.tapSwitch(nodeID: "switch")
        let boardChanged = OSAllocatedUnfairLock(initialState: false)
        withObservationTracking {
            _ = engine.runtimeGraph
            _ = engine.previewRoutes
        } onChange: { boardChanged.withLock { $0 = true } }
        for id in ["red_start", "barrier", "missing"] {
            XCTAssertEqual(engine.tapSwitch(nodeID: id), .notASwitch)
        }
        engine.go()
        XCTAssertEqual(engine.tapSwitch(nodeID: "switch"), .rejectedFrozen)
        XCTAssertFalse(boardChanged.withLock { $0 })
        try assertConfiguration(engine, edgeID: "to_house", angle: 0, ending: .matchingHouse, changes: 1)
        engine.advance(by: 10)
        XCTAssertEqual(engine.phase, .finished)
        XCTAssertEqual(engine.tapSwitch(nodeID: "switch"), .rejectedFrozen)
        XCTAssertFalse(boardChanged.withLock { $0 })
        try assertConfiguration(engine, edgeID: "to_house", angle: 0, ending: .matchingHouse, changes: 1)
    }
}

final class MultiVanSimultaneousTests: XCTestCase {
    // Parallel straight roads keep distance thresholds exact. Merge roads meet at
    // (1, 0) and continue along the same edge, exercising transition leftovers.
    private func engine(
        delays: [Double] = [0, 0], spacing: Double = 1,
        merge: Bool = false, sharedStart: Bool = false,
        lengths: [Double] = [], wrongFirst: Bool = false, deadFirst: Bool = false,
        reverse: Bool = false, speed: Double = 1.5, crashDistance: Double = 0.35
    ) throws -> MultiVanEngine {
        let colors = ["red", "blue", "yellow", "green"]
        var nodes: [[String: Any]] = []
        var edges: [[String: Any]] = []
        var vans: [[String: Any]] = []
        var houses: [[String: Any]] = []
        for index in delays.indices {
            let y = Double(index) * spacing
            let start = sharedStart ? "s0" : "s\(index)"
            if !sharedStart || index == 0 {
                nodes.append(["id": "s\(index)", "x": 0, "y": y, "outgoingEdgeIDs": ["e\(index)"]])
                edges.append(["id": "e\(index)", "fromNodeID": "s\(index)", "toNodeID": merge ? "merge" : "h\(index)"])
            }
            vans.append(["id": "v\(index)", "color": sharedStart || merge ? "red" : colors[index],
                         "startNodeID": start, "departDelay": delays[index]])
            if !merge && (!sharedStart || index == 0) {
                nodes.append(["id": "h\(index)", "x": lengths.isEmpty ? 6 : lengths[index], "y": y, "outgoingEdgeIDs": []])
                if !(deadFirst && index == 0) {
                    houses.append(["nodeID": "h\(index)", "color": wrongFirst && index == 0 ? "blue" : colors[index]])
                }
            }
        }
        if merge {
            // Second approach has the same length as the first, arriving together.
            nodes[1]["x"] = 1
            nodes[1]["y"] = -1
            nodes.append(["id": "merge", "x": 1, "y": 0, "outgoingEdgeIDs": ["out"]])
            nodes.append(["id": "home", "x": 6, "y": 0, "outgoingEdgeIDs": []])
            edges.append(["id": "out", "fromNodeID": "merge", "toNodeID": "home"])
            houses.append(["nodeID": "home", "color": "red"])
        }
        if reverse { vans.reverse() }
        let json: [String: Any] = ["id": "mv20", "name": "MV20", "graph": ["nodes": nodes, "edges": edges],
                                   "vans": vans, "houses": houses, "initialSwitchEdges": [:], "parChanges": 0]
        let level = try JSONDecoder().decode(MultiVanLevel.self, from: JSONSerialization.data(withJSONObject: json))
        var tuning = MultiVanTuning.default
        tuning.vanSpeed = speed
        tuning.crashDistance = crashDistance
        return try MultiVanEngine(level: level, tuning: tuning)
    }

    func testTwoVansMoveOnTheirOwnRoadsSimultaneously() throws {
        let run = try engine()
        run.go(); run.advance(by: 0.5)
        XCTAssertEqual(run.vans.map(\.currentEdgeID), ["e0", "e1"])
        for (index, van) in run.vans.enumerated() {
            XCTAssertEqual(van.position.x, 0.75, accuracy: 1e-12)
            XCTAssertEqual(van.position.y, Double(index))
        }
        XCTAssertNil(run.outcome)
    }

    func testTwoVansDeliverAtDifferentTimesWithoutPrematureVictory() throws {
        let run = try engine(delays: [0, 1], lengths: [0.75, 1.5])
        run.go(); run.advance(by: 0.5)
        XCTAssertEqual(run.vans.map(\.status), [.parked, .waiting])
        XCTAssertNil(run.outcome)
        run.advance(by: 0.75)
        XCTAssertEqual(run.vans.map(\.status), [.parked, .driving])
        XCTAssertNil(run.outcome)
        run.advance(by: 1)
        XCTAssertEqual(run.vans.map(\.status), [.parked, .parked])
        XCTAssertEqual(run.outcome, .win)
    }

    func testZeroDelayDepartsAtGo() throws {
        let run = try engine(delays: [0, 1])
        run.go()
        XCTAssertEqual(run.vans.map(\.status), [.driving, .waiting])
        XCTAssertEqual(run.runTime, 0)
    }

    func testDelayedVanCannotMoveBeforeItsStepBoundary() throws {
        let run = try engine(delays: [0, 0.501])
        run.go(); run.advance(by: 61.0 / 120)
        XCTAssertEqual(run.vans[1].status, .waiting)
        XCTAssertEqual(run.vans[1].position, RoadPoint(x: 0, y: 1))
        run.advance(by: 1.0 / 120)
        XCTAssertEqual(run.vans[1].status, .driving)
        XCTAssertEqual(run.vans[1].distanceAlongEdge, 0.0125, accuracy: 1e-12)
    }

    func testDifferentDelaysProduceCorrectSpacing() throws {
        let run = try engine(delays: [0, 1], sharedStart: true)
        run.go(); run.advance(by: 2)
        XCTAssertEqual(run.vans[0].position.x - run.vans[1].position.x, 1.5, accuracy: 1e-12)
        XCTAssertNil(run.outcome)
    }

    func testStopResetsAllDepartureAndAccumulatorState() throws {
        let run = try engine(delays: [0, 1])
        run.go(); run.advance(by: 0.503); run.stop()
        XCTAssertEqual(run.runTime, 0)
        XCTAssertEqual(run.vans.map(\.status), [.waiting, .waiting])
        XCTAssertEqual(run.vans.map(\.distanceAlongEdge), [0, 0])
        XCTAssertTrue(run.vans.allSatisfy { $0.currentEdgeID == nil })
        run.go(); run.advance(by: 1)
        XCTAssertEqual(run.vans[1].status, .waiting)
        run.advance(by: 1.0 / 120)
        XCTAssertEqual(run.vans[1].distanceAlongEdge, 0.0125, accuracy: 1e-12)
    }

    func testRetryResetsDelaysAndRetainsCrashPointUntilGo() throws {
        let run = try engine(delays: [0.5, 0.5], sharedStart: true)
        run.go(); run.advance(by: 1)
        let point = try XCTUnwrap(run.lastFailPoint)
        let time = run.runTime
        run.retry()
        XCTAssertNil(run.outcome)
        XCTAssertEqual(run.lastFailPoint, point)
        XCTAssertEqual(run.runTime, 0)
        XCTAssertEqual(run.vans.map(\.position), [RoadPoint(x: 0, y: 0), RoadPoint(x: 0, y: 0)])
        run.go()
        XCTAssertNil(run.lastFailPoint)
        run.advance(by: 0.5)
        XCTAssertEqual(run.vans.map(\.status), [.waiting, .waiting])
        run.advance(by: 1)
        XCTAssertEqual(run.runTime, time)
        XCTAssertEqual(run.lastFailPoint, point)
    }

    func testMergeCrashIdentifiesVansAndMidpoint() throws {
        let run = try engine(merge: true)
        run.go(); run.advance(by: 2)
        let a = run.vans[0].position, b = run.vans[1].position
        let midpoint = RoadPoint(x: (a.x + b.x) / 2, y: (a.y + b.y) / 2)
        XCTAssertEqual(run.outcome, .failCrash(vanIDs: ["v0", "v1"], point: midpoint))
        XCTAssertEqual(run.lastFailPoint, midpoint)
        XCTAssertEqual(run.vans.map(\.status), [.crashed, .crashed])
        XCTAssertEqual(run.phase, .finished)
        XCTAssertTrue(run.runTime < 1)
    }

    func testOneSecondDepartureSpacingPreventsMergeCrashAndBothDeliver() throws {
        let run = try engine(delays: [0, 1], merge: true)
        run.go(); run.advance(by: 10)
        XCTAssertEqual(run.outcome, .win)
        XCTAssertEqual(run.vans.map(\.status), [.parked, .parked])
    }

    func testSharedStartDoesNotCrashWithWaitingVan() throws {
        let run = try engine(delays: [0, 1], sharedStart: true)
        run.go(); run.advance(by: 1.0 / 120)
        XCTAssertNil(run.outcome)
        XCTAssertEqual(run.vans.map(\.status), [.driving, .waiting])
        XCTAssertEqual(run.vans[1].position, RoadPoint(x: 0, y: 0))
        run.advance(by: 10)
        XCTAssertEqual(run.outcome, .win)
    }

    func testSimultaneouslyDrivingOverlappingVansCrash() throws {
        let run = try engine(sharedStart: true)
        run.go(); run.advance(by: 1.0 / 120)
        XCTAssertEqual(run.vans.map(\.status), [.crashed, .crashed])
        XCTAssertEqual(run.runTime, 1.0 / 120)
    }

    func testParkedVansAreExcludedEvenAtOverlappingDestination() throws {
        let run = try engine(delays: [0, 1], sharedStart: true, lengths: [0.75, 0.75])
        run.go(); run.advance(by: 3)
        XCTAssertEqual(run.outcome, .win)
        XCTAssertEqual(run.vans[0].position, run.vans[1].position)
    }

    func testDistanceBelowConfiguredThresholdCrashes() throws {
        let run = try engine(spacing: 0.499, crashDistance: 0.5)
        run.go(); run.advance(by: 1.0 / 120)
        XCTAssertEqual(run.vans.map(\.status), [.crashed, .crashed])
        XCTAssertEqual(run.lastFailPoint, RoadPoint(x: 0.0125, y: 0.2495))
    }

    func testExactThresholdDoesNotCrash() throws {
        for threshold in [0.35, 0.5] {
            let run = try engine(spacing: threshold, crashDistance: threshold)
            run.go(); run.advance(by: 1)
            XCTAssertNil(run.outcome)
            XCTAssertEqual(run.vans.map(\.status), [.driving, .driving])
        }
    }

    func testCrashFreezesAllStateIncludingClock() throws {
        let run = try engine(merge: true)
        run.go(); run.advance(by: 1)
        let positions = run.vans.map(\.position), time = run.runTime
        let outcome = run.outcome, point = run.lastFailPoint
        for delta in [0.01, 10, Double.infinity] { run.advance(by: delta) }
        XCTAssertEqual(run.vans.map(\.position), positions)
        XCTAssertEqual(run.runTime, time)
        XCTAssertEqual(run.outcome, outcome)
        XCTAssertEqual(run.lastFailPoint, point)
    }

    func testCrashIsIdenticalAcrossFramePartitionsAndRepeatedRuns() throws {
        let reference = try engine(merge: true)
        reference.go(); reference.advance(by: 2)
        for frames in [[2.0], Array(repeating: 1.0 / 60, count: 120), [0.003, 0.017, 0.31, 1.67]] {
            let run = try engine(merge: true)
            for _ in 0..<3 {
                run.go()
                for frame in frames { run.advance(by: frame) }
                XCTAssertEqual(run.outcome, reference.outcome)
                XCTAssertEqual(run.lastFailPoint, reference.lastFailPoint)
                XCTAssertEqual(run.runTime, reference.runTime)
                XCTAssertEqual(run.vans.map(\.position), reference.vans.map(\.position))
                run.retry()
            }
        }
    }

    func testFourOverlappingVansChooseFirstAuthoredPairAfterEveryoneMoves() throws {
        for reverse in [false, true] {
            let run = try engine(delays: [0, 0, 0, 0], sharedStart: true, reverse: reverse)
            run.go(); run.advance(by: 1.0 / 120)
            XCTAssertEqual(run.outcome, .failCrash(vanIDs: reverse ? ["v3", "v2"] : ["v0", "v1"], point: RoadPoint(x: 0.0125, y: 0)))
            XCTAssertEqual(run.vans.map(\.status), [.crashed, .crashed, .driving, .driving])
            XCTAssertTrue(run.vans.allSatisfy { abs($0.position.x - 0.0125) < 1e-12 })
        }
    }

    func testThreeVansFollowIndependentRoutesAndAllDeliver() throws {
        let run = try engine(delays: [0, 0.5, 1], lengths: [1.5, 3, 4.5])
        run.go(); run.advance(by: 0.75)
        XCTAssertEqual(run.vans.map(\.status), [.driving, .driving, .waiting])
        XCTAssertEqual(run.vans[0].distanceAlongEdge, 1.125, accuracy: 1e-12)
        XCTAssertEqual(run.vans[1].distanceAlongEdge, 0.375, accuracy: 1e-12)
        run.advance(by: 10)
        XCTAssertEqual(run.outcome, .win)
        XCTAssertEqual(run.runTime, 4, accuracy: 1e-12)
    }

    func testArrivalFailurePrecedesSameStepCrashAndAllVansAdvance() throws {
        for dead in [false, true] {
            let run = try engine(delays: [0, 0, 0], spacing: 0.1,
                                 lengths: [0.0125, 6, 6], wrongFirst: !dead, deadFirst: dead)
            run.go(); run.advance(by: 1)
            XCTAssertEqual(run.outcome, dead ? .failStuck(vanID: "v0", nodeID: "h0") : .failWrongHouse(vanID: "v0", houseNodeID: "h0"))
            XCTAssertEqual(run.vans[1].position.x, 0.0125, accuracy: 1e-12)
            XCTAssertEqual(run.vans[2].position.x, 0.0125, accuracy: 1e-12)
            XCTAssertEqual(run.vans[1].status, .driving)
            XCTAssertEqual(run.lastFailPoint, RoadPoint(x: 0.0125, y: 0))
        }
    }

    func testTerminalStepCompletesOtherDeliveriesAcrossVanOrderAndPartitions() throws {
        for reverse in [false, true] {
            for frames in [[1.0], [0.003, 0.997]] {
                let run = try engine(lengths: [0.0125, 0.0125], wrongFirst: true, deadFirst: true, reverse: reverse)
                // First van reaches a dead end; the other parks in this step.
                run.go()
                for frame in frames { run.advance(by: frame) }
                XCTAssertEqual(run.outcome, .failStuck(vanID: "v0", nodeID: "h0"))
                XCTAssertEqual(run.vans.first { $0.id == "v1" }?.status, .parked)
            }
        }
    }
}

final class MultiVanLiveSwitchTests: XCTestCase {
    /// Small shared-switch fixture; no authored level content is needed for MV-21.
    static func fixture(mutate: (inout [String: Any]) -> Void = { _ in }) throws -> MultiVanLevel {
        var json: [String: Any] = [
            "id": "mv21_fixture", "name": "Live split", "parChanges": 1,
            "liveSwitchNodeIDs": ["switch"], "initialSwitchEdges": ["switch": "red_exit"],
            "graph": [
                "nodes": [
                    ["id": "start", "x": -1, "y": 0, "outgoingEdgeIDs": ["approach"]],
                    ["id": "switch", "x": 0, "y": 0, "outgoingEdgeIDs": ["red_exit", "blue_exit"]],
                    ["id": "red_house", "x": 2, "y": 0, "outgoingEdgeIDs": []],
                    ["id": "blue_house", "x": 0, "y": 2, "outgoingEdgeIDs": []],
                    ["id": "normal", "x": 5, "y": 5, "outgoingEdgeIDs": ["normal_red", "normal_blue"]]
                ],
                // Storage order must not change cycling order.
                "edges": [
                    ["id": "blue_exit", "fromNodeID": "switch", "toNodeID": "blue_house"],
                    ["id": "red_exit", "fromNodeID": "switch", "toNodeID": "red_house"],
                    ["id": "approach", "fromNodeID": "start", "toNodeID": "switch"],
                    ["id": "normal_red", "fromNodeID": "normal", "toNodeID": "red_house"],
                    ["id": "normal_blue", "fromNodeID": "normal", "toNodeID": "blue_house"]
                ]
            ],
            "vans": [
                ["id": "red", "color": "red", "startNodeID": "start"],
                ["id": "blue", "color": "blue", "startNodeID": "start", "departDelay": 2]
            ],
            "houses": [["nodeID": "red_house", "color": "red"], ["nodeID": "blue_house", "color": "blue"]]
        ]
        mutate(&json)
        return try JSONDecoder().decode(MultiVanLevel.self, from: JSONSerialization.data(withJSONObject: json))
    }

    private func engine(at point: RoadPoint = RoadPoint(x: -1, y: 0), radius: Double = 0.4) throws -> MultiVanEngine {
        let level = try Self.fixture {
            var graph = $0["graph"] as! [String: Any]
            var nodes = graph["nodes"] as! [[String: Any]]
            nodes[0]["x"] = point.x
            nodes[0]["y"] = point.y
            graph["nodes"] = nodes
            $0["graph"] = graph
        }
        var tuning = MultiVanTuning.default
        tuning.liveSwitchLockRadius = radius
        return try MultiVanEngine(level: level, tuning: tuning)
    }

    private func assertRejected(_ engine: MultiVanEngine, node: String, result: MultiVanTapResult) {
        let edge = engine.runtimeGraph.nodesByID[node]?.activeOutgoingEdgeID
        let previews = engine.previewRoutes
        let count = engine.changeCount
        XCTAssertEqual(engine.tapSwitch(nodeID: node), result)
        XCTAssertEqual(engine.runtimeGraph.nodesByID[node]?.activeOutgoingEdgeID, edge)
        XCTAssertEqual(engine.previewRoutes, previews)
        XCTAssertEqual(engine.changeCount, count)
    }

    func testNormalFrozenLiveAcceptedAndConfigurationCountWrapsDuringRun() throws {
        let run = try engine()
        XCTAssertTrue(run.lockedSwitchNodeIDs.isEmpty)
        XCTAssertEqual(run.tapSwitch(nodeID: "normal"), .accepted)
        XCTAssertEqual(run.tapSwitch(nodeID: "normal"), .accepted)
        XCTAssertEqual(run.tapSwitch(nodeID: "switch"), .accepted)
        XCTAssertEqual(run.changeCount, 1)
        run.go()
        XCTAssertEqual(run.lockedSwitchNodeIDs, ["normal"])
        assertRejected(run, node: "normal", result: .rejectedFrozen)
        XCTAssertEqual(run.tapSwitch(nodeID: "switch"), .accepted)
        XCTAssertEqual(run.runtimeGraph.nodesByID["switch"]?.activeOutgoingEdgeID, "red_exit")
        XCTAssertEqual(run.changeCount, 0)
        XCTAssertEqual(run.previewRoutes[0].edgeIDs, ["approach", "red_exit"])
        XCTAssertEqual(run.tapSwitch(nodeID: "switch"), .accepted)
        XCTAssertEqual(run.previewRoutes[0].edgeIDs, ["approach", "blue_exit"])
        XCTAssertEqual(run.changeCount, 1)
        run.stop()
        XCTAssertTrue(run.lockedSwitchNodeIDs.isEmpty)
        XCTAssertEqual(run.changeCount, 1)
        run.resetSwitches()
        XCTAssertEqual(run.changeCount, 0)
    }

    func testInclusiveRadiusZeroAndEuclideanDistanceAtGo() throws {
        for (point, locked) in [
            (RoadPoint(x: -0.3, y: 0), true),
            (RoadPoint(x: -0.4, y: 0), true), // Exact default radius, no accumulated movement rounding.
            (RoadPoint(x: -0.400001, y: 0), false),
            (RoadPoint(x: 0, y: 0), true),
            (RoadPoint(x: -0.3, y: -0.3), false),
            (RoadPoint(x: -0.25, y: -0.25), true)
        ] {
            let run = try engine(at: point)
            run.go()
            XCTAssertEqual(run.vans[0].position, point)
            XCTAssertEqual(run.lockedSwitchNodeIDs.contains("switch"), locked)
            if locked { assertRejected(run, node: "switch", result: .rejectedLocked) }
            else { XCTAssertEqual(run.tapSwitch(nodeID: "switch"), .accepted) }
        }
        let custom = try engine(at: RoadPoint(x: -0.5, y: 0), radius: 0.6)
        custom.go()
        assertRejected(custom, node: "switch", result: .rejectedLocked)
    }

    func testLockUsesActualSwitchGridPosition() throws {
        let level = try Self.fixture {
            var graph = $0["graph"] as! [String: Any]
            var nodes = graph["nodes"] as! [[String: Any]]
            for index in nodes.indices {
                nodes[index]["x"] = (nodes[index]["x"] as! NSNumber).doubleValue + 10
                nodes[index]["y"] = (nodes[index]["y"] as! NSNumber).doubleValue + 7
            }
            nodes[0]["x"] = 9.75
            graph["nodes"] = nodes
            $0["graph"] = graph
        }
        let run = try MultiVanEngine(level: level)
        run.go()
        XCTAssertEqual(run.vans[0].position, RoadPoint(x: 9.75, y: 7))
        assertRejected(run, node: "switch", result: .rejectedLocked)
    }

    func testLocksTrackApproachArrivalAndDepartureEachStep() throws {
        let run = try engine()
        run.go()
        let lockChanged = OSAllocatedUnfairLock(initialState: false)
        withObservationTracking { _ = run.lockedSwitchNodeIDs } onChange: { lockChanged.withLock { $0 = true } }
        var sawApproach = false
        var sawDeparture = false
        for _ in 0..<120 {
            let van = run.vans[0]
            let distance = hypot(van.position.x, van.position.y)
            XCTAssertEqual(run.lockedSwitchNodeIDs.contains("switch"), distance <= run.tuning.liveSwitchLockRadius)
            if distance < 0.4 { sawApproach = true }
            if sawApproach && distance > 0.4 { sawDeparture = true }
            run.advance(by: run.tuning.stepDuration)
        }
        XCTAssertTrue(lockChanged.withLock { $0 })
        XCTAssertTrue(sawApproach)
        XCTAssertTrue(sawDeparture)
        XCTAssertFalse(run.lockedSwitchNodeIDs.contains("switch"))
    }

    func testWaitingAndParkedVansAtSwitchDoNotLockIt() throws {
        for parked in [false, true] {
            let level = try Self.fixture {
                $0["vans"] = [
                    ["id": "red", "color": "red", "startNodeID": "switch", "departDelay": parked ? 0 : 1],
                    ["id": "blue", "color": "blue", "startNodeID": "start", "departDelay": 2]
                ]
                if parked { $0["houses"] = [["nodeID": "switch", "color": "red"]] }
            }
            let run = try MultiVanEngine(level: level)
            run.go()
            XCTAssertEqual(run.phase, .run)
            XCTAssertEqual(run.vans[0].position, RoadPoint(x: 0, y: 0))
            XCTAssertEqual(run.vans[0].status, parked ? .parked : .waiting)
            XCTAssertEqual(run.lockedSwitchNodeIDs, ["normal"])
            XCTAssertTrue(MultiVanSwitchAppearance(engine: run, nodeID: "switch").isAvailable)
            XCTAssertEqual(run.tapSwitch(nodeID: "switch"), .accepted)
        }
    }

    func testStuckVanOnZeroLengthCycleDoesNotLockSwitch() throws {
        let level = try Self.fixture {
            $0["vans"] = [["id": "red", "color": "red", "startNodeID": "switch"]]
            var graph = $0["graph"] as! [String: Any]
            var edges = graph["edges"] as! [[String: Any]]
            edges[1]["toNodeID"] = "switch"
            graph["edges"] = edges
            $0["graph"] = graph
        }
        let run = try MultiVanEngine(level: level)
        run.go()
        XCTAssertTrue(run.lockedSwitchNodeIDs.contains("switch"))
        run.advance(by: run.tuning.stepDuration)
        XCTAssertEqual(run.vans[0].status, .stuck)
        XCTAssertEqual(run.phase, .run)
        XCTAssertEqual(run.lockedSwitchNodeIDs, ["normal"])
        XCTAssertEqual(run.tapSwitch(nodeID: "switch"), .accepted)
    }

    func testFirstVanKeepsOriginalEdgeSecondTakesChangedExitAndBothWin() throws {
        let run = try engine()
        run.go()
        run.advance(by: 1)
        XCTAssertEqual(run.vans[0].currentEdgeID, "red_exit")
        let position = run.vans[0].position
        XCTAssertEqual(run.tapSwitch(nodeID: "switch"), .accepted)
        XCTAssertEqual(run.vans[0].currentEdgeID, "red_exit")
        XCTAssertEqual(run.vans[0].position, position)
        run.advance(by: 2)
        XCTAssertEqual(run.vans[0].status, .parked)
        XCTAssertEqual(run.vans[1].currentEdgeID, "blue_exit")
        run.advance(by: 2)
        XCTAssertEqual(run.outcome, .win)
        XCTAssertEqual(run.vans.map(\.status), [.parked, .parked])
        XCTAssertEqual(run.changeCount, 1)
        XCTAssertTrue(run.lockedSwitchNodeIDs.isEmpty)
        assertRejected(run, node: "switch", result: .rejectedFrozen)
        assertRejected(run, node: "normal", result: .rejectedFrozen)
        run.retry()
        XCTAssertTrue(run.lockedSwitchNodeIDs.isEmpty)
        XCTAssertEqual(run.changeCount, 1)
        XCTAssertEqual(run.runtimeGraph.nodesByID["switch"]?.activeOutgoingEdgeID, "blue_exit")
        run.go()
        XCTAssertEqual(run.lockedSwitchNodeIDs, ["normal"])
    }

    func testEquivalentTimedInputsAcrossFramePartitionsAreIdentical() throws {
        var reference: MultiVanEngine?
        for frames in [[1.0], Array(repeating: 1.0 / 60, count: 60), [0.003, 0.017, 0.31, 0.67]] {
            let run = try engine()
            run.go()
            for frame in frames { run.advance(by: frame) }
            XCTAssertEqual(run.runTime, 1)
            XCTAssertEqual(run.tapSwitch(nodeID: "switch"), .accepted)
            for _ in 0..<4 { for frame in frames { run.advance(by: frame) } }
            XCTAssertEqual(run.outcome, .win)
            if let reference {
                XCTAssertEqual(run.outcome, reference.outcome)
                XCTAssertEqual(run.runTime, reference.runTime)
                XCTAssertEqual(run.vans.map(\.position), reference.vans.map(\.position))
                XCTAssertEqual(run.vans.map(\.currentEdgeID), reference.vans.map(\.currentEdgeID))
                XCTAssertEqual(run.previewRoutes, reference.previewRoutes)
                XCTAssertEqual(run.changeCount, reference.changeCount)
                XCTAssertEqual(run.lockedSwitchNodeIDs, reference.lockedSwitchNodeIDs)
            }
            reference = run
        }
    }

    func testLiveTapPublishesGraphPreviewAndCountAndRejectedTapPublishesNothing() throws {
        let run = try engine()
        run.go()
        let changed = OSAllocatedUnfairLock(initialState: Set<String>())
        withObservationTracking { _ = run.runtimeGraph } onChange: { changed.withLock { _ = $0.insert("graph") } }
        withObservationTracking { _ = run.previewRoutes } onChange: { changed.withLock { _ = $0.insert("preview") } }
        withObservationTracking { _ = run.changeCount } onChange: { changed.withLock { _ = $0.insert("count") } }
        XCTAssertEqual(run.tapSwitch(nodeID: "switch"), .accepted)
        XCTAssertEqual(changed.withLock { $0 }, ["graph", "preview", "count"])
        run.advance(by: 0.5)
        changed.withLock { $0 = [] }
        withObservationTracking {
            _ = run.runtimeGraph
            _ = run.previewRoutes
            _ = run.changeCount
        } onChange: { changed.withLock { _ = $0.insert("rejected") } }
        assertRejected(run, node: "switch", result: .rejectedLocked)
        XCTAssertTrue(changed.withLock { $0.isEmpty })
    }
}

// MV-31: feedback is an ordered, explicitly drained record of engine actions.
extension MultiVanLiveSwitchTests {
    func testAcceptedAndRejectedTapEventsPreserveOrderAndConfiguration() throws {
        let run = try engine()
        XCTAssertEqual(run.tapSwitch(nodeID: "switch"), .accepted)
        XCTAssertEqual(run.tapSwitch(nodeID: "switch"), .accepted)
        run.go()
        let count = run.changeCount
        assertRejected(run, node: "normal", result: .rejectedFrozen)
        run.advance(by: 0.5)
        assertRejected(run, node: "switch", result: .rejectedLocked)
        XCTAssertEqual(run.changeCount, count)
        XCTAssertEqual(run.drainEvents(), [.switchTapped, .switchTapped, .go,
                                          .tapRejected(nodeID: "normal"), .tapRejected(nodeID: "switch")])
        XCTAssertEqual(run.drainEvents(), [])
    }

    func testQueueReadsAndRejectedTapsDoNotPublishGameplayChanges() throws {
        let run = try engine()
        run.go()
        let changed = OSAllocatedUnfairLock(initialState: false)
        withObservationTracking {
            _ = run.drainEvents()
            _ = run.phase
            _ = run.runtimeGraph
            _ = run.changeCount
            _ = run.vans
        } onChange: { changed.withLock { $0 = true } }
        run.tapSwitch(nodeID: "normal")
        XCTAssertFalse(changed.withLock { $0 })
        XCTAssertEqual(run.drainEvents(), [.tapRejected(nodeID: "normal")])
        XCTAssertFalse(changed.withLock { $0 })
    }

    func testEquivalentTimedLiveInputsProduceIdenticalEventSequences() throws {
        var reference: [MultiVanEvent]?
        for frames in [[1.0], Array(repeating: 1.0 / 60, count: 60), [0.003, 0.017, 0.31, 0.67]] {
            let run = try engine()
            run.go()
            var events = run.drainEvents()
            for frame in frames { run.advance(by: frame); events += run.drainEvents() }
            run.tapSwitch(nodeID: "switch")
            events += run.drainEvents()
            for _ in 0..<4 {
                for frame in frames { run.advance(by: frame); events += run.drainEvents() }
            }
            XCTAssertEqual(events, [.go, .switchTapped, .delivered(vanID: "red", comboIndex: 1),
                                    .delivered(vanID: "blue", comboIndex: 2), .allDelivered])
            if let reference { XCTAssertEqual(events, reference) }
            reference = events
        }
    }
}

extension MultiVanOutcomeTests {
    func testDeliveryAndVictoryEventsDrainOnceInOrder() throws {
        let run = try makeEngine()
        run.go()
        run.go()
        XCTAssertEqual(run.drainEvents(), [.go])
        run.advance(by: 1)
        XCTAssertEqual(run.drainEvents(), [.delivered(vanID: "first", comboIndex: 1), .allDelivered])
        for _ in 0..<3 { run.go(); run.stop(); run.advance(by: 10) }
        XCTAssertEqual(run.drainEvents(), [])
    }

    func testInvalidPhaseActionsAndNonSwitchesEmitNothing() throws {
        let run = try makeEngine()
        run.stop()
        run.retry()
        run.advance(by: 1)
        XCTAssertEqual(run.tapSwitch(nodeID: "start"), .notASwitch)
        XCTAssertEqual(run.tapSwitch(nodeID: "missing"), .notASwitch)
        XCTAssertEqual(run.drainEvents(), [])
        run.go()
        _ = run.drainEvents()
        run.retry()
        run.go()
        XCTAssertEqual(run.drainEvents(), [])
    }

    func testWrongHouseAndStuckDoNotEmitDeliveryOrVictory() throws {
        for color: String? in ["blue", nil] {
            let run = try makeEngine(houseColor: color)
            run.go()
            run.advance(by: 10)
            XCTAssertEqual(run.drainEvents(), color == nil ? [.go] : [.go, .wrongHouse(vanID: "first")])
            run.advance(by: 10)
            XCTAssertEqual(run.drainEvents(), [])
        }
    }

    func testTerminalStartEventsFollowGoIncludingImmediateVictory() throws {
        for color in ["red", "blue"] {
            let run = try makeEngine(houseColor: color, startAtDestination: true)
            run.go()
            XCTAssertEqual(run.drainEvents(), color == "red"
                           ? [.go, .delivered(vanID: "first", comboIndex: 1), .allDelivered]
                           : [.go, .wrongHouse(vanID: "first")])
            run.go()
            XCTAssertEqual(run.drainEvents(), [])
        }
    }

    func testStopAndRetryRestartComboWithoutDiscardingPendingEvents() throws {
        let run = try makeEngine(secondDelay: 10)
        run.go()
        run.advance(by: 0.25)
        run.stop()
        run.go()
        run.advance(by: 20)
        XCTAssertEqual(run.drainEvents(), [.go, .delivered(vanID: "first", comboIndex: 1),
                                          .go, .delivered(vanID: "first", comboIndex: 1),
                                          .delivered(vanID: "second", comboIndex: 2), .allDelivered])
        run.retry()
        XCTAssertEqual(run.drainEvents(), [])
        run.go()
        run.advance(by: 20)
        run.retry() // An undrained run remains available until explicitly consumed.
        XCTAssertEqual(run.drainEvents(), [.go, .delivered(vanID: "first", comboIndex: 1),
                                          .delivered(vanID: "second", comboIndex: 2), .allDelivered])
        XCTAssertEqual(run.drainEvents(), [])
    }

    func testRetryDoesNotReplayDrainedFailureEvents() throws {
        let run = try makeEngine(houseColor: "blue")
        for _ in 0..<2 {
            run.go()
            run.advance(by: 10)
            XCTAssertEqual(run.drainEvents(), [.go, .wrongHouse(vanID: "first")])
            run.retry()
            XCTAssertEqual(run.drainEvents(), [])
        }
    }
}

extension MultiVanSimultaneousTests {
    func testSimultaneousDeliveryEventsUseAuthoredOrder() throws {
        for reverse in [false, true] {
            let run = try engine(delays: [0, 0, 0, 0], reverse: reverse)
            run.go()
            run.advance(by: 10)
            let ids = reverse ? ["v3", "v2", "v1", "v0"] : ["v0", "v1", "v2", "v3"]
            XCTAssertEqual(run.drainEvents(), [.go] + ids.enumerated().map {
                .delivered(vanID: $0.element, comboIndex: $0.offset + 1)
            } + [.allDelivered])
        }
    }

    func testStaggeredDeliveriesCountInArrivalOrder() throws {
        let run = try engine(delays: [1, 0], lengths: [1.5, 1.5])
        run.go()
        run.advance(by: 10)
        XCTAssertEqual(run.drainEvents(), [.go, .delivered(vanID: "v1", comboIndex: 1),
                                          .delivered(vanID: "v0", comboIndex: 2), .allDelivered])
    }

    func testCrashEventUsesAuthoritativeMidpointAndEmitsOnce() throws {
        let run = try engine(merge: true)
        for _ in 0..<2 {
            run.go()
            run.advance(by: 10)
            let a = run.vans[0].position, b = run.vans[1].position
            let point = RoadPoint(x: (a.x + b.x) / 2, y: (a.y + b.y) / 2)
            XCTAssertEqual(run.lastFailPoint, point)
            XCTAssertEqual(run.drainEvents(), [.go, .crashed(point: point)])
            run.go(); run.advance(by: 10)
            XCTAssertEqual(run.drainEvents(), [])
            run.retry()
            XCTAssertEqual(run.drainEvents(), [])
        }
    }

    func testArrivalFailureSuppressesSameStepCrashEvent() throws {
        for dead in [false, true] {
            let run = try engine(delays: [0, 0, 0], spacing: 0.1,
                                 lengths: [0.0125, 6, 6], wrongFirst: !dead, deadFirst: dead)
            run.go()
            run.advance(by: 1)
            XCTAssertEqual(run.drainEvents(), dead ? [.go] : [.go, .wrongHouse(vanID: "v0")])
        }
    }

    func testOnlyAuthoritativeSimultaneousWrongHouseEmits() throws {
        let level = try MultiVanLiveSwitchTests.fixture {
            $0["vans"] = [
                ["id": "first", "color": "blue", "startNodeID": "red_house"],
                ["id": "second", "color": "red", "startNodeID": "blue_house"]
            ]
        }
        let run = try MultiVanEngine(level: level)
        run.go()
        XCTAssertEqual(run.drainEvents(), [.go, .wrongHouse(vanID: "first")])
    }

    func testTerminalStepDeliveryPrecedesSelectedFailureWithoutVictory() throws {
        for reverse in [false, true] {
            let run = try engine(lengths: [0.0125, 0.0125], wrongFirst: true, reverse: reverse)
            run.go()
            run.advance(by: 1)
            XCTAssertEqual(run.drainEvents(), [.go, .delivered(vanID: "v1", comboIndex: 1), .wrongHouse(vanID: "v0")])
        }
    }

    func testSuccessCrashAndWrongHouseEventsAreFramePartitionIndependent() throws {
        for scenario in 0..<3 {
            var reference: [MultiVanEvent]?
            for frames in [[10.0], Array(repeating: 1.0 / 60, count: 600), [0.003, 0.017, 0.31, 9.67]] {
                let run = try engine(merge: scenario == 1, wrongFirst: scenario == 2)
                run.go()
                var events = run.drainEvents()
                for frame in frames { run.advance(by: frame); events += run.drainEvents() }
                if let reference { XCTAssertEqual(events, reference) }
                reference = events
            }
        }
    }
}

extension MultiVanSimultaneousTests {
    func testPersonalityIdleEligibilityAndDelayedDeparture() throws {
        for status in [MultiVanVanState.Status.waiting, .parked] {
            XCTAssertTrue(MultiVanPersonality.isIdle(status: status, reduceMotion: false))
            XCTAssertFalse(MultiVanPersonality.isIdle(status: status, reduceMotion: true))
        }
        for status in [MultiVanVanState.Status.driving, .crashed, .stuck] {
            XCTAssertFalse(MultiVanPersonality.isIdle(status: status, reduceMotion: false))
        }
        let run = try engine(delays: [0, 1])
        var personality = MultiVanPersonality()
        run.go()
        for event in run.drainEvents() { personality.process(event, engine: run, reduceMotion: false) }
        func active(_ index: Int) -> MultiVanPersonality.Reaction? {
            let van = run.vans[index]
            return MultiVanPersonality.activeReaction(
                personality.reactions[van.id], status: van.status, reduceMotion: false
            )
        }
        XCTAssertEqual(active(0)?.kind, .departure)
        XCTAssertNil(active(1), "GO must not lean a delayed van before it departs")
        let delayedToken = personality.reactions["v1"]
        run.advance(by: 1)
        XCTAssertNil(active(1))
        run.advance(by: run.tuning.stepDuration)
        XCTAssertEqual(active(1), delayedToken, "The existing engine status starts the armed reaction")
        XCTAssertFalse(MultiVanPersonality.isIdle(status: run.vans[1].status, reduceMotion: false))
    }

    func testPersonalityDeliveryTargetsAndIndependentSimultaneousHops() throws {
        let run = try engine(delays: [0, 1], lengths: [0.75, 1.5])
        var personality = MultiVanPersonality()
        run.go()
        for event in run.drainEvents() { personality.process(event, engine: run, reduceMotion: false) }
        let other = personality.reactions["v1"]
        run.advance(by: 0.5)
        for event in run.drainEvents() { personality.process(event, engine: run, reduceMotion: false) }
        XCTAssertEqual(personality.reactions["v0"]?.kind, .delivery)
        XCTAssertEqual(personality.reactions["v1"], other)
        XCTAssertTrue(MultiVanPersonality.isIdle(status: run.vans[0].status, reduceMotion: false))

        let simultaneous = try engine(delays: [0, 0, 0, 0])
        personality.reset()
        simultaneous.go()
        simultaneous.advance(by: 10)
        for event in simultaneous.drainEvents() {
            personality.process(event, engine: simultaneous, reduceMotion: false)
        }
        XCTAssertEqual(personality.reactions.count, 4)
        XCTAssertTrue(personality.reactions.values.allSatisfy { $0.kind == .delivery })
        XCTAssertEqual(Set(personality.reactions.values.map(\.token)).count, 4)
        let tokens = personality.reactions
        for event in simultaneous.drainEvents() {
            personality.process(event, engine: simultaneous, reduceMotion: false)
        }
        XCTAssertEqual(personality.reactions, tokens, "Redraws/empty drains cannot replay hops")
    }

    func testPersonalityCrashUsesOnlyOutcomePairAndDoesNotReplay() throws {
        let run = try engine(delays: [0, 0, 0, 0], sharedStart: true)
        var personality = MultiVanPersonality()
        run.go()
        for event in run.drainEvents() { personality.process(event, engine: run, reduceMotion: false) }
        let uninvolved = [personality.reactions["v2"], personality.reactions["v3"]]
        run.advance(by: run.tuning.stepDuration)
        let events = run.drainEvents()
        for event in events { personality.process(event, engine: run, reduceMotion: false) }
        XCTAssertEqual(personality.reactions.filter { $0.value.kind == .crash }.map(\.key).sorted(), ["v0", "v1"])
        XCTAssertEqual([personality.reactions["v2"], personality.reactions["v3"]], uninvolved)
        let tokens = personality.reactions
        for event in events { personality.process(event, engine: run, reduceMotion: false) }
        XCTAssertEqual(personality.reactions, tokens, "A failure spins each affected van once")
    }

    func testPersonalityResetAndReducedMotionLeaveNoStaleReactions() throws {
        let run = try engine()
        var personality = MultiVanPersonality()
        run.go()
        for event in run.drainEvents() { personality.process(event, engine: run, reduceMotion: false) }
        let first = personality.reactions["v0"]
        run.stop()
        personality.reset() // Same reset used by Stop, Retry, level changes and disappearance.
        XCTAssertTrue(personality.reactions.isEmpty)
        run.go()
        for event in run.drainEvents() { personality.process(event, engine: run, reduceMotion: false) }
        XCTAssertNotEqual(personality.reactions["v0"], first)
        run.advance(by: 10)
        let deliveries = run.drainEvents()
        for event in deliveries { personality.process(event, engine: run, reduceMotion: false) }
        run.retry()
        personality.reset()
        XCTAssertTrue(personality.reactions.isEmpty)
        let nextLevel = try engine(delays: [0, 1, 2])
        XCTAssertTrue(nextLevel.vans.allSatisfy { personality.reactions[$0.id] == nil })

        for event in [.go, .crashed(point: RoadPoint(x: 0, y: 0))] + deliveries {
            personality.process(event, engine: run, reduceMotion: true)
        }
        XCTAssertTrue(personality.reactions.isEmpty)
        for kind in [MultiVanPersonality.Reaction.Kind.departure, .delivery, .crash] {
            XCTAssertNil(MultiVanPersonality.activeReaction(
                .init(kind: kind), status: .driving, reduceMotion: true
            ))
        }
        // Turning motion off invalidates an in-flight token; turning it back on
        // does not recreate a hop, lean or spin from old gameplay state.
        personality.process(.delivered(vanID: "v0", comboIndex: 1), engine: run, reduceMotion: false)
        personality.reset()
        XCTAssertNil(MultiVanPersonality.activeReaction(
            personality.reactions["v0"], status: .parked, reduceMotion: false
        ))
    }

    @MainActor
    func testPersonalitySharesDispatcherAndPreservesDeliveryEffectsAndDeterminism() throws {
        for merge in [false, true] {
            let reference = try engine(merge: merge)
            reference.go()
            reference.advance(by: 10)
            let expectedEvents = reference.drainEvents()
            for reduced in [false, true] {
                let run = try engine(merge: merge)
                var personality = MultiVanPersonality()
                var celebration = MultiVanCelebration()
                var crashEffects = MultiVanCrashEffects()
                let sound = MultiVanSoundPlayer(resourceURL: { _ in nil }, configureSession: {}, activateSession: {})
                var settings = UserSettings()
                settings.reducesExtraAnimations = reduced
                var drains = 0
                var dispatched: [MultiVanEvent] = []
                var haptics: [MultiVanHaptic] = []
                var crashReactions = 0
                func dispatch() {
                    MultiVanFeedback.process(drainEvents: {
                        drains += 1
                        return run.drainEvents()
                    }, settings: settings, soundPlayer: sound, playHaptic: { haptics.append($0) },
                    reactVisually: { event in
                        dispatched.append(event)
                        personality.process(event, engine: run, reduceMotion: reduced)
                        celebration.process(event, engine: run, reduceMotion: reduced)
                        let previousImpact = crashEffects.impact?.id
                        crashEffects.process(event, reduceMotion: reduced)
                        if crashEffects.impact?.id != previousImpact { crashReactions += 1 }
                    })
                }
                run.go()
                dispatch()
                for _ in 0..<600 {
                    run.advance(by: 1.0 / 60)
                    let positions = run.vans.map(\.position)
                    let headings = run.vans.map {
                        MultiVanVanView.heading(for: $0, startNodeID: nil, graph: run.runtimeGraph).radians
                    }
                    dispatch()
                    XCTAssertEqual(run.vans.map(\.position), positions)
                    XCTAssertEqual(run.vans.map {
                        MultiVanVanView.heading(for: $0, startNodeID: nil, graph: run.runtimeGraph).radians
                    }, headings)
                }
                XCTAssertEqual(drains, 601)
                XCTAssertEqual(dispatched, expectedEvents)
                XCTAssertEqual(haptics, dispatched.compactMap { MultiVanHaptic.feedback(for: $0) })
                XCTAssertEqual(run.outcome, reference.outcome)
                XCTAssertEqual(run.runTime, reference.runTime)
                XCTAssertEqual(run.vans.map(\.position), reference.vans.map(\.position))
                XCTAssertEqual(crashReactions, merge && !reduced ? 1 : 0)
                XCTAssertEqual(personality.reactions.values.filter { $0.kind == .crash }.count,
                               merge && !reduced ? 2 : 0)
                if reduced || merge {
                    XCTAssertTrue(celebration.deliveries.isEmpty)
                } else {
                    XCTAssertEqual(celebration.deliveries.count, 2)
                    XCTAssertEqual(celebration.houseTokens.count, 2)
                    XCTAssertNotNil(celebration.confettiID)
                }
                if reduced { XCTAssertTrue(personality.reactions.isEmpty) }
            }
        }
    }

    @MainActor
    func testMV38AcceleratedFrameDispatchesEveryDeliveryAndTerminalEventOnce() throws {
        for reduced in [false, true] {
            let run = try engine(lengths: [0.3, 0.6])
            let driver = MultiVanFrameDriver()
            var celebration = MultiVanCelebration()
            var personality = MultiVanPersonality()
            var dispatched: [MultiVanEvent] = []
            var haptics: [MultiVanHaptic] = []
            var drains = 0
            let sound = MultiVanSoundPlayer(resourceURL: { _ in nil }, configureSession: {}, activateSession: {})
            func dispatch() {
                MultiVanFeedback.process(drainEvents: {
                    drains += 1
                    return run.drainEvents()
                }, settings: UserSettings(), soundPlayer: sound,
                playHaptic: { haptics.append($0) }, reactVisually: { event in
                    dispatched.append(event)
                    celebration.process(event, engine: run, reduceMotion: reduced)
                    personality.process(event, engine: run, reduceMotion: reduced)
                })
            }
            run.go()
            dispatch()
            driver.advance(at: Date(timeIntervalSinceReferenceDate: 0), engine: run, isActive: true)
            driver.setFastForwarding(true, at: Date(timeIntervalSinceReferenceDate: 0), engine: run, isActive: true)
            // One visual frame crosses two distinct delivery steps and victory.
            driver.advance(at: Date(timeIntervalSinceReferenceDate: 0.25), engine: run, isActive: true)
            dispatch()
            XCTAssertEqual(drains, 2)
            XCTAssertEqual(dispatched, [.go, .delivered(vanID: "v0", comboIndex: 1),
                                        .delivered(vanID: "v1", comboIndex: 2), .allDelivered])
            XCTAssertEqual(haptics, [.mediumImpact, .success, .success, .success])
            XCTAssertEqual(run.outcome, .win)
            XCTAssertFalse(driver.isFastForwarding)
            XCTAssertTrue(run.drainEvents().isEmpty)
            XCTAssertEqual(celebration.deliveries.map(\.label), reduced ? [] : ["+1", "+1  ×2"])
            XCTAssertEqual(celebration.confettiID != nil, !reduced)
            XCTAssertEqual(personality.reactions.values.filter { $0.kind == .delivery }.count, reduced ? 0 : 2)
        }
    }

    @MainActor
    func testDeliveryPayoffKeepsEverySameStepDeliveryInEngineOrder() throws {
        for reverse in [false, true] {
            let run = try engine(delays: [0, 0, 0, 0], reverse: reverse)
            var celebration = MultiVanCelebration()
            run.go()
            run.advance(by: 10)
            let outcome = run.outcome
            let stars = MultiVanStars.rating(changes: run.changeCount, par: run.level.parChanges)
            for event in run.drainEvents() {
                celebration.process(event, engine: run, reduceMotion: false)
            }
            let ids = reverse ? [3, 2, 1, 0] : [0, 1, 2, 3]
            XCTAssertEqual(celebration.deliveries.map(\.houseNodeID), ids.map { "h\($0)" })
            XCTAssertEqual(celebration.deliveries.map(\.label), ["+1", "+1  ×2", "+1  ×3", "+1  ×4"])
            XCTAssertEqual(Set(celebration.deliveries.map(\.id)).count, 4)
            for delivery in celebration.deliveries {
                XCTAssertEqual(celebration.houseTokens[delivery.houseNodeID], delivery.id)
            }
            let confettiID = try XCTUnwrap(celebration.confettiID)
            celebration.process(.allDelivered, engine: run, reduceMotion: false)
            XCTAssertEqual(celebration.confettiID, confettiID)
            XCTAssertEqual(celebration.deliveries.count, 4, "Victory preserves the final popup")
            let first = celebration.deliveries[0]
            celebration.complete(first.id)
            XCTAssertEqual(celebration.deliveries.count, 3)
            XCTAssertEqual(celebration.houseTokens[first.houseNodeID], first.id,
                           "Cleanup must not retrigger the house")
            XCTAssertEqual(run.outcome, outcome)
            XCTAssertEqual(MultiVanStars.rating(changes: run.changeCount, par: run.level.parChanges), stars)
            XCTAssertTrue(run.drainEvents().isEmpty)

            run.retry()
            celebration.reset()
            XCTAssertTrue(celebration.deliveries.isEmpty)
            XCTAssertTrue(celebration.houseTokens.isEmpty)
            XCTAssertNil(celebration.confettiID)
            celebration.complete(first.id) // An obsolete completion cannot affect a new run.
            run.go()
            run.advance(by: 10)
            for event in run.drainEvents() {
                celebration.process(event, engine: run, reduceMotion: false)
            }
            XCTAssertEqual(celebration.deliveries.count, 4)
            XCTAssertNotEqual(celebration.confettiID, confettiID)
        }
    }

    @MainActor
    func testFailedRunsNeverCelebrateVictoryOrWrongHouseArrival() throws {
        for run in [try engine(wrongFirst: true), try engine(deadFirst: true), try engine(merge: true)] {
            var celebration = MultiVanCelebration()
            run.go()
            run.advance(by: 10)
            for event in run.drainEvents() {
                celebration.process(event, engine: run, reduceMotion: false)
            }
            XCTAssertNotEqual(run.outcome, .win)
            XCTAssertNil(celebration.confettiID)
            XCTAssertFalse(celebration.deliveries.contains { $0.houseNodeID == "h0" })
            celebration.process(.allDelivered, engine: run, reduceMotion: false)
            XCTAssertNil(celebration.confettiID)
        }
    }

    @MainActor
    func testReducedMotionAndLifecycleClearExtraDeliveryEffects() throws {
        let run = try engine(delays: [0, 0, 0, 0])
        run.go()
        run.advance(by: 10)
        let events = run.drainEvents()
        var celebration = MultiVanCelebration()
        for event in events { celebration.process(event, engine: run, reduceMotion: true) }
        XCTAssertTrue(celebration.deliveries.isEmpty)
        XCTAssertTrue(celebration.houseTokens.isEmpty)
        XCTAssertNil(celebration.confettiID)
        for house in run.level.houses {
            XCTAssertTrue(MultiVanBoardView.isDelivered(house, vans: run.vans, graph: run.runtimeGraph))
        }
        celebration.process(.allDelivered, engine: run, reduceMotion: false)
        XCTAssertNil(celebration.confettiID, "Changing settings must not replay victory")
        celebration.reset()
        for event in events { celebration.process(event, engine: run, reduceMotion: false) }
        XCTAssertEqual(celebration.deliveries.count, 4)
        celebration.suppressMotion()
        XCTAssertTrue(celebration.deliveries.isEmpty)
        XCTAssertTrue(celebration.houseTokens.isEmpty)
        XCTAssertNil(celebration.confettiID)
        celebration.process(.allDelivered, engine: run, reduceMotion: false)
        XCTAssertNil(celebration.confettiID)
        celebration.reset() // Same cleanup used by Stop, Retry, level changes and disappearance.
        XCTAssertTrue(celebration.deliveries.isEmpty)
    }
}

// MV-36: presentation tokens are independent of engine positions and outcomes.
extension MultiVanSimultaneousTests {
    func testCrashEffectUsesEventPointAndShakeSettlesBeforeFailureCard() throws {
        let run = try engine(merge: true)
        var effects = MultiVanCrashEffects()
        run.go()
        run.advance(by: 10)
        guard case let .failCrash(_, point) = run.outcome else { return XCTFail("Expected crash") }
        let positions = run.vans.map(\.position)
        for event in run.drainEvents() { effects.process(event, reduceMotion: false) }
        XCTAssertEqual(try XCTUnwrap(effects.impact).point, point)
        XCTAssertEqual(MultiVanCrashEffects.shakeOffset(progress: 0), 0)
        XCTAssertGreaterThan(MultiVanCrashEffects.shakeOffset(progress: 1.0 / 12), 3)
        XCTAssertLessThan(MultiVanCrashEffects.shakeOffset(progress: 3.0 / 12), 0)
        XCTAssertEqual(MultiVanCrashEffects.shakeOffset(progress: 1), 0)
        XCTAssertEqual(MultiVanCrashEffects.shakeOffset(progress: 2), 0)
        for sample in 0...100 {
            XCTAssertLessThanOrEqual(abs(MultiVanCrashEffects.shakeOffset(progress: Double(sample) / 100)), 4)
        }
        XCTAssertLessThanOrEqual(MultiVanCrashEffects.shakeDuration, 0.35)
        XCTAssertLessThanOrEqual(MultiVanCrashEffects.impactDuration, 0.5)
        XCTAssertEqual(run.tuning.failFreezeDuration, 0.6)
        XCTAssertLessThan(MultiVanCrashEffects.impactDuration, run.tuning.failFreezeDuration)
        for size in [CGSize(width: 280, height: 340), CGSize(width: 430, height: 680)] {
            let layout = MultiVanBoardView.boardLayout(level: run.level, size: size)
            XCTAssertEqual(layout.point(for: try XCTUnwrap(effects.impact).point), layout.point(for: point))
        }
        effects.complete(try XCTUnwrap(effects.impact).id)
        XCTAssertNil(effects.impact)
        XCTAssertEqual(run.vans.map(\.position), positions)
    }

    func testWrongHouseAndStuckFailuresHaveNoCrashEffects() throws {
        for run in [try engine(wrongFirst: true), try engine(deadFirst: true)] {
            var effects = MultiVanCrashEffects()
            run.go()
            run.advance(by: 10)
            XCTAssertNotNil(run.outcome)
            for event in run.drainEvents() { effects.process(event, reduceMotion: false) }
            XCTAssertNil(effects.impact)
        }
    }

    func testCrashEffectResetRetryAndNewRunRejectStaleCompletion() throws {
        let run = try engine(merge: true)
        var effects = MultiVanCrashEffects()
        func crash() {
            run.go()
            run.advance(by: 10)
            for event in run.drainEvents() { effects.process(event, reduceMotion: false) }
        }
        crash()
        let first = try XCTUnwrap(effects.impact)
        run.retry()
        effects.reset() // Shared by Retry/Replay, Stop, level replacement and dismissal.
        XCTAssertNil(effects.impact)
        XCTAssertEqual(run.lastFailPoint, first.point, "The static retry indicator is retained")
        crash()
        let next = try XCTUnwrap(effects.impact)
        XCTAssertNotEqual(next.id, first.id)
        effects.complete(first.id)
        XCTAssertEqual(effects.impact?.id, next.id)
        effects.reset()
        effects.complete(next.id)
        XCTAssertNil(effects.impact)
        let newLevel = try engine()
        newLevel.go()
        for event in newLevel.drainEvents() { effects.process(event, reduceMotion: false) }
        XCTAssertNil(effects.impact)
    }

    func testReducedMotionSuppressesCrashEffectsAndTurningItOffDoesNotReplay() throws {
        let run = try engine(merge: true)
        run.go()
        run.advance(by: 10)
        let events = run.drainEvents()
        var effects = MultiVanCrashEffects()
        for event in events { effects.process(event, reduceMotion: true) }
        XCTAssertNil(effects.impact)
        for event in events { effects.process(event, reduceMotion: false) }
        XCTAssertNotNil(effects.impact)
        effects.reset() // Either accessibility preference suppresses an in-flight effect.
        for event in run.drainEvents() { effects.process(event, reduceMotion: false) }
        XCTAssertNil(effects.impact)
    }
}

// MV-37: the appearance is a snapshot, with no UI lock cache or proximity rule.
final class MultiVanSwitchAppearanceTests: XCTestCase {
    func testPlanningAndRunningStylesFollowAuthoritativeLockSet() throws {
        let run = try MultiVanEngine(level: MultiVanLiveSwitchTests.fixture())
        for id in ["switch", "normal"] {
            let appearance = MultiVanSwitchAppearance(engine: run, nodeID: id)
            XCTAssertTrue(appearance.isAvailable)
            XCTAssertFalse(appearance.showsLock)
            XCTAssertFalse(appearance.pulses)
            XCTAssertEqual(appearance.opacity, 1)
            XCTAssertEqual(appearance.isLive, id == "switch")
        }
        run.go()
        let live = MultiVanSwitchAppearance(engine: run, nodeID: "switch")
        XCTAssertTrue(live.isAvailable)
        XCTAssertTrue(live.pulses)
        let normal = MultiVanSwitchAppearance(engine: run, nodeID: "normal")
        XCTAssertTrue(normal.showsLock)
        XCTAssertEqual(normal.opacity, 0.5)
        run.advance(by: 0.5)
        let locked = MultiVanSwitchAppearance(engine: run, nodeID: "switch")
        XCTAssertTrue(locked.showsLock)
        XCTAssertEqual(locked.opacity, 1)
        XCTAssertFalse(locked.pulses)
        XCTAssertEqual(locked.accessibilityValue, "Live switch, temporarily locked while a van is nearby")
        run.advance(by: 0.5)
        XCTAssertTrue(MultiVanSwitchAppearance(engine: run, nodeID: "switch").pulses)
        run.stop()
        XCTAssertFalse(MultiVanSwitchAppearance(engine: run, nodeID: "normal").showsLock)
    }

    func testMultipleDrivingVansLockAndUnlockSwitchesIndependently() throws {
        let level = try MultiVanLiveSwitchTests.fixture {
            $0["liveSwitchNodeIDs"] = ["switch", "normal"]
            $0["vans"] = [
                ["id": "red", "color": "red", "startNodeID": "switch"],
                ["id": "blue", "color": "blue", "startNodeID": "normal", "departDelay": 0.25]
            ]
        }
        let run = try MultiVanEngine(level: level)
        run.go()
        for (time, expected) in [(0.0, Set(["switch"])), (0.26, Set(["switch", "normal"])),
                                 (0.3, Set(["normal"])), (0.6, Set<String>())] {
            run.advance(by: time - run.runTime)
            XCTAssertEqual(run.lockedSwitchNodeIDs, expected)
            for id in ["switch", "normal"] {
                let state = MultiVanSwitchAppearance(engine: run, nodeID: id)
                XCTAssertEqual(state.showsLock, expected.contains(id))
                XCTAssertEqual(state.pulses, !expected.contains(id))
            }
        }
        XCTAssertEqual(run.vans.map(\.status), [.driving, .driving])
    }

    func testAcceptedTapUpdatesArrowSourceRejectedTapPreservesItAndEmitsFeedback() throws {
        let run = try MultiVanEngine(level: MultiVanLiveSwitchTests.fixture())
        run.go()
        XCTAssertEqual(run.tapSwitch(nodeID: "switch"), .accepted)
        XCTAssertEqual(run.runtimeGraph.nodesByID["switch"]?.activeOutgoingEdgeID, "blue_exit")
        run.advance(by: 0.5)
        let routes = run.previewRoutes
        let time = run.runTime
        XCTAssertTrue(MultiVanSwitchAppearance(engine: run, nodeID: "switch").showsLock)
        XCTAssertEqual(run.tapSwitch(nodeID: "switch"), .rejectedLocked)
        XCTAssertEqual(run.runtimeGraph.nodesByID["switch"]?.activeOutgoingEdgeID, "blue_exit")
        XCTAssertEqual(run.previewRoutes, routes)
        XCTAssertEqual(run.runTime, time)
        let events = run.drainEvents()
        XCTAssertEqual(events, [.go, .switchTapped, .tapRejected(nodeID: "switch")])
        var feedback = MultiVanSwitchFeedback()
        for event in events { feedback.process(event, reduceMotion: false) }
        XCTAssertNotNil(feedback.rejectionTokens["switch"])
        XCTAssertEqual(MultiVanHaptic.feedback(for: events.last!), .lightImpact)
        XCTAssertTrue(run.drainEvents().isEmpty)
    }

    func testRetryAndNewEngineHaveNoStaleRunningAppearance() throws {
        let level = try MultiVanLiveSwitchTests.fixture()
        let run = try MultiVanEngine(level: level)
        run.go()
        run.advance(by: 1)
        run.tapSwitch(nodeID: "switch")
        run.advance(by: 5)
        XCTAssertEqual(run.outcome, .win)
        XCTAssertTrue(MultiVanSwitchAppearance(engine: run, nodeID: "switch").showsLock)
        run.retry()
        for engine in [run, try MultiVanEngine(level: level)] {
            for id in ["switch", "normal"] {
                let state = MultiVanSwitchAppearance(engine: engine, nodeID: id)
                XCTAssertTrue(state.isAvailable)
                XCTAssertFalse(state.showsLock)
                XCTAssertFalse(state.pulses)
            }
        }
        var feedback = MultiVanSwitchFeedback()
        feedback.process(.tapRejected(nodeID: "switch"), reduceMotion: false)
        feedback.reset()
        XCTAssertTrue(feedback.rejectionTokens.isEmpty)
        feedback.process(.tapRejected(nodeID: "normal"), reduceMotion: false)
        feedback.process(.go, reduceMotion: false)
        XCTAssertTrue(feedback.rejectionTokens.isEmpty)
    }

    func testEitherReduceMotionSettingKeepsStaticLockAndLiveDistinctions() throws {
        let run = try MultiVanEngine(level: MultiVanLiveSwitchTests.fixture())
        run.go()
        for locked in [false, true] {
            if locked { run.advance(by: 0.5) }
            for (system, user) in [(true, false), (false, true), (true, true)] {
                let state = MultiVanSwitchAppearance(engine: run, nodeID: "switch", systemReduceMotion: system, reducesExtraAnimations: user)
                XCTAssertFalse(state.pulses)
                XCTAssertTrue(state.isLive)
                XCTAssertEqual(state.showsLock, locked)
                XCTAssertEqual(state.isAvailable, !locked)
                XCTAssertEqual(state.opacity, 1)
            }
        }
        var feedback = MultiVanSwitchFeedback()
        feedback.process(.tapRejected(nodeID: "switch"), reduceMotion: true)
        XCTAssertTrue(feedback.rejectionTokens.isEmpty)
    }
}

final class MultiVanWinPresentationTests: XCTestCase {
    // A real delivery plus an independent four-exit switch lets each rating use
    // configuration-based changeCount without altering any authored solution.
    private func engine(changes: Int = 0) throws -> MultiVanEngine {
        let url = URL(fileURLWithPath: #filePath)
            .deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent()
            .appendingPathComponent("TinyRoutes/Resources/PrototypeLevels/proto_01.json")
        var json = try XCTUnwrap(JSONSerialization.jsonObject(with: Data(contentsOf: url)) as? [String: Any])
        var graph = try XCTUnwrap(json["graph"] as? [String: Any])
        var nodes = try XCTUnwrap(graph["nodes"] as? [[String: Any]])
        var edges = try XCTUnwrap(graph["edges"] as? [[String: Any]])
        nodes.append(["id": "rating_switch", "x": 1, "y": 0, "outgoingEdgeIDs": (0..<4).map { "exit_\($0)" }])
        for index in 0..<4 {
            edges.append(["id": "exit_\(index)", "fromNodeID": "rating_switch", "toNodeID": "red_house"])
        }
        graph["nodes"] = nodes
        graph["edges"] = edges
        json["graph"] = graph
        let level = try JSONDecoder().decode(MultiVanLevel.self, from: JSONSerialization.data(withJSONObject: json))
        let engine = try MultiVanEngine(level: level)
        for _ in 0..<changes { engine.tapSwitch(nodeID: "rating_switch") }
        return engine
    }

    private func win(_ engine: MultiVanEngine) {
        engine.go()
        engine.advance(by: 20)
        XCTAssertEqual(engine.outcome, .win)
    }

    func testOneTwoAndThreeStarWinsRevealOnlyEarnedStarsThenActions() throws {
        for (changes, expected) in [(0, 3), (1, 2), (3, 1)] {
            let run = try engine(changes: changes)
            win(run)
            var state = MultiVanWinPresentation()
            let token = try XCTUnwrap(state.begin(engine: run, reduceMotion: false))
            XCTAssertEqual(state.rating, expected)
            XCTAssertEqual(state.rating, MultiVanStars.rating(changes: run.changeCount, par: run.level.parChanges))
            XCTAssertEqual(state.revealedStars, 0)
            XCTAssertFalse(state.showsActions)
            state.complete(for: token)
            XCTAssertFalse(state.showsActions)
            for count in 1...expected {
                state.revealNext(for: token)
                XCTAssertEqual(state.revealedStars, count)
                XCTAssertEqual(3 - state.revealedStars, 3 - count)
                XCTAssertFalse(state.showsActions)
            }
            state.revealNext(for: token)
            XCTAssertEqual(state.revealedStars, expected)
            state.complete(for: token)
            XCTAssertTrue(state.showsActions)
            XCTAssertFalse(state.accessibilityRating.isEmpty)
        }
    }

    func testPlanningRunningAndFailureNeverBeginAReveal() throws {
        let run = try engine()
        var state = MultiVanWinPresentation()
        XCTAssertNil(state.begin(engine: run, reduceMotion: false))
        run.go()
        XCTAssertNil(state.begin(engine: run, reduceMotion: false))
        let url = URL(fileURLWithPath: #filePath)
            .deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent()
            .appendingPathComponent("TinyRoutes/Resources/PrototypeLevels/proto_02.json")
        let failed = try MultiVanEngine(level: JSONDecoder().decode(MultiVanLevel.self, from: Data(contentsOf: url)))
        failed.go()
        failed.advance(by: 20)
        XCTAssertEqual(failed.phase, .finished)
        XCTAssertNotEqual(failed.outcome, .win)
        XCTAssertNil(state.begin(engine: failed, reduceMotion: true))
        XCTAssertEqual(state.rating, 0)
        XCTAssertEqual(state.revealedStars, 0)
        XCTAssertFalse(state.showsActions)
    }

    func testRepeatedWinReadsAndPreferenceChangesDoNotRestartReveal() throws {
        let run = try engine()
        win(run)
        var state = MultiVanWinPresentation()
        let token = try XCTUnwrap(state.begin(engine: run, reduceMotion: false))
        state.revealNext(for: token)
        for reduced in [false, true, false] {
            XCTAssertNil(state.begin(engine: run, reduceMotion: reduced))
            XCTAssertEqual(state.id, token)
            XCTAssertEqual(state.revealedStars, 1)
        }
        state.finishImmediately()
        XCTAssertEqual(state.revealedStars, 3)
        XCTAssertTrue(state.showsActions)
        state.revealNext(for: token)
        XCTAssertEqual(state.revealedStars, 3)
        XCTAssertNil(state.begin(engine: run, reduceMotion: false))
    }

    func testReplayGetsFreshTokenAndRejectsStaleCompletions() throws {
        let run = try engine()
        win(run)
        var state = MultiVanWinPresentation()
        let old = try XCTUnwrap(state.begin(engine: run, reduceMotion: true))
        state.reset()
        run.retry()
        XCTAssertEqual(state.revealedStars, 0)
        XCTAssertNil(state.begin(engine: run, reduceMotion: false))
        win(run)
        let fresh = try XCTUnwrap(state.begin(engine: run, reduceMotion: false))
        XCTAssertNotEqual(old, fresh)
        state.revealNext(for: old)
        state.complete(for: old)
        XCTAssertEqual(state.revealedStars, 0)
        XCTAssertFalse(state.showsActions)
        state.revealNext(for: fresh)
        XCTAssertEqual(state.revealedStars, 1)
    }

    func testNewLevelAndLeavingInvalidatePendingSteps() throws {
        let first = try engine()
        win(first)
        var state = MultiVanWinPresentation()
        let old = try XCTUnwrap(state.begin(engine: first, reduceMotion: true))
        state.reset()
        state.revealNext(for: old)
        state.complete(for: old)
        XCTAssertNil(state.id)
        XCTAssertEqual(state.revealedStars, 0)
        let next = try engine(changes: 3)
        win(next)
        let fresh = try XCTUnwrap(state.begin(engine: next, reduceMotion: false))
        state.revealNext(for: old)
        XCTAssertEqual(state.revealedStars, 0)
        state.revealNext(for: fresh)
        XCTAssertEqual(state.revealedStars, 1)
        XCTAssertEqual(state.rating, 1)
    }

    func testReduceMotionImmediatelyShowsEachEarnedRatingAndActions() throws {
        for changes in [0, 1, 3] {
            let run = try engine(changes: changes)
            win(run)
            var state = MultiVanWinPresentation()
            XCTAssertNotNil(state.begin(engine: run, reduceMotion: true))
            XCTAssertEqual(state.revealedStars, MultiVanStars.rating(changes: run.changeCount, par: run.level.parChanges))
            XCTAssertTrue(state.showsActions)
        }
    }

    func testPresentationDoesNotConsumeOrDuplicateVictoryEvents() throws {
        let run = try engine()
        win(run)
        var state = MultiVanWinPresentation()
        let token = try XCTUnwrap(state.begin(engine: run, reduceMotion: false))
        for _ in 0..<3 { state.revealNext(for: token) }
        state.complete(for: token)
        let events = run.drainEvents()
        XCTAssertEqual(events.filter { $0 == .allDelivered }.count, 1)
        XCTAssertEqual(events.filter { if case .delivered = $0 { return true }; return false }.count, 1)
        XCTAssertTrue(run.drainEvents().isEmpty)
    }

    func testFastForwardWinResetsSpeedAndUsesSameRevealSequence() throws {
        var sequences: [[Int]] = []
        for accelerated in [false, true] {
            let run = try engine()
            let driver = MultiVanFrameDriver()
            run.go()
            driver.advance(at: Date(timeIntervalSinceReferenceDate: 0), engine: run, isActive: true)
            driver.setFastForwarding(accelerated, at: Date(timeIntervalSinceReferenceDate: 0), engine: run, isActive: true)
            for frame in 1...1200 where run.phase == .run {
                driver.advance(at: Date(timeIntervalSinceReferenceDate: Double(frame) / 60), engine: run, isActive: true)
            }
            XCTAssertEqual(run.outcome, .win)
            XCTAssertFalse(driver.isFastForwarding)
            var state = MultiVanWinPresentation()
            let token = try XCTUnwrap(state.begin(engine: run, reduceMotion: false))
            var counts = [state.revealedStars]
            for _ in 0..<3 {
                state.revealNext(for: token)
                counts.append(state.revealedStars)
            }
            sequences.append(counts)
        }
        XCTAssertEqual(sequences[0], [0, 1, 2, 3])
        XCTAssertEqual(sequences[0], sequences[1])
    }
}

/// Description checks and source wiring checks complement physical VoiceOver testing.
/// They do not establish actual focus, speech, or touch usability on iOS.
final class MultiVanAccessibilityTests: XCTestCase {
    private var root: URL {
        URL(fileURLWithPath: #filePath)
            .deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent()
    }

    private func source(_ path: String) throws -> String {
        try String(contentsOf: root.appendingPathComponent(path), encoding: .utf8)
    }

    private func engine(_ id: String) throws -> MultiVanEngine {
        let data = try Data(contentsOf: root.appendingPathComponent("TinyRoutes/Resources/PrototypeLevels/\(id).json"))
        return try MultiVanEngine(level: JSONDecoder().decode(MultiVanLevel.self, from: data))
    }

    func testAuthoredSwitchLocationsAreUniqueAndDoNotSpeakInternalIDs() throws {
        for index in 1...12 {
            let run = try engine(String(format: "proto_%02d", index))
            let nodes = MultiVanBoardView.switchNodes(in: run.runtimeGraph)
            let labels = nodes.map { MultiVanSwitchAppearance.accessibilityLabel(node: $0, gridRows: run.tuning.gridRows) }
            XCTAssertEqual(Set(labels).count, nodes.count)
            for (node, label) in zip(nodes, labels) {
                XCTAssertTrue(label.contains("column"))
                XCTAssertTrue(label.contains("row"))
                XCTAssertFalse(label.contains(node.id))
            }
        }
        let run = try engine("proto_09")
        let node = try XCTUnwrap(run.runtimeGraph.nodesByID["switch"])
        XCTAssertEqual(MultiVanSwitchAppearance.accessibilityLabel(node: node, gridRows: 7), "Switch at column 3, row 4")
    }

    func testSelectedRouteUsesAuthoredGeometryAndDescriptionReadsDoNotEmitEvents() throws {
        let run = try engine("proto_09")
        func value() throws -> String {
            let node = try XCTUnwrap(run.runtimeGraph.nodesByID["switch"])
            let edge = try XCTUnwrap(node.activeOutgoingEdgeID.flatMap { run.runtimeGraph.edgesByID[$0] })
            let angle = SwitchArrowDirectionResolver.directionAngle(for: edge, from: node, in: run.runtimeGraph)
            return MultiVanSwitchAppearance(engine: run, nodeID: node.id).routeAccessibilityValue(
                direction: SwitchOptionIndicatorLayout.cardinalDirectionLabel(for: angle), exitCount: node.outgoingEdgeIDs.count
            )
        }
        for _ in 0..<20 {
            XCTAssertEqual(try value(), "Route selected: west. 2 exits. Live switch, available to change")
        }
        XCTAssertEqual(run.changeCount, 0)
        XCTAssertTrue(run.drainEvents().isEmpty)
        XCTAssertEqual(run.tapSwitch(nodeID: "switch"), .accepted)
        XCTAssertEqual(try value(), "Route selected: north. 2 exits. Live switch, available to change")
        XCTAssertEqual(run.changeCount, 1)
        XCTAssertEqual(run.drainEvents(), [.switchTapped])
    }

    func testSwitchAvailabilityExplainsTemporaryAndRunLocksWithoutBypassingRejection() throws {
        let run = try MultiVanEngine(level: MultiVanLiveSwitchTests.fixture())
        XCTAssertEqual(MultiVanSwitchAppearance(engine: run, nodeID: "switch").accessibilityHint, "Activate to select the next exit")
        run.go()
        XCTAssertEqual(MultiVanSwitchAppearance(engine: run, nodeID: "normal").accessibilityValue, "Locked during the run")
        XCTAssertTrue(MultiVanSwitchAppearance(engine: run, nodeID: "normal").accessibilityHint.contains("Stop"))
        run.advance(by: 0.5)
        let locked = MultiVanSwitchAppearance(engine: run, nodeID: "switch")
        XCTAssertTrue(locked.accessibilityValue.contains("temporarily locked"))
        XCTAssertFalse(locked.isAvailable)
        let selection = run.runtimeGraph.nodesByID["switch"]?.activeOutgoingEdgeID
        let count = run.changeCount
        _ = run.drainEvents()
        XCTAssertEqual(run.tapSwitch(nodeID: "switch"), .rejectedLocked)
        XCTAssertEqual(run.runtimeGraph.nodesByID["switch"]?.activeOutgoingEdgeID, selection)
        XCTAssertEqual(run.changeCount, count)
        XCTAssertEqual(run.drainEvents(), [.tapRejected(nodeID: "switch")])
        run.stop()
        XCTAssertTrue(MultiVanSwitchAppearance(engine: run, nodeID: "switch").isAvailable)
    }

    func testVanDescriptionsDistinguishStatesDestinationsAndAllMatchingSymbols() {
        for (color, symbol) in [(VanColor.red, "circle"), (.blue, "triangle"), (.yellow, "square"), (.green, "star")] {
            XCTAssertEqual(color.accessibilitySymbolName, symbol)
            for (status, state, delivered) in [
                (MultiVanVanState.Status.waiting, "Waiting", false),
                (.driving, "Driving", false), (.parked, "Delivered", true),
                (.parked, "Parked at a different house", false),
                (.crashed, "Crashed", false), (.stuck, "Stopped at a dead end", false)
            ] {
                let value = MultiVanVanView.accessibilityValue(color: color, status: status, isDelivered: delivered)
                XCTAssertTrue(value.hasPrefix(state))
                XCTAssertTrue(value.contains("Destination: \(color.rawValue) \(symbol) house"))
            }
        }
    }

    func testVictoryRatingIsStableDuringRevealAndResetsForReplay() throws {
        let run = try engine("proto_01")
        run.go()
        run.advance(by: 10)
        var presentation = MultiVanWinPresentation()
        let token = try XCTUnwrap(presentation.begin(engine: run, reduceMotion: false))
        XCTAssertEqual(presentation.accessibilityRating, "Three out of three stars")
        for _ in 0..<3 {
            presentation.revealNext(for: token)
            XCTAssertEqual(presentation.accessibilityRating, "Three out of three stars")
            XCTAssertNil(presentation.begin(engine: run, reduceMotion: false))
        }
        XCTAssertEqual(run.drainEvents().filter { $0 == .allDelivered }.count, 1)
        presentation.reset()
        run.retry()
        XCTAssertNil(presentation.begin(engine: run, reduceMotion: false))
        XCTAssertTrue(run.drainEvents().isEmpty)
    }

    func testSwitchAndObjectAccessibilitySourceWiring() throws {
        let board = try source("TinyRoutes/Prototype/MultiVanBoardView.swift")
        XCTAssertEqual(board.components(separatedBy: "engine.tapSwitch(nodeID: node.id)").count - 1, 1)
        XCTAssertTrue(board.contains("Button {\n                            let result = engine.tapSwitch"))
        XCTAssertTrue(board.contains("onSwitchTapped?(node.id, result)"))
        XCTAssertTrue(board.contains(".accessibilityElement(children: .ignore)"))
        XCTAssertTrue(board.contains(".accessibilityValue(appearance.routeAccessibilityValue("))
        XCTAssertTrue(board.contains(".accessibilityHint(appearance.accessibilityHint)"))
        XCTAssertFalse(board.contains(".disabled(")) // Locked switches must remain discoverable and testable.
        XCTAssertTrue(board.contains("static let switchHitSize: CGFloat = 44"))
        XCTAssertTrue(board.contains(".accessibilityHidden(true)")) // Roads, effects and failure ring.
        let house = try source("TinyRoutes/Prototype/MultiVanHouseView.swift")
        XCTAssertTrue(house.contains("color.accessibilitySymbolName"))
        XCTAssertTrue(house.contains("isDelivered ? \"Delivered\" : \"Awaiting delivery\""))
        XCTAssertTrue(house.contains(".accessibilityElement(children: .ignore)"))
        let van = try source("TinyRoutes/Prototype/MultiVanVanView.swift")
        XCTAssertTrue(van.contains(".accessibilityValue(Self.accessibilityValue("))
        XCTAssertTrue(van.contains(".accessibilityElement(children: .ignore)"))
    }

    func testControlsAndFastForwardUseExistingActions() throws {
        let screen = try source("TinyRoutes/Prototype/MultiVanGameplayScreen.swift")
        for title in ["GO", "Stop", "Try again", "Replay", "Next", "Reset switches", "Fast-forward"] {
            XCTAssertTrue(screen.contains("\"\(title)\""), title)
        }
        XCTAssertTrue(screen.contains(".accessibilityAction { setFastForwarding(!frameDriver.isFastForwarding) }"))
        XCTAssertTrue(screen.contains("guard !voiceOverEnabled else { return }"))
        XCTAssertTrue(screen.contains("onLongPressGesture(minimumDuration: .infinity"))
        XCTAssertTrue(screen.contains("frameDriver.setFastForwarding(enabled, at: Date(), engine: engine"))
        XCTAssertTrue(screen.contains(".accessibilityAddTraits(frameDriver.isFastForwarding ? [.isSelected] : [])"))
        let levels = try source("TinyRoutes/Prototype/MultiVanPrototypeScreen.swift")
        XCTAssertTrue(levels.contains(".accessibilityLabel(\"Level"))
        XCTAssertTrue(levels.contains(".frame(minHeight: 44)"))
    }

    func testDynamicTypeAndReducedMotionSourceWiring() throws {
        let screen = try source("TinyRoutes/Prototype/MultiVanGameplayScreen.swift")
        XCTAssertTrue(screen.contains("ScrollView {"))
        XCTAssertTrue(screen.contains(".frame(minHeight: engine.outcome == .win ? 140 : 320)"))
        XCTAssertTrue(screen.contains("dynamicTypeSize.isAccessibilitySize ? AnyLayout(VStackLayout"))
        XCTAssertTrue(screen.contains("dynamicTypeSize.isAccessibilitySize ? 240 : 110"))
        XCTAssertTrue(screen.contains("reduceMotion || settingsService.settings.reducesExtraAnimations"))
        XCTAssertTrue(screen.contains(".transition(reducesExtraAnimations ? .identity"))
        XCTAssertTrue(screen.contains("withAnimation(reducesExtraAnimations ? nil"))
        XCTAssertTrue(screen.contains("winPresentation.finishImmediately()"))
        let actions = try source("TinyRoutes/UI/Components/TRResultActionButton.swift")
        XCTAssertTrue(actions.contains("@ScaledMetric"))
        XCTAssertTrue(actions.contains("supportsDynamicType: Bool = false")) // Existing production callers retain their layout.
        XCTAssertTrue(actions.contains(".lineLimit(supportsDynamicType ? nil : 1)"))
        XCTAssertEqual(screen.components(separatedBy: "supportsDynamicType: true").count - 1, 2)
    }

    func testResultFocusIsOutcomeDrivenAndNoAnnouncementPollingWasAdded() throws {
        let screen = try source("TinyRoutes/Prototype/MultiVanGameplayScreen.swift")
        XCTAssertTrue(screen.contains(".accessibilityFocused($accessibilityFocus, equals: .failure)"))
        XCTAssertTrue(screen.contains(".accessibilityFocused($accessibilityFocus, equals: .victory)"))
        XCTAssertTrue(screen.contains(".onChange(of: winPresentation.id)"))
        XCTAssertEqual(screen.components(separatedBy: "accessibilityFocus = .victory").count - 1, 1)
        XCTAssertEqual(screen.components(separatedBy: "accessibilityFocus = .failure").count - 1, 1)
        XCTAssertTrue(screen.contains("accessibilityFocus = .levelTitle"))
        XCTAssertTrue(screen.contains(".accessibilityHidden(presentedFailure != nil || engine.outcome == .win)"))
        XCTAssertTrue(screen.contains("All delivered! \\(winPresentation.accessibilityRating)"))
        XCTAssertTrue(screen.contains(".accessibilityHidden(true)")) // Star artwork is represented by the heading.
        XCTAssertEqual(screen.components(separatedBy: "drainEvents: engine.drainEvents").count - 1, 1)
        XCTAssertFalse(screen.contains("UIAccessibility.post"))
        XCTAssertFalse(screen.contains("Timer("))
    }
}


#if DEBUG
final class MultiVanTuningTests: XCTestCase {
    private final class Rig {
        let suite = "MultiVanTuningTests.\(UUID().uuidString)"
        let store: MultiVanPrototypeTuning
        let log: MultiVanPlaytestLog
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)

        init() throws {
            store = MultiVanPrototypeTuning(defaults: try XCTUnwrap(UserDefaults(suiteName: suite)))
            log = MultiVanPlaytestLog(fileURL: directory.appendingPathComponent("attempts.jsonl"))
        }

        deinit {
            log.flush()
            try? FileManager.default.removeItem(at: directory)
            store.defaults.removePersistentDomain(forName: suite)
        }
    }

    private var root: URL {
        URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent()
    }

    private func level(_ number: Int) throws -> MultiVanLevel {
        let id = String(format: "proto_%02d", number)
        return try JSONDecoder().decode(MultiVanLevel.self, from: Data(contentsOf:
            root.appendingPathComponent("TinyRoutes/Resources/PrototypeLevels/\(id).json")))
    }

    private func assertTuning(_ actual: MultiVanTuning, _ expected: MultiVanTuning,
                              file: StaticString = #filePath, line: UInt = #line) {
        XCTAssertEqual(actual.vanSpeed, expected.vanSpeed, file: file, line: line)
        XCTAssertEqual(actual.crashDistance, expected.crashDistance, file: file, line: line)
        XCTAssertEqual(actual.liveSwitchLockRadius, expected.liveSwitchLockRadius, file: file, line: line)
        XCTAssertEqual(actual.stepDuration, expected.stepDuration, file: file, line: line)
        XCTAssertEqual(actual.previewEdgeLimit, expected.previewEdgeLimit, file: file, line: line)
        XCTAssertEqual(actual.failFreezeDuration, expected.failFreezeDuration, file: file, line: line)
        XCTAssertEqual(actual.fastForwardMultiplier, expected.fastForwardMultiplier, file: file, line: line)
        XCTAssertEqual(actual.gridColumns, expected.gridColumns, file: file, line: line)
        XCTAssertEqual(actual.gridRows, expected.gridRows, file: file, line: line)
    }

    func testDefaultsPreserveEveryEstablishedValue() throws {
        let rig = try Rig(), tuning = rig.store.tuning
        assertTuning(tuning, .default)
        XCTAssertEqual(tuning.vanSpeed, 1.5)
        XCTAssertEqual(tuning.crashDistance, 0.35)
        XCTAssertEqual(tuning.liveSwitchLockRadius, 0.4)
        XCTAssertEqual(tuning.stepDuration, 1.0 / 120)
        XCTAssertEqual(tuning.previewEdgeLimit, 40)
        XCTAssertEqual(tuning.failFreezeDuration, 0.6)
        XCTAssertEqual(tuning.fastForwardMultiplier, 2)
        XCTAssertEqual(tuning.gridColumns, 5)
        XCTAssertEqual(tuning.gridRows, 7)
        XCTAssertTrue(MultiVanPrototypeTuning.isDefault(tuning))
        XCTAssertEqual(MultiVanPrototypeTuning.Parameter.allCases.map(\.rawValue),
                       ["vanSpeed", "crashDistance", "liveSwitchLockRadius"])
    }

    func testEachBoundPersistsAndReachesFreshEnginesWithoutChangingOtherFields() throws {
        let rig = try Rig()
        for parameter in MultiVanPrototypeTuning.Parameter.allCases {
            for value in [parameter.range.lowerBound, parameter.range.upperBound] {
                rig.store.reset()
                rig.store.set(value, for: parameter)
                let reopened = MultiVanPrototypeTuning(defaults: try XCTUnwrap(UserDefaults(suiteName: rig.suite)))
                var expected = MultiVanTuning.default
                expected[keyPath: parameter.keyPath] = value
                assertTuning(reopened.tuning, expected)
                var session = MultiVanPrototypeSession(playtestLog: rig.log, tuningOverrides: reopened)
                try session.open(level(1))
                assertTuning(try XCTUnwrap(session.engine).tuning, expected)
                XCTAssertFalse(MultiVanPrototypeTuning.isDefault(reopened.tuning))
                session.returnToList()
                reopened.reset()
                assertTuning(reopened.tuning, .default)
                XCTAssertNil(rig.store.defaults.object(forKey: parameter.key))
            }
        }
    }

    func testInvalidWritesAreRejectedAndInvalidStoredOverridesFallBackToDefaults() throws {
        let rig = try Rig()
        for parameter in MultiVanPrototypeTuning.Parameter.allCases {
            rig.store.set(parameter.range.upperBound, for: parameter)
            let invalid = [Double.nan, .infinity, -.infinity, -1,
                           parameter.range.lowerBound - 0.01, parameter.range.upperBound + 1]
            for value in invalid {
                rig.store.set(value, for: parameter)
                XCTAssertEqual(rig.store.tuning[keyPath: parameter.keyPath], parameter.range.upperBound)
            }
            for value: Any in invalid.map({ $0 as Any }) + ["garbage", "0.5", true, [1.0]] {
                rig.store.defaults.set(value, forKey: parameter.key)
                XCTAssertEqual(rig.store.tuning[keyPath: parameter.keyPath], parameter.defaultValue)
            }
            rig.store.reset()
        }
    }

    func testResetRemovesOnlyTuningOverridesAndExplicitDefaultsRemoveOverrides() throws {
        let rig = try Rig()
        rig.store.defaults.set("keep", forKey: "multiVanPrototype.unrelated")
        rig.store.defaults.set(true, forKey: "production.preference")
        for parameter in MultiVanPrototypeTuning.Parameter.allCases {
            rig.store.set(parameter.range.upperBound, for: parameter)
            rig.store.set(parameter.defaultValue, for: parameter)
            XCTAssertNil(rig.store.defaults.object(forKey: parameter.key))
            rig.store.set(parameter.range.lowerBound, for: parameter)
        }
        rig.store.reset()
        assertTuning(rig.store.tuning, .default)
        XCTAssertTrue(MultiVanPrototypeTuning.isDefault(rig.store.tuning))
        XCTAssertEqual(rig.store.defaults.string(forKey: "multiVanPrototype.unrelated"), "keep")
        XCTAssertTrue(rig.store.defaults.bool(forKey: "production.preference"))
    }

    func testOpenRetryReplayNextListAndReopenUseConsistentSnapshots() throws {
        let rig = try Rig(), firstLevel = try level(1), secondLevel = try level(2)
        var session = MultiVanPrototypeSession(playtestLog: rig.log, tuningOverrides: rig.store)
        try session.open(firstLevel)
        let first = try XCTUnwrap(session.engine)
        first.go()
        first.advance(by: 0.125)
        let position = first.vans[0].position, time = first.runTime
        for parameter in MultiVanPrototypeTuning.Parameter.allCases { rig.store.set(parameter.range.upperBound, for: parameter) }
        assertTuning(first.tuning, .default)
        XCTAssertEqual(first.vans[0].position, position)
        XCTAssertEqual(first.runTime, time)
        XCTAssertEqual(first.phase, .run)
        first.advance(by: 120)
        XCTAssertEqual(first.outcome, .win)
        first.retry() // The same path serves Retry and Replay.
        assertTuning(first.tuning, .default)
        first.go()
        first.advance(by: 120)
        XCTAssertEqual(first.outcome, .win)
        try session.next(in: [firstLevel, secondLevel])
        let experimental = try XCTUnwrap(session.engine)
        assertTuning(experimental.tuning, rig.store.tuning)
        rig.store.reset()
        XCTAssertFalse(MultiVanPrototypeTuning.isDefault(experimental.tuning))
        session.returnToList()
        try session.open(firstLevel)
        assertTuning(try XCTUnwrap(session.engine).tuning, .default)
        session.returnToList()
        rig.store.set(2, for: .vanSpeed)
        var reopened = MultiVanPrototypeSession(playtestLog: rig.log,
            tuningOverrides: MultiVanPrototypeTuning(defaults: try XCTUnwrap(UserDefaults(suiteName: rig.suite))))
        try reopened.open(firstLevel)
        XCTAssertEqual(reopened.engine?.tuning.vanSpeed, 2)
        reopened.returnToList()
    }

    private func replay(_ level: MultiVanLevel, tuning: MultiVanTuning, frame: Double) throws
        -> (MultiVanEngine, [MultiVanEvent]) {
        let script = try PrototypeSolutionScript.load(levelID: level.id)
        let engine = try MultiVanEngine(level: level, tuning: tuning)
        for node in script.planTaps { _ = engine.tapSwitch(nodeID: node) }
        engine.go()
        var nextTap = 0, events = engine.drainEvents()
        var budget = 0.0
        while engine.phase == .run && budget < 120 {
            while nextTap < script.liveTaps.count && script.liveTaps[nextTap].atTime <= engine.runTime + 1e-12 {
                _ = engine.tapSwitch(nodeID: script.liveTaps[nextTap].nodeID)
                nextTap += 1
            }
            // Split at input boundaries so partitions receive identical inputs.
            let untilTap = nextTap < script.liveTaps.count ? script.liveTaps[nextTap].atTime - budget : 120 - budget
            let delta = min(frame, untilTap, 120 - budget)
            guard delta > 1e-12 else { break }
            engine.advance(by: delta)
            budget += delta
            events += engine.drainEvents()
        }
        return (engine, events)
    }

    func testEveryExperimentalBoundIsDeterministicAcrossPartitionsIncludingFailedSolutions() throws {
        let rig = try Rig()
        var sawFailure = false
        for parameter in MultiVanPrototypeTuning.Parameter.allCases {
            for value in [parameter.range.lowerBound, parameter.range.upperBound] {
                rig.store.reset()
                rig.store.set(value, for: parameter)
                let tuning = rig.store.tuning
                for number in [1, 7, 8, 9, 11, 12] {
                    let level = try level(number)
                    let (reference, events) = try replay(level, tuning: tuning, frame: tuning.stepDuration)
                    sawFailure = sawFailure || (reference.outcome != nil && reference.outcome != .win)
                    for frame in [tuning.stepDuration, 1.0 / 60, 0.037] {
                        let (run, replayEvents) = try replay(level, tuning: tuning, frame: frame)
                        XCTAssertEqual(run.outcome, reference.outcome)
                        XCTAssertEqual(run.runTime, reference.runTime)
                        XCTAssertEqual(run.vans.map(\.position), reference.vans.map(\.position))
                        XCTAssertEqual(run.vans.map(\.status), reference.vans.map(\.status))
                        XCTAssertEqual(run.lockedSwitchNodeIDs, reference.lockedSwitchNodeIDs)
                        XCTAssertEqual(run.changeCount, reference.changeCount)
                        XCTAssertEqual(replayEvents, events)
                    }
                }
            }
        }
        XCTAssertTrue(sawFailure, "An experimental configuration should safely exercise a failed authored solution")
    }

    func testVanSpeedAndFastForwardScaleIndependentQuantitiesAndReleaseRestoresPlayback() throws {
        let rig = try Rig()
        rig.store.set(3, for: .vanSpeed)
        let engine = try MultiVanEngine(level: level(1), tuning: rig.store.tuning)
        engine.go()
        let driver = MultiVanFrameDriver()
        func date(_ time: Double) -> Date { Date(timeIntervalSinceReferenceDate: time) }
        driver.advance(at: date(0), engine: engine, isActive: true)
        driver.advance(at: date(0.125), engine: engine, isActive: true)
        XCTAssertEqual(engine.runTime, 0.125)
        XCTAssertEqual(engine.vans[0].distanceAlongEdge, 0.375, accuracy: 1e-9)
        driver.setFastForwarding(true, at: date(0.125), engine: engine, isActive: true)
        driver.advance(at: date(0.25), engine: engine, isActive: true)
        XCTAssertEqual(engine.runTime, 0.375)
        XCTAssertEqual(engine.vans[0].distanceAlongEdge, 1.125, accuracy: 1e-9)
        driver.setFastForwarding(false, at: date(0.25), engine: engine, isActive: true)
        driver.advance(at: date(0.375), engine: engine, isActive: true)
        XCTAssertEqual(engine.runTime, 0.5)
        XCTAssertEqual(engine.vans[0].distanceAlongEdge, 1.5, accuracy: 1e-9)
        XCTAssertFalse(driver.isFastForwarding)
        XCTAssertEqual(engine.tuning.fastForwardMultiplier, 2)
    }
}
#endif
