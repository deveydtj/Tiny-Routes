import XCTest
@testable import TinyRoutes

/// Parcel Row, campaign levels 15 to 19: the first content pack after the
/// original fourteen. Every static setting of each new board is pinned here,
/// so a level cannot quietly gain a second answer or lose its only one.
final class MultiVanContentPackTests: XCTestCase {
    private typealias Boards = MultiVanTestBoards

    private static let packIDs = ["level_015", "level_016", "level_017", "level_018", "level_019"]

    private func campaign() throws -> [MultiVanLevel] {
        try MultiVanLevelRepository(bundle: Boards.appBundle).loadAllLevels()
    }

    private func level(_ id: String) throws -> MultiVanLevel {
        try XCTUnwrap(campaign().first { $0.id == id }, "\(id): missing campaign level")
    }

    /// Every static setting of `id`, keyed by its exits in `switches` order.
    private func table(_ id: String, switches: [String], seconds: Double = 40) throws -> [String: Boards.Run] {
        let level = try level(id)
        XCTAssertEqual(level.graph.nodes.filter { $0.outgoingEdgeIDs.count > 1 }.map(\.id).sorted(), switches.sorted(), id)
        var runs: [String: Boards.Run] = [:]
        for configuration in Boards.configurations(of: level) {
            let engine = try Boards.engine(level, selections: configuration)
            runs[switches.map { configuration[$0]! }.joined(separator: " ")] = Boards.run(engine, seconds: seconds)
        }
        return runs
    }

    // MARK: - The pack as a whole

    func testThePackFollowsTheOriginalFourteenAndEveryBoardPassesPolicy() throws {
        let levels = try campaign()
        XCTAssertEqual(Array(levels.map(\.id).suffix(5)), Self.packIDs)
        XCTAssertEqual(levels.count, 19)
        let pack = Array(levels.suffix(5))
        XCTAssertEqual(pack.map(\.name),
                       ["Pick Up First", "Make Room for a Pickup", "Around the Block", "Two Good Plans", "Neighborhood Round"])
        XCTAssertEqual(pack.map(\.parChanges), [1, 2, 2, 2, 3])
        // One board in the pack is a delivery-only rest from parcels.
        XCTAssertEqual(pack.map { $0.packages.count }, [1, 1, 1, 0, 2])
        XCTAssertEqual(Set(pack.map(\.scenerySeed)).count, 5)
        for level in pack {
            XCTAssertEqual(MultiVanLevelRules.authoringIssues(in: level), [], level.id)
            XCTAssertEqual(level.biome, .depot, level.id)
            XCTAssertFalse(level.hint?.isEmpty ?? true, "\(level.id): every board in the pack ships with a hint")
            XCTAssertFalse(level.hintFocusNodeIDs.isEmpty, level.id)
            // Planning only: nothing here needs a tap during the run, a light or ice.
            XCTAssertTrue(level.liveSwitchNodeIDs.isEmpty && level.signals.isEmpty && level.roadZones.isEmpty, level.id)
            XCTAssertEqual(level.houses.count, level.vans.count, level.id)
            for node in level.graph.nodes {
                XCTAssertTrue((0...4).contains(node.x) && (0...6).contains(node.y), "\(level.id) \(node.id)")
                XCTAssertLessThanOrEqual(node.outgoingEdgeIDs.count, 2, "\(level.id) \(node.id)")
            }
            let switches = level.graph.nodes.filter { $0.outgoingEdgeIDs.count > 1 }.map(\.id)
            XCTAssertEqual(Set(level.initialSwitchEdges.keys), Set(switches), level.id)

            // The recorded script wins at par with everything delivered, and help's
            // last step reads the same script from the app.
            let script = try PrototypeSolutionScript.load(levelID: level.id)
            let engine = try PrototypeSolutionRunner.verify(level: level, script: script)
            XCTAssertEqual(engine.outcome, .win, level.id)
            XCTAssertEqual(MultiVanStars.rating(changes: engine.changeCount, par: level.parChanges), 3, level.id)
            for package in level.packages {
                XCTAssertEqual(engine.packageStates[package.id], .delivered, "\(level.id): \(package.id)")
            }
            XCTAssertEqual(MultiVanSolution.load(levelID: level.id, bundle: Boards.appBundle)?.planTaps, script.planTaps, level.id)
            // The untouched board never wins.
            XCTAssertNotEqual(Boards.run(try Boards.engine(level), seconds: 40).engine.outcome, .win, level.id)
        }
    }

