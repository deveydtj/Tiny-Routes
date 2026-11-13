import SceneKit
import XCTest
@testable import TinyRoutes

/// MW-09: every event the flat board reacts to has a diorama response, and none
/// plays with motion reduced. SceneKit runs no actions without a renderer, so the
/// bursts these tests start stay in the scene for them to count.
@MainActor
final class MultiVanDioramaEffectsTests: XCTestCase {
    /// The gameplay screen's wiring without the screen: one drain feeds every
    /// feedback model, then the scene syncs and plays, as `updateUIView` does.
    @MainActor
    private final class Rig {
        let reduced: Bool
        let scene = MultiVanDioramaScene()
        var celebration = MultiVanCelebration()
        var personality = MultiVanPersonality()
        var crashEffects = MultiVanCrashEffects()
        var switchFeedback = MultiVanSwitchFeedback()
        private(set) var events: [MultiVanEvent] = []
        private(set) var outcome: MultiVanEngine.Outcome?

        init(reduced: Bool) { self.reduced = reduced }

        func step(_ engine: MultiVanEngine) {
            if scene.levelID == nil {
                scene.load(engine.level, graph: engine.runtimeGraph)
                // The board was up while the player planned, before anything happened.
                scene.play(MultiVanDioramaCues(), animates: !reduced)
            }
            outcome = engine.outcome
            let drained = engine.drainEvents()
            events += drained
            for event in drained {
                celebration.process(event, engine: engine, reduceMotion: reduced)
                personality.process(event, engine: engine, reduceMotion: reduced)
                crashEffects.process(event, reduceMotion: reduced)
                switchFeedback.process(event, reduceMotion: reduced)
            }
            scene.sync(MultiVanDioramaFrame(engine: engine, systemReduceMotion: false, reducesExtraAnimations: reduced))
            scene.play(
                MultiVanDioramaCues(
                    engine: engine, celebration: celebration, personality: personality,
                    crashEffects: crashEffects, switchFeedback: switchFeedback
                ),
                animates: !reduced
            )
        }

        func bursts(_ name: String) -> [SCNNode] {
            scene.effectsNode.childNodes.filter { $0.name == name }
        }
    }

    private func levels() throws -> [MultiVanLevel] {
        let levels = try MultiVanLevelRepository().loadAllLevels()
        XCTAssertEqual(levels.count, 19)
        return levels
    }

    private func pose(_ van: SCNNode?) -> SCNNode? {
        van?.childNode(withName: MultiVanDioramaPieces.Part.pose, recursively: false)
    }

    private func body(_ house: SCNNode?) -> SCNNode? {
        house?.childNode(withName: MultiVanDioramaPieces.Part.houseBody, recursively: false)
    }

    // MARK: - Every event

    func testEveryLevelsEventsGetADioramaResponse() throws {
        var seen = Set<String>()
        for level in try levels() {
            for (name, script) in [
                ("solution", try PrototypeSolutionScript.load(levelID: level.id)),
                ("as authored", PrototypeSolutionScript()),
            ] {
                let label = "\(level.id) \(name)"
                let rig = Rig(reduced: false)
                var drove = Set<String>()
                var deliveries = 0, crashes = 0
                let check = { (engine: MultiVanEngine) in
                    let before = rig.events.count
                    rig.step(engine)
                    engine.vans.filter { $0.status == .driving }.forEach { drove.insert($0.id) }
                    for event in rig.events[before...] {
                        switch event {
                        case let .delivered(vanID, _):
                            deliveries += 1
                            seen.insert("delivered")
                            XCTAssertNotNil(self.pose(rig.scene.vans[vanID])?.action(forKey: MultiVanDioramaEffects.Key.hop), "\(label): \(vanID) hops home")
                            let house = engine.level.houses.first { $0.color == engine.vans.first { $0.id == vanID }?.color }
                            let squashes = self.body(house.flatMap { rig.scene.houses[$0.nodeID] })?.animationKeys ?? []
                            XCTAssertTrue(squashes.contains(MultiVanDioramaEffects.Key.squash), "\(label): the house squashes")
                        case .crashed:
                            crashes += 1
                            seen.insert("crashed")
                            XCTAssertNotNil(rig.scene.cameraNode.action(forKey: MultiVanDioramaEffects.Key.shake), "\(label): the camera shakes")
                        case .allDelivered:
                            seen.insert("allDelivered")
                        case .go:
                            seen.insert("go")
                        case .switchTapped, .tapRejected, .wrongHouse, .pickedUp, .missingPackage,
                             .held, .released, .paused, .resumed:
                            break
                        }
                    }
                }
                if name == "solution" {
                    XCTAssertEqual(try PrototypeSolutionRunner.run(level: level, script: script, onStep: check).outcome, .win, label)
                } else {
                    _ = try? PrototypeSolutionRunner.run(level: level, script: script, onStep: check)
                }

                // A parcel and a pop of confetti for each delivery, and a shower for a win.
                XCTAssertEqual(rig.bursts(MultiVanDioramaEffects.Name.parcel).count, deliveries, label)
                let confetti = rig.bursts(MultiVanDioramaEffects.Name.confetti).map(\.childNodes.count)
                let won = rig.outcome == .win
                XCTAssertEqual(confetti.sorted(), ([Int](repeating: 26, count: deliveries) + (won ? [90] : [])).sorted(), label)
                // Exhaust behind every van that pulled away, and cotton wool where two met.
                let puffs = rig.bursts(MultiVanDioramaEffects.Name.puff).map(\.childNodes.count)
                XCTAssertEqual(puffs.filter { $0 == 3 }.count, drove.count, "\(label) departures")
                XCTAssertEqual(puffs.filter { $0 == 10 }.count, crashes, "\(label) crashes")
                XCTAssertEqual(rig.scene.smokeColumns.count, level.houses.count, "\(label): every chimney smokes")
            }
        }
        XCTAssertEqual(seen, ["go", "delivered", "allDelivered", "crashed"], "the corpus reaches every event with a response")
    }