    func testPromotedPickupBoardsAreTheTrialBoardsUnderCampaignIDs() throws {
        for (campaignID, trialID) in [("level_015", "experiment_pickup_a"), ("level_016", "experiment_pickup_b")] {
            var promoted = try Boards.json(campaignID)
            var trial = try Boards.json(trialID)
            XCTAssertEqual(promoted.removeValue(forKey: "id") as? String, campaignID)
            XCTAssertEqual(trial.removeValue(forKey: "id") as? String, trialID)
            // Same roads, vans, parcels, settings, par and words: what the trial
            // boards' tests prove holds for these too.
            XCTAssertEqual(promoted as NSDictionary, trial as NSDictionary, campaignID)
        }
        // Still pinned directly, so the campaign copy cannot drift from the lesson.
        let first = try table("level_015", switches: ["fork"])
        XCTAssertEqual(first.mapValues { Boards.name($0.engine.outcome) }, ["direct": "missingPackage", "tour": "win"])
        let second = try table("level_016", switches: ["red_fork", "blue_fork"])
        XCTAssertEqual(second.mapValues { Boards.name($0.engine.outcome) }, [
            "red_direct blue_short": "missingPackage",
            "red_direct blue_long": "missingPackage",
            "red_tour blue_short": "crash",
            "red_tour blue_long": "win",
        ])
        XCTAssertGreaterThan(try XCTUnwrap(second["red_tour blue_long"]).closestApproach, 1.0)
    }

    func testEveryBoardInThePackReplaysTheSameAcrossFramePartitionsAndSpeeds() throws {
        for id in Self.packIDs {
            let level = try level(id)
            let script = try PrototypeSolutionScript.load(levelID: id)
            // The recorded win, and the untouched board's failure or endless loop.
            for taps in [script.planTaps, []] {
                var reference: (MultiVanEngine.Outcome?, TimeInterval, [MultiVanEvent])?
                // Regular frames, uneven frames, and 2× in whole and split frames.
                for frames in [[1.0 / 120], [1.0 / 60], [1.0 / 30, 1.0 / 240, 0.019], [2.0 / 60], [0.25, 0.003]] {
                    let engine = try MultiVanEngine(level: level)
                    for nodeID in taps { XCTAssertEqual(engine.tapSwitch(nodeID: nodeID), .accepted, "\(id) \(nodeID)") }
                    _ = engine.drainEvents()
                    engine.go()
                    var events = engine.drainEvents()
                    var index = 0
                    // Twenty seconds of simulation is past every outcome in the pack.
                    while engine.phase == .run, engine.runTime < 20 {
                        engine.advance(by: min(frames[index % frames.count], 20 - engine.runTime))
                        events += engine.drainEvents()
                        index += 1
                    }
                    if let reference {
                        XCTAssertEqual(engine.outcome, reference.0, "\(id) \(taps) \(frames)")
                        XCTAssertEqual(engine.runTime, reference.1, accuracy: 1e-9, "\(id) \(taps) \(frames)")
                        XCTAssertEqual(events, reference.2, "\(id) \(taps) \(frames)")
                    } else {
                        reference = (engine.outcome, engine.runTime, events)
                    }
                }
            }
        }
    }

    // MARK: - 17 Around the Block