    func testReducedMotionPlaysNothing() throws {
        for level in try levels() {
            let rig = Rig(reduced: true)
            let check = { (engine: MultiVanEngine) in
                rig.step(engine)
                XCTAssertTrue(rig.scene.effectsNode.childNodes.isEmpty, level.id)
                XCTAssertNil(rig.scene.cameraNode.action(forKey: MultiVanDioramaEffects.Key.shake), level.id)
                for van in rig.scene.vans.values {
                    XCTAssertNil(self.pose(van)?.action(forKey: MultiVanDioramaEffects.Key.hop), level.id)
                }
                for house in rig.scene.houses.values {
                    XCTAssertTrue(self.body(house)?.animationKeys.isEmpty ?? false, level.id)
                }
                for dial in rig.scene.dials.values {
                    XCTAssertFalse(dial.hasActions, "\(level.id): dials neither pulse nor shake")
                }
            }
            XCTAssertEqual(try PrototypeSolutionRunner.run(level: level, script: try PrototypeSolutionScript.load(levelID: level.id), onStep: check).outcome, .win)
            XCTAssertTrue(rig.scene.smokeColumns.isEmpty, "\(level.id): no chimney smoke")
        }
    }

    // MARK: - Tokens

    func testFirstCuesAreHistoryAndMotionOffNeverReplays() throws {
        let level = try XCTUnwrap(levels().first { $0.id == "level_002" })
        let engine = try MultiVanEngine(level: level)
        let scene = MultiVanDioramaScene()
        scene.load(level, graph: engine.runtimeGraph)
        let frame = { (reduced: Bool) in MultiVanDioramaFrame(engine: engine, systemReduceMotion: false, reducesExtraAnimations: reduced) }
        scene.sync(frame(false))

        var cues = MultiVanDioramaCues()
        cues.confetti = UUID()
        scene.play(cues, animates: true)
        XCTAssertTrue(scene.effectsNode.childNodes.isEmpty, "a board's first cues already happened")
        scene.play(cues, animates: true)
        XCTAssertTrue(scene.effectsNode.childNodes.isEmpty, "a token plays at most once")

        cues.confetti = UUID()
        cues.impact = .init(token: UUID(), point: RoadPoint(x: 2, y: 3))
        scene.play(cues, animates: true)
        XCTAssertEqual(scene.effectsNode.childNodes.compactMap(\.name).sorted(), [MultiVanDioramaEffects.Name.confetti, MultiVanDioramaEffects.Name.puff])
        XCTAssertNotNil(scene.cameraNode.action(forKey: MultiVanDioramaEffects.Key.shake))

        // Turning motion off clears what is in flight and settles the lens.
        scene.sync(frame(true))
        XCTAssertTrue(scene.effectsNode.childNodes.isEmpty)
        XCTAssertNil(scene.cameraNode.action(forKey: MultiVanDioramaEffects.Key.shake))
        XCTAssertEqual(scene.cameraNode.simdPosition, .zero)

        // Tokens that arrive while motion is off are noted, not saved up.
        cues.confetti = UUID()
        scene.play(cues, animates: false)
        scene.sync(frame(false))
        scene.play(cues, animates: true)
        XCTAssertTrue(scene.effectsNode.childNodes.isEmpty)
    }

    func testRejectedTapShakesItsDial() throws {
        let level = try XCTUnwrap(levels().first { $0.id == "level_002" })
        for reduced in [false, true] {
            let engine = try MultiVanEngine(level: level)
            let rig = Rig(reduced: reduced)
            rig.step(engine)
            engine.go()
            rig.step(engine)
            let node = try XCTUnwrap(MultiVanBoardRules.switchNodes(in: engine.runtimeGraph).first)
            XCTAssertEqual(engine.tapSwitch(nodeID: node.id), .rejectedFrozen)
            rig.step(engine)
            XCTAssertEqual(rig.scene.dials[node.id]?.action(forKey: MultiVanDioramaEffects.Key.shake) != nil, !reduced)
        }
    }

    // MARK: - State-driven feedback