    func testAroundTheBlockNeedsTheFarSideAndThenTheTurnForHome() throws {
        let level = try level("level_017")
        let runs = try table(level.id, switches: ["approach_fork", "return_fork"])
        XCTAssertEqual(runs.mapValues { Boards.name($0.engine.outcome) }, [
            "near_side around_again": "unfinished",
            "near_side home": "missingPackage",
            "far_side around_again": "unfinished",
            "far_side home": "win",
        ])
        // Two taps is the least that wins: the one win is both switches changed.
        XCTAssertEqual(level.initialSwitchEdges, ["approach_fork": "near_side", "return_fork": "around_again"])
        XCTAssertEqual(try XCTUnwrap(runs["far_side home"]).engine.changeCount, level.parChanges)

        // The near side ends beside the parcel, one junction downstream of it,
        // and no road leads back up the street.
        let graph = try MultiVanEngine(level: level).runtimeGraph
        XCTAssertEqual(graph.edgesByID["near_side"]?.toNodeID, "block_corner")
        XCTAssertEqual(graph.edgesByID["street_end"]?.fromNodeID, "pickup")
        XCTAssertEqual(graph.edgesByID["street_end"]?.toNodeID, "block_corner")
        XCTAssertFalse(graph.edgesByID.values.contains { $0.fromNodeID == "block_corner" && $0.toNodeID == "pickup" })

        // Each wrong plan says what is wrong before Go.
        let untouched = try Boards.engine(level)
        XCTAssertEqual(untouched.previewRoutes[0].ending, .loopLimit)
        XCTAssertTrue(untouched.previewRoutes[0].missingPackageIDs.isEmpty, "the lap does pass the parcel")
        XCTAssertEqual(MultiVanRoutePreview.summary(for: level.vans[0], route: untouched.previewRoutes[0], level: level),
                       "Red van collects its parcel, then keeps circling: this route is not finished.")
        let shortcut = try Boards.engine(level, selections: ["return_fork": "home"])
        XCTAssertEqual(shortcut.previewRoutes[0].ending, .missingPackage)
        XCTAssertEqual(shortcut.previewRoutes[0].missingPackageIDs, ["red_parcel"])
        XCTAssertEqual(try XCTUnwrap(runs["near_side home"]).engine.outcome,
                       .failMissingPackage(vanID: "red", packageID: "red_parcel", pickupNodeID: "pickup"))

        // The endless lap is safe: the parcel is aboard, and Stop puts it back
        // and keeps the plan.
        let lap = try XCTUnwrap(runs["near_side around_again"]).engine
        XCTAssertEqual(lap.phase, .run)
        XCTAssertEqual(lap.vans[0].status, .driving)
        XCTAssertEqual(lap.cargoStatus(forVanID: "red"), .carrying)
        lap.stop()
        XCTAssertEqual(lap.packageStates, ["red_parcel": .atPickup])
        XCTAssertEqual(lap.runtimeGraph.nodesByID["return_fork"]?.activeOutgoingEdgeID, "around_again")

        // The win collects once and delivers once.
        let win = try XCTUnwrap(runs["far_side home"])
        XCTAssertEqual(win.events.filter { if case .pickedUp = $0 { true } else { false } }.count, 1)
        XCTAssertEqual(win.events.filter { if case .delivered = $0 { true } else { false } }.count, 1)
        XCTAssertEqual(win.events.last, .allDelivered)
    }

    // MARK: - 18 Two Good Plans

    func testTwoGoodPlansHasExactlyTwoWinsAndBothEarnFullStars() throws {
        let level = try level("level_018")
        XCTAssertTrue(level.packages.isEmpty)
        XCTAssertEqual(level.schemaVersion, 1)
        let switches = ["red_fork", "blue_fork", "top_switch", "bottom_switch"]
        let runs = try table(level.id, switches: switches)
        XCTAssertEqual(runs.count, 16)
        let wins = runs.filter { $0.value.engine.outcome == .win }
        // One van over the top, the other round the bottom, each middle switch
        // set for the van that uses it. Either van can take either road.
        XCTAssertEqual(Set(wins.keys), [
            "red_top blue_round top_to_red bottom_to_blue",
            "red_round blue_top top_to_blue bottom_to_red",
        ])
        for (key, run) in runs {
            switch run.engine.outcome {
            case .win:
                XCTAssertEqual(run.engine.changeCount, level.parChanges, key)
                XCTAssertEqual(MultiVanStars.rating(changes: run.engine.changeCount, par: level.parChanges), 3, key)
                // The two vans never share a road in a winning plan.
                XCTAssertGreaterThan(run.closestApproach, 1.5, key)
            case .failWrongHouse:
                // Every other plan sends a van to the other colour's house, and
                // the preview shows that before Go.
                let planned = try Boards.engine(level, selections: Dictionary(uniqueKeysWithValues: zip(switches, key.split(separator: " ").map(String.init))))
                XCTAssertTrue(planned.previewRoutes.contains { $0.ending == .wrongHouse }, key)
                // Two vans on one road follow each other; they never touch.
                XCTAssertGreaterThanOrEqual(run.closestApproach, 1.0 - 1e-6, key)
            default:
                XCTFail("\(key): \(Boards.name(run.engine.outcome)) — this board has no crash, dead end or loop")
            }
        }
        // A shared switch has one setting for both vans: with both on one road,
        // neither setting of its switch delivers the pair.
        for shared in ["red_top blue_top", "red_round blue_round"] {
            XCTAssertTrue(runs.filter { $0.key.hasPrefix(shared) }.allSatisfy { $0.value.engine.outcome != .win }, shared)
        }

        // The recorded script is one plan; the other is proved here, tap for tap.
        XCTAssertEqual(try PrototypeSolutionScript.load(levelID: level.id).planTaps, ["blue_fork", "bottom_switch"])
        let other = try PrototypeSolutionRunner.verify(level: level, script: .init(planTaps: ["red_fork", "top_switch"]))
        XCTAssertEqual(other.outcome, .win)
        XCTAssertEqual(other.changeCount, level.parChanges)
        // No single tap wins, so par is the least for either plan.
        XCTAssertTrue(wins.allSatisfy { $0.value.engine.changeCount == 2 })
        XCTAssertFalse(runs.contains { $0.value.engine.changeCount < 2 && $0.value.engine.outcome == .win })
    }

    // MARK: - 19 Neighborhood Round

    func testNeighborhoodRoundNeedsBothPickupsAndThenTheRoadThatClearsTheCrossing() throws {
        let level = try level("level_019")
        XCTAssertEqual(level.packages(ownedBy: "red").map(\.id), ["red_parcel"])
        XCTAssertEqual(level.packages(ownedBy: "blue").map(\.id), ["blue_parcel"])
        let switches = ["red_fork", "way_fork", "blue_fork"]
        let runs = try table(level.id, switches: switches)
        XCTAssertEqual(runs.mapValues { Boards.name($0.engine.outcome) }, [
            "red_direct way_long blue_direct": "missingPackage",
            "red_direct way_short blue_direct": "missingPackage",
            "red_direct way_long blue_tour": "missingPackage",
            "red_direct way_short blue_tour": "missingPackage",
            "red_tour way_long blue_direct": "missingPackage",
            "red_tour way_short blue_direct": "missingPackage",
            "red_tour way_long blue_tour": "crash",
            "red_tour way_short blue_tour": "win",
        ])
        XCTAssertEqual(level.initialSwitchEdges, ["red_fork": "red_direct", "way_fork": "way_long", "blue_fork": "blue_direct"])

        for (key, run) in runs {
            let engine = run.engine
            switch engine.outcome {
            case .win:
                // All three switches changed: nothing cheaper wins. Not a near miss.
                XCTAssertEqual(engine.changeCount, level.parChanges, key)
                XCTAssertGreaterThan(run.closestApproach, 1.5, key)
                XCTAssertEqual(engine.packageStates, ["red_parcel": .delivered, "blue_parcel": .delivered])
                XCTAssertEqual(run.events.filter { if case .pickedUp = $0 { true } else { false } }.count, 2)
                XCTAssertEqual(run.events.last, .allDelivered)
            case let .failCrash(vanIDs, point):
                // Both parcels are aboard and both routes read as complete: what
                // is left to decide is traffic, at the one crossing.
                XCTAssertEqual(vanIDs, ["red", "blue"], key)
                XCTAssertEqual(point.x, 3, accuracy: 0.3, key)
                XCTAssertEqual(point.y, 5, accuracy: 0.3, key)
                XCTAssertEqual(engine.packageStates, ["red_parcel": .carried, "blue_parcel": .carried], key)
                let planned = try Boards.engine(level, selections: ["red_fork": "red_tour", "blue_fork": "blue_tour"])
                XCTAssertTrue(planned.previewRoutes.allSatisfy(\.isComplete), key)
            case let .failMissingPackage(vanID, packageID, _):
                // A skipped pickup is reported at the house, with no crash on the
                // way to hide it, and names the van that skipped.
                XCTAssertEqual(packageID, "\(vanID)_parcel", key)
                XCTAssertEqual(vanID, key.contains("red_direct") ? "red" : "blue", key)
                XCTAssertGreaterThan(run.closestApproach, 1.0, key)
            default:
                XCTFail("\(key): \(Boards.name(engine.outcome))")
            }
        }

        // Only the owner collects: Blue's trip never touches Red's parcel.
        let blueOnly = try XCTUnwrap(runs["red_direct way_long blue_tour"])
        XCTAssertEqual(blueOnly.engine.packageStates["red_parcel"], .atPickup)
        // The crash tip points at the switch that fixes it.
        XCTAssertEqual(level.tutorialTip(for: .crash)?.focusNodeIDs, ["way_fork"])
        XCTAssertNil(level.tutorialTip(for: .start))
    }

    func testPickupMarkersInThePackStandClearOfEveryRoad() throws {
        for id in Self.packIDs {
            let level = try level(id)
            let engine = try MultiVanEngine(level: level)
            XCTAssertEqual(MultiVanPickup.pickups(engine: engine).count, level.packages.count, id)
            for pickup in MultiVanPickup.pickups(engine: engine) {
                for edge in engine.runtimeGraph.edgesByID.values {
                    for distance in stride(from: 0, through: edge.roadPath.totalLength, by: 0.05) {
                        let point = edge.roadPath.point(atDistance: distance)
                        XCTAssertGreaterThan(hypot(point.x - pickup.point.x, point.y - pickup.point.y), 0.3,
                                             "\(id): \(pickup.id) sits on road \(edge.id)")
                    }
                }
            }
        }
    }
}