    func testFailureRingMarksTheLastFailureWhilePlanning() throws {
        for reduced in [false, true] {
            var failed = 0
            for level in try levels() {
                let rig = Rig(reduced: reduced)
                let engine = (try? PrototypeSolutionRunner.run(level: level, script: PrototypeSolutionScript(), onStep: rig.step))
                guard let engine, engine.outcome != .win, let point = engine.lastFailPoint else { continue }
                failed += 1
                rig.step(engine)
                XCTAssertNil(rig.scene.failureRing, "\(level.id): no ring until the player is planning again")

                engine.retry()
                rig.step(engine)
                let ring = try XCTUnwrap(rig.scene.failureRing, level.id)
                let world = MultiVanDioramaGeometry.world(gridX: point.x, gridY: point.y)
                XCTAssertLessThan(simd_distance(SIMD2<Double>(Double(ring.simdWorldPosition.x), Double(ring.simdWorldPosition.z)), SIMD2(world.x, world.z)), 1e-4, level.id)
                XCTAssertEqual(ring.action(forKey: MultiVanDioramaEffects.Key.pulse) != nil, !reduced, level.id)
                if reduced { XCTAssertEqual(ring.opacity, 0.55, accuracy: 1e-6) }

                engine.go()
                rig.step(engine)
                XCTAssertNil(rig.scene.failureRing, "\(level.id): Go clears the ring")
                XCTAssertNil(ring.parent)
            }
            XCTAssertGreaterThan(failed, 0, "some authored plan fails")
        }
    }

    func testLiveDialsPulseOnlyMidRunWithMotionOn() throws {
        let level = try XCTUnwrap(levels().first { $0.id == "level_007" })
        let liveID = try XCTUnwrap(level.liveSwitchNodeIDs.first)
        for reduced in [false, true] {
            let engine = try MultiVanEngine(level: level)
            let rig = Rig(reduced: reduced)
            rig.step(engine)
            let dial = try XCTUnwrap(rig.scene.dials[liveID])
            XCTAssertNil(dial.action(forKey: MultiVanDioramaEffects.Key.pulse), "planning dials hold still")
            engine.go()
            rig.step(engine)
            XCTAssertEqual(dial.action(forKey: MultiVanDioramaEffects.Key.pulse) != nil, !reduced)
            engine.stop()
            rig.step(engine)
            XCTAssertNil(dial.action(forKey: MultiVanDioramaEffects.Key.pulse))
            XCTAssertEqual(dial.simdScale, SIMD3(repeating: MultiVanDioramaPieces.Measure.dialScale))
        }
    }

    // MARK: - Shapes of the effects

    func testShakeFollowsTheFlatBoardsCurveAndComesToRest() {
        let turns = MultiVanDioramaEffects.shakeTurns(peak: 0.06)
        XCTAssertEqual(turns.last?.progress, 1)
        XCTAssertEqual(turns.last?.offset, 0)
        XCTAssertEqual(turns.map { abs($0.offset) }.max() ?? 0, 0.06 * 11 / 12, accuracy: 1e-9)
        // Each turn swings back the other way, smaller.
        for (a, b) in zip(turns.dropLast(2), turns.dropFirst().dropLast()) {
            XCTAssertLessThan(a.offset * b.offset, 0)
            XCTAssertGreaterThan(abs(a.offset), abs(b.offset))
        }
    }

    func testConfettiLandsOnTheLawnInTime() {
        var random = MultiVanDioramaRandom(seed: 9)
        for _ in 0..<200 {
            let velocity = SIMD3((random.next() - 0.5) * 2.2 * 2.2, 1.6 + random.next() * 1.8, (random.next() - 0.5) * 2.2 * 2.2)
            let flight = MultiVanDioramaEffects.ConfettiFlight(height: 1.4, velocity: velocity)
            XCTAssertGreaterThan(flight.apex, 0)
            XCTAssertLessThan(flight.apexTime, flight.landingTime)
            XCTAssertLessThan(flight.landingTime, MultiVanDioramaEffects.Timing.confetti, "lands before the shower ends")
            // The win's shower stays on the table.
            XCTAssertLessThan(abs(flight.landing.x), MultiVanDioramaGeometry.slabWidth / 2)
            XCTAssertLessThan(abs(flight.landing.y), MultiVanDioramaGeometry.slabDepth / 2)
        }
    }

    func testSquashStartsAndEndsAtRest() throws {
        let squash = try XCTUnwrap(MultiVanDioramaEffects.squash(delay: MultiVanDioramaEffects.Timing.toss) as? CAKeyframeAnimation)
        let values = try XCTUnwrap(squash.values as? [NSValue]).map(\.scnVector3Value)
        let rest = SCNVector3(1, 1, 1)
        XCTAssertTrue(SCNVector3EqualToVector3(try XCTUnwrap(values.first), rest))
        XCTAssertTrue(SCNVector3EqualToVector3(try XCTUnwrap(values.last), rest))
        // Holds still while the parcel flies, then squashes wide and low.
        XCTAssertEqual(squash.keyTimes?[1].doubleValue ?? 0, MultiVanDioramaEffects.Timing.toss / squash.duration, accuracy: 1e-9)
        XCTAssertGreaterThan(values.map(\.x).max() ?? 0, 1.07)
        XCTAssertLessThan(values.map(\.y).min() ?? 1, 0.9)
    }
}
