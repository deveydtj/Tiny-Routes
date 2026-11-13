import XCTest
@testable import TinyRoutes

/// Package pickup: definitions, the engine's lifecycle, the cargo-aware preview,
/// and the three experiment boards.
final class MultiVanCargoTests: XCTestCase {
    private typealias Boards = MultiVanTestBoards

    // MARK: - Definitions and content checks

    func testOriginalCampaignLevelsDecodeAsBeforeWithNoPackages() throws {
        // Levels 15 on are the content pack; see `MultiVanContentPackTests`.
        let levels = try MultiVanLevelRepository(bundle: Boards.appBundle).loadAllLevels().prefix(14)
        XCTAssertEqual(levels.last?.id, "level_014")
        for level in levels {
            XCTAssertEqual(level.schemaVersion, 1, level.id)
            XCTAssertTrue(level.packages.isEmpty, level.id)
            XCTAssertTrue(level.signals.isEmpty && level.roadZones.isEmpty, level.id)
            XCTAssertEqual(level.biome, .meadow, level.id)
            XCTAssertFalse(level.id.hasPrefix(MultiVanLevelRepository.experimentPrefix))
            let engine = try MultiVanEngine(level: level)
            XCTAssertTrue(engine.packageStates.isEmpty, level.id)
            for van in level.vans { XCTAssertEqual(engine.cargoStatus(forVanID: van.id), .ready, level.id) }
        }
    }

    func testPackagesNeedTheirSchemaVersionAndNewerFilesAreRefused() throws {
        var json = try Boards.json("experiment_pickup_a")
        XCTAssertEqual(try Boards.level(json).packages.map(\.id), ["red_parcel"])
        json["schemaVersion"] = 1
        XCTAssertThrowsError(try Boards.level(json)) { XCTAssertTrue("\($0)".contains("packages need schemaVersion 2")) }
        json.removeValue(forKey: "schemaVersion")
        XCTAssertThrowsError(try Boards.level(json))
        json["schemaVersion"] = MultiVanLevel.supportedSchemaVersion + 1
        XCTAssertThrowsError(try Boards.level(json)) { XCTAssertTrue("\($0)".contains("not supported")) }
        // An unknown biome is art the app lacks, never a reason to refuse a board.
        json["schemaVersion"] = 2
        json["biome"] = "moon"
        XCTAssertEqual(try Boards.level(json).biome, .meadow)
    }

    func testEngineRefusesBrokenPackageDefinitions() throws {
        func error(_ packages: [[String: Any]], vans: [[String: Any]]? = nil) -> MultiVanLevelError? {
            do {
                var json = try Boards.json("experiment_pickup_a")
                json["packages"] = packages
                if let vans { json["vans"] = vans }
                _ = try MultiVanEngine(level: Boards.level(json))
                return nil
            } catch {
                return error as? MultiVanLevelError
            }
        }
        let parcel: [String: Any] = ["id": "p", "nodeID": "pickup", "ownerVanID": "red"]
        XCTAssertNil(error([parcel]))
        XCTAssertEqual(error([parcel, parcel]), .duplicatePackage("p"))
        XCTAssertEqual(error([parcel.merging(["id": ""]) { $1 }]), .emptyPackageID)
        XCTAssertEqual(error([parcel.merging(["ownerVanID": "ghost"]) { $1 }]), .packageOwnerMissing(packageID: "p", vanID: "ghost"))
        XCTAssertEqual(error([parcel.merging(["nodeID": "nowhere"]) { $1 }]), .packageNodeMissing(packageID: "p", nodeID: "nowhere"))
        let three = (1...3).map { parcel.merging(["id": "p\($0)"]) { $1 } }
        XCTAssertEqual(error(three), .tooManyPackages(vanID: "red", count: 3))
        let red: [String: Any] = ["id": "red", "color": "red", "startNodeID": "start"]
        XCTAssertEqual(error([parcel], vans: [red, red]), .duplicateVan("red"))

        var json = try Boards.json("experiment_pickup_a")
        var graph = try XCTUnwrap(json["graph"] as? [String: Any])
        var edges = try XCTUnwrap(graph["edges"] as? [[String: Any]])
        edges[0]["availability"] = "afterPackage"
        graph["edges"] = edges
        json["graph"] = graph
        XCTAssertThrowsError(try MultiVanEngine(level: Boards.level(json))) {
            XCTAssertEqual($0 as? MultiVanLevelError, .unsupportedEdgeRule(edgeID: edges[0]["id"] as! String))
        }
    }

    func testAuthoringPolicyRejectsCrowdedOrUnreachablePickups() throws {
        func issues(_ mutate: (inout [String: Any]) -> Void) throws -> [String] {
            var json = try Boards.json("experiment_pickup_a")
            mutate(&json)
            return MultiVanLevelRules.authoringIssues(in: try Boards.level(json))
        }
        XCTAssertEqual(try issues { _ in }, [])
        let parcel = { (id: String, node: String) -> [String: Any] in ["id": id, "nodeID": node, "ownerVanID": "red"] }
        XCTAssertTrue(try issues { $0["packages"] = [parcel("p", "fork")] }.contains { $0.contains("sits on a switch") })
        XCTAssertTrue(try issues { $0["packages"] = [parcel("p", "start")] }.contains { $0.contains("sits on a van's start") })
        XCTAssertTrue(try issues { $0["packages"] = [parcel("p", "house")] }.contains { $0.contains("sits on a house") })
        XCTAssertTrue(try issues { $0["packages"] = [parcel("p", "pickup"), parcel("q", "pickup")] }
            .contains { $0.contains("shares node pickup") })
        XCTAssertTrue(try issues { $0.removeValue(forKey: "hint") }.contains { $0.contains("needs a hint") })
        XCTAssertTrue(try issues { $0["hintFocusNodeIDs"] = ["join"] }.contains { $0.contains("not a switch") })
        // A pickup past the house: the roads to collect it and still get home do not exist.
        let stranded = try Boards.board(
            nodes: [("start", 0, 0), ("house", 0, 2), ("far", 2, 2)],
            edges: [("home", "start", "house")],
            vans: [["id": "red", "color": "red", "startNodeID": "start"]], houses: [("house", "red")],
            packages: [["id": "p", "nodeID": "far", "ownerVanID": "red"]], extra: ["hint": "x"]
        )
        XCTAssertTrue(MultiVanLevelRules.authoringIssues(in: stranded).contains { $0.contains("cannot reach its pickups") })
    }

    func testEveryExperimentBoardLoadsPassesPolicyAndItsScriptWinsAtPar() throws {
        let experiments = try Boards.experiments()
        XCTAssertFalse(experiments.isEmpty)
        for level in experiments {
            XCTAssertTrue(level.id.hasPrefix(MultiVanLevelRepository.experimentPrefix), level.id)
            XCTAssertEqual(MultiVanLevelRules.authoringIssues(in: level), [], level.id)
            XCTAssertNotNil(level.hint, "\(level.id): every new board ships with a hint")
            let script = try PrototypeSolutionScript.load(levelID: level.id)
            let engine = try PrototypeSolutionRunner.verify(level: level, script: script)
            XCTAssertEqual(engine.outcome, .win, level.id)
            for package in level.packages {
                XCTAssertEqual(engine.packageStates[package.id], .delivered, "\(level.id): \(package.id)")
            }
        }
    }

    // MARK: - Experiment A

    func testExperimentAPickupRouteCollectsOnceAndDeliversOnce() throws {
        let level = try Boards.experiment("experiment_pickup_a")
        let engine = try Boards.engine(level, selections: ["fork": "tour"])
        XCTAssertEqual(engine.cargoStatus(forVanID: "red"), .pickupNeeded(remaining: level.packages))
        XCTAssertEqual(engine.previewRoutes[0].ending, .matchingHouse)
        XCTAssertEqual(engine.previewRoutes[0].collectedPackageIDs, ["red_parcel"])
        XCTAssertEqual(engine.packageStates, ["red_parcel": .atPickup], "a traced pickup takes nothing off the board")

        let run = Boards.run(engine)
        XCTAssertEqual(engine.outcome, .win)
        XCTAssertEqual(engine.packageStates, ["red_parcel": .delivered])
        XCTAssertEqual(engine.cargoStatus(forVanID: "red"), .delivered)
        let pickups = run.events.filter { if case .pickedUp = $0 { true } else { false } }
        XCTAssertEqual(pickups.count, 1)
        guard case let .pickedUp(vanID, packageID, tick)? = pickups.first else { return XCTFail("no pickup event") }
        XCTAssertEqual([vanID, packageID], ["red", "red_parcel"])
        // The pickup is 1 + 2.923 units from the start: the step the van arrives on.
        let road = try XCTUnwrap(engine.runtimeGraph.edgesByID["tour"]).roadPath.totalLength
        let arrival = Int(((1 + road) / (engine.tuning.vanSpeed * engine.tuning.stepDuration)).rounded(.up))
        XCTAssertEqual(tick, arrival)
        XCTAssertEqual(run.events.filter { if case .delivered = $0 { true } else { false } }.count, 1)
        // Collection comes before the delivery it makes possible.
        let order = run.events.compactMap { event -> String? in
            switch event {
            case .pickedUp: "pickup"
            case .delivered: "delivered"
            case .allDelivered: "all"
            default: nil
            }
        }
        XCTAssertEqual(order, ["pickup", "delivered", "all"])
        let house = try XCTUnwrap(level.houses.first)
        XCTAssertTrue(MultiVanBoardRules.isDelivered(house, vans: engine.vans, graph: engine.runtimeGraph))
    }

    func testExperimentABypassFailsAtTheHouseWithoutCreditAndPreviewSaysSoFirst() throws {
        let level = try Boards.experiment("experiment_pickup_a")
        let engine = try Boards.engine(level)
        // The preview names the missing parcel before any run.
        XCTAssertEqual(engine.previewRoutes[0].ending, .missingPackage)
        XCTAssertEqual(engine.previewRoutes[0].missingPackageIDs, ["red_parcel"])
        XCTAssertFalse(engine.previewRoutes[0].isComplete)
        XCTAssertEqual(MultiVanPreviewMarker.make(routes: engine.previewRoutes, vans: level.vans, graph: engine.runtimeGraph)[0]?.glyph, "✗")
        XCTAssertTrue(MultiVanPickup.pickups(engine: engine)[0].isMissed)

        let run = Boards.run(engine)
        XCTAssertEqual(engine.outcome, .failMissingPackage(vanID: "red", packageID: "red_parcel", pickupNodeID: "pickup"))
        XCTAssertEqual(engine.vans[0].status, .missingCargo)
        XCTAssertEqual(engine.packageStates, ["red_parcel": .atPickup])
        XCTAssertEqual(engine.cargoStatus(forVanID: "red"), .pickupNeeded(remaining: level.packages))
        XCTAssertFalse(MultiVanBoardRules.isDelivered(level.houses[0], vans: engine.vans, graph: engine.runtimeGraph))
        XCTAssertTrue(run.events.contains(.missingPackage(vanID: "red", packageID: "red_parcel")))
        for event in run.events {
            switch event {
            case .delivered, .allDelivered, .pickedUp: XCTFail("\(event) on an empty arrival")
            default: break
            }
        }
        XCTAssertEqual(MultiVanFailureCopy.message(for: try XCTUnwrap(engine.outcome), level: level),
                       "Red got home without its parcel! Pick it up first.")
        // The failure points at the house the van reached empty.
        XCTAssertEqual(engine.lastFailPoint, RoadPoint(x: 2, y: 6))
    }

    func testExperimentAResetsRestoreTheParcelAndKeepSelections() throws {
        let level = try Boards.experiment("experiment_pickup_a")
        let engine = try Boards.engine(level, selections: ["fork": "tour"])
        let selected = { engine.runtimeGraph.nodesByID["fork"]?.activeOutgoingEdgeID }

        // Stop before the pickup.
        engine.go()
        engine.advance(by: 0.5)
        XCTAssertEqual(engine.packageStates["red_parcel"], .atPickup)
        engine.stop()
        XCTAssertEqual(engine.packageStates["red_parcel"], .atPickup)
        XCTAssertEqual(selected(), "tour")

        // Stop after the pickup: the parcel is back, the selection stays.
        engine.go()
        engine.advance(by: 3.5)
        XCTAssertEqual(engine.packageStates["red_parcel"], .carried)
        XCTAssertEqual(engine.cargoStatus(forVanID: "red"), .carrying)
        engine.stop()
        XCTAssertEqual(engine.phase, .plan)
        XCTAssertEqual(engine.packageStates["red_parcel"], .atPickup)
        XCTAssertEqual(selected(), "tour")
        XCTAssertEqual(engine.previewRoutes[0].ending, .matchingHouse)

        // Replay after a win starts from a full board again.
        XCTAssertEqual(Boards.run(engine).engine.outcome, .win)
        engine.retry()
        XCTAssertEqual(engine.packageStates["red_parcel"], .atPickup)
        XCTAssertEqual(selected(), "tour")
        XCTAssertEqual(Boards.run(engine).engine.outcome, .win)
        XCTAssertEqual(engine.packageStates["red_parcel"], .delivered)

        // Retry after the empty arrival clears its status and keeps the failing plan.
        engine.retry()
        try Boards.select(["fork": "direct"], in: engine)
        Boards.run(engine)
        XCTAssertEqual(engine.vans[0].status, .missingCargo)
        engine.retry()
        XCTAssertEqual(engine.vans[0].status, .waiting)
        XCTAssertEqual(engine.packageStates["red_parcel"], .atPickup)
        XCTAssertEqual(selected(), "direct")
        XCTAssertEqual(engine.lastFailPoint, RoadPoint(x: 2, y: 6), "the failure point stays until the next Go")

        // Reset switches is a different action: authored settings, parcels untouched.
        try Boards.select(["fork": "tour"], in: engine)
        engine.resetSwitches()
        XCTAssertEqual(selected(), "direct")
        XCTAssertEqual(engine.packageStates["red_parcel"], .atPickup)
    }

    func testExperimentAReplaysTheSameAcrossFramePartitionsAndSpeeds() throws {
        let level = try Boards.experiment("experiment_pickup_a")
        for selections in [["fork": "tour"], ["fork": "direct"]] {
            var reference: (MultiVanEngine.Outcome?, TimeInterval, [MultiVanEvent])?
            // Regular frames, uneven frames, and 2× in whole and split frames.
            for frames in [[1.0 / 120], [1.0 / 60], [1.0 / 30, 1.0 / 240, 0.019], [2.0 / 60], [0.25, 0.003]] {
                let engine = try Boards.engine(level, selections: selections)
                engine.go()
                var events = engine.drainEvents()
                var index = 0
                while engine.phase == .run, index < 100_000 {
                    engine.advance(by: frames[index % frames.count])
                    events += engine.drainEvents()
                    index += 1
                }
                if let reference {
                    XCTAssertEqual(engine.outcome, reference.0, "\(selections) \(frames)")
                    XCTAssertEqual(engine.runTime, reference.1, accuracy: 1e-9, "\(selections) \(frames)")
                    XCTAssertEqual(events, reference.2, "\(selections) \(frames)")
                } else {
                    reference = (engine.outcome, engine.runTime, events)
                }
            }
        }
    }

    // MARK: - Experiments B and C

    private let streets = [
        (red: "red_direct", blue: "blue_short"), (red: "red_direct", blue: "blue_long"),
        (red: "red_tour", blue: "blue_short"), (red: "red_tour", blue: "blue_long"),
    ]

    private func outcomes(_ id: String) throws -> [(String, MultiVanTestBoards.Run)] {
        let level = try Boards.experiment(id)
        XCTAssertEqual(Boards.configurations(of: level).count, 4)
        return try streets.map { pair in
            let engine = try Boards.engine(level, selections: ["red_fork": pair.red, "blue_fork": pair.blue])
            let run = Boards.run(engine)
            return (Boards.name(engine.outcome), run)
        }
    }

    func testExperimentBOnlyPickupWithBlueLongWinsAndEachFailureHasItsOwnCause() throws {
        let level = try Boards.experiment("experiment_pickup_b")
        let results = try outcomes(level.id)
        XCTAssertEqual(results.map(\.0), ["missingPackage", "missingPackage", "crash", "win"])

        // Empty routes reach the house and say why, with no earlier crash to hide it.
        for index in 0...1 {
            let engine = results[index].1.engine
            XCTAssertEqual(engine.outcome, .failMissingPackage(vanID: "red", packageID: "red_parcel", pickupNodeID: "pickup"))
            XCTAssertEqual(engine.runTime, 4.0, accuracy: 1e-9)
            XCTAssertEqual(engine.vans[1].status, .driving, "Blue is still on its way")
        }
        // Cargo-valid routes that still collide: ✓ never promised safe traffic.
        let crash = results[2].1.engine
        let planned = try Boards.engine(level, selections: ["red_fork": "red_tour", "blue_fork": "blue_short"])
        XCTAssertTrue(planned.previewRoutes.allSatisfy(\.isComplete))
        guard case let .failCrash(vanIDs, point) = crash.outcome else { return XCTFail("expected a crash") }
        XCTAssertEqual(vanIDs, ["red", "blue"])
        XCTAssertEqual(point.x, 2, accuracy: 0.3)
        XCTAssertEqual(point.y, 4, accuracy: 0.3)
        XCTAssertEqual(crash.packageStates["red_parcel"], .carried, "the pickup stays collected on a failed attempt")

        // The winner is not a near miss: the vans stay well over a crash apart.
        let win = results[3].1
        XCTAssertEqual(win.engine.outcome, .win)
        XCTAssertGreaterThan(win.closestApproach, 1.0)
        XCTAssertEqual(win.engine.changeCount, level.parChanges)
        // Blue is ready from the start and never touches Red's parcel.
        XCTAssertEqual(win.engine.cargoStatus(forVanID: "blue"), .ready)
        XCTAssertEqual(win.events.filter { if case .pickedUp = $0 { true } else { false } }.count, 1)
        // No early win when the first van parks.
        let deliveries = win.events.compactMap { event -> Int? in
            if case let .delivered(_, combo) = event { combo } else { nil }
        }
        XCTAssertEqual(deliveries, [1, 2])
        XCTAssertEqual(win.events.filter { $0 == .allDelivered }.count, 1)
        XCTAssertEqual(win.events.last, .allDelivered)
    }

    func testExperimentCMatchesBExceptThatNoParcelIsNeeded() throws {
        let cargo = try Boards.experiment("experiment_pickup_b")
        let control = try Boards.experiment("experiment_pickup_c")
        // The same streets: every road, start, delay, switch and setting.
        XCTAssertEqual(control.graph.nodes.map(\.id), cargo.graph.nodes.map(\.id))
        XCTAssertEqual(control.graph.edges.map(\.id), cargo.graph.edges.map(\.id))
        XCTAssertEqual(control.vans.map(\.departDelay), cargo.vans.map(\.departDelay))
        XCTAssertEqual(control.initialSwitchEdges, cargo.initialSwitchEdges)
        XCTAssertTrue(control.packages.isEmpty)
        XCTAssertEqual(control.schemaVersion, 1)

        let withCargo = try outcomes(cargo.id)
        let without = try outcomes(control.id)
        XCTAssertEqual(without.map(\.0), ["win", "win", "crash", "win"])
        // The two boards differ exactly where cargo decides the outcome.
        for index in streets.indices {
            let differs = withCargo[index].0 != without[index].0
            XCTAssertEqual(differs, withCargo[index].0 == "missingPackage", "\(streets[index])")
        }
        // The same routes meet at the same place at the same time.
        XCTAssertEqual(without[2].1.engine.outcome, withCargo[2].1.engine.outcome)
        XCTAssertEqual(without[2].1.engine.runTime, withCargo[2].1.engine.runTime, accuracy: 1e-12)
        XCTAssertEqual(without[3].1.closestApproach, withCargo[3].1.closestApproach, accuracy: 1e-12)
        XCTAssertEqual(without[3].1.engine.runTime, withCargo[3].1.engine.runTime, accuracy: 1e-12)
        for (_, run) in without {
            XCTAssertTrue(run.engine.packageStates.isEmpty)
            for event in run.events {
                switch event {
                case .pickedUp, .missingPackage: XCTFail("\(event) on a board with no parcels")
                default: break
                }
            }
        }
        // Authored settings already win here: the shortcut B forbids is the answer.
        XCTAssertEqual(control.parChanges, 0)
    }

    func testExperimentBRetryKeepsSelectionsAndReplaysDeterministically() throws {
        let level = try Boards.experiment("experiment_pickup_b")
        let engine = try Boards.engine(level, selections: ["red_fork": "red_tour", "blue_fork": "blue_short"])
        let first = Boards.run(engine)
        engine.retry()
        XCTAssertEqual(engine.runtimeGraph.nodesByID["red_fork"]?.activeOutgoingEdgeID, "red_tour")
        XCTAssertEqual(engine.runtimeGraph.nodesByID["blue_fork"]?.activeOutgoingEdgeID, "blue_short")
        XCTAssertEqual(engine.packageStates["red_parcel"], .atPickup)
        // Uneven frames and 2× reach the same crash on the same step.
        let second = Boards.run(engine, frame: 1.0 / 37)
        XCTAssertEqual(second.engine.outcome, first.engine.outcome)
        XCTAssertEqual(second.events, first.events)
        engine.retry()
        XCTAssertEqual(engine.tapSwitch(nodeID: "blue_fork"), .accepted)
        XCTAssertEqual(Boards.run(engine, frame: 2.0 / 60).engine.outcome, .win)
    }

    // MARK: - Arrival and lifecycle fixtures

    private func red(_ start: String, delay: Double = 0) -> [String: Any] {
        ["id": "red", "color": "red", "startNodeID": start, "departDelay": delay]
    }

    private func blue(_ start: String, delay: Double = 0) -> [String: Any] {
        ["id": "blue", "color": "blue", "startNodeID": start, "departDelay": delay]
    }

    func testPickupOnTheStartIsCollectedOnlyWhenTheVanDeparts() throws {
        let level = try Boards.board(
            nodes: [("start", 0, 0), ("house", 0, 2)], edges: [("home", "start", "house")],
            vans: [red("start", delay: 1)], houses: [("house", "red")],
            packages: [["id": "p", "nodeID": "start", "ownerVanID": "red"]]
        )
        let engine = try MultiVanEngine(level: level)
        // Planning never collects, however long the player waits.
        XCTAssertEqual(engine.packageStates["p"], .atPickup)
        XCTAssertEqual(engine.previewRoutes[0].collectedPackageIDs, ["p"])
        XCTAssertEqual(engine.previewRoutes[0].ending, .matchingHouse)
        engine.go()
        XCTAssertEqual(engine.packageStates["p"], .atPickup, "a delayed van has not left yet")
        engine.advance(by: 0.5)
        XCTAssertEqual(engine.packageStates["p"], .atPickup)
        engine.advance(by: 0.6)
        XCTAssertEqual(engine.packageStates["p"], .carried)
        let events = engine.drainEvents()
        XCTAssertTrue(events.contains(.pickedUp(vanID: "red", packageID: "p", tick: 120)), "\(events)")

        // With no delay the departure, and the pickup, happen at Go on step 0.
        let prompt = try MultiVanEngine(level: Boards.board(
            nodes: [("start", 0, 0), ("house", 0, 2)], edges: [("home", "start", "house")],
            vans: [red("start")], houses: [("house", "red")],
            packages: [["id": "p", "nodeID": "start", "ownerVanID": "red"]]
        ))
        prompt.go()
        XCTAssertEqual(prompt.drainEvents(), [.go, .pickedUp(vanID: "red", packageID: "p", tick: 0)])
    }

    func testPickupThenHouseInOneStepKeepsLeftoverDistance() throws {
        // Speed 240 covers both one-unit roads inside a single step.
        var tuning = MultiVanTuning.default
        tuning.vanSpeed = 240
        let level = try Boards.board(
            nodes: [("start", 0, 0), ("pickup", 0, 1), ("house", 0, 2)],
            edges: [("a", "start", "pickup"), ("b", "pickup", "house")],
            vans: [red("start")], houses: [("house", "red")],
            packages: [["id": "p", "nodeID": "pickup", "ownerVanID": "red"]]
        )
        let engine = try MultiVanEngine(level: level, tuning: tuning)
        engine.go()
        engine.advance(by: tuning.stepDuration)
        XCTAssertEqual(engine.outcome, .win)
        XCTAssertEqual(engine.packageStates["p"], .delivered)
        XCTAssertEqual(engine.drainEvents(), [
            .go, .pickedUp(vanID: "red", packageID: "p", tick: 1), .delivered(vanID: "red", comboIndex: 1), .allDelivered,
        ])
    }

    func testOnlyTheOwnerCollectsAndPassingAgainCollectsNothing() throws {
        // Blue drives through Red's pickup; Red laps its own pickup twice.
        let level = try Boards.board(
            nodes: [("blue_start", 4, 0), ("pickup", 4, 2), ("blue_house", 4, 4),
                    ("red_start", 0, 0), ("loop", 0, 1), ("red_pickup", 0, 3), ("back", 2, 3), ("red_house", 2, 6)],
            edges: [("b1", "blue_start", "pickup"), ("b2", "pickup", "blue_house"),
                    ("r1", "red_start", "loop"), ("lap", "loop", "red_pickup"), ("home", "loop", "red_house"),
                    ("r3", "red_pickup", "back"), ("r4", "back", "loop")],
            vans: [blue("blue_start"), red("red_start")],
            houses: [("blue_house", "blue"), ("red_house", "red")],
            packages: [["id": "blue_site", "nodeID": "pickup", "ownerVanID": "red"],
                       ["id": "lap", "nodeID": "red_pickup", "ownerVanID": "red"]],
            initial: ["loop": "lap"], live: ["loop"]
        )
        let engine = try MultiVanEngine(level: level)
        var run = Boards.run(engine, seconds: 14)
        // Blue parked after driving straight through a parcel that is not its own.
        XCTAssertEqual(engine.vans[0].status, .parked)
        XCTAssertEqual(engine.packageStates["blue_site"], .atPickup)
        XCTAssertEqual(engine.cargoStatus(forVanID: "blue"), .ready)
        // Red has lapped its pickup more than once and holds one parcel.
        XCTAssertEqual(engine.packageStates["lap"], .carried)
        XCTAssertEqual(run.events.filter { if case .pickedUp = $0 { true } else { false } },
                       [.pickedUp(vanID: "red", packageID: "lap", tick: 240)])
        XCTAssertEqual(engine.cargoStatus(forVanID: "red"),
                       .pickupNeeded(remaining: [level.packages[0]]), "one of two parcels is still out")
        // Sending Red home now is an empty arrival: both parcels were required.
        while engine.tapSwitch(nodeID: "loop") != .accepted { engine.advance(by: 0.05) }
        while engine.phase == .run { engine.advance(by: 0.05) }
        run.events += engine.drainEvents()
        XCTAssertEqual(engine.outcome, .failMissingPackage(vanID: "red", packageID: "blue_site", pickupNodeID: "pickup"))
        XCTAssertEqual(MultiVanFailureCopy.message(for: try XCTUnwrap(engine.outcome), level: level),
                       "Red got home without all its parcels! Pick it up first.")
    }

    func testTwoOwnersCollectingOnTheSameStepAreIndependentInAuthoredOrder() throws {
        func level(redFirst: Bool) throws -> MultiVanLevel {
            let vans = redFirst ? [red("rs"), blue("bs")] : [blue("bs"), red("rs")]
            return try Boards.board(
                nodes: [("rs", 0, 0), ("rp", 0, 2), ("rh", 0, 4), ("bs", 4, 0), ("bp", 4, 2), ("bh", 4, 4)],
                edges: [("r1", "rs", "rp"), ("r2", "rp", "rh"), ("b1", "bs", "bp"), ("b2", "bp", "bh")],
                vans: vans, houses: [("rh", "red"), ("bh", "blue")],
                packages: [["id": "rp", "nodeID": "rp", "ownerVanID": "red"], ["id": "bp", "nodeID": "bp", "ownerVanID": "blue"]]
            )
        }
        for redFirst in [true, false] {
            let run = Boards.run(try MultiVanEngine(level: level(redFirst: redFirst)))
            XCTAssertEqual(run.engine.outcome, .win)
            XCTAssertEqual(run.engine.packageStates, ["rp": .delivered, "bp": .delivered])
            let pickups = run.events.compactMap { event -> String? in
                if case let .pickedUp(vanID, packageID, tick) = event { "\(vanID):\(packageID):\(tick)" } else { nil }
            }
            // The same step for both; authored van order decides which event is first,
            // never who owns what.
            XCTAssertEqual(pickups, redFirst ? ["red:rp:160", "blue:bp:160"] : ["blue:bp:160", "red:rp:160"])
        }
    }

    func testWrongHouseStillComesFirstAndACrashAfterAPickupKeepsThePickup() throws {
        // Red reaches Blue's house empty: the wrong house is the failure reported.
        let wrong = try Boards.board(
            nodes: [("rs", 0, 0), ("bh", 0, 2), ("rp", 2, 0), ("rh", 2, 2), ("bs", 4, 0), ("far", 4, 6)],
            edges: [("r1", "rs", "bh"), ("x", "rp", "rh"), ("b1", "bs", "far")],
            vans: [red("rs"), blue("bs")], houses: [("bh", "blue"), ("rh", "red")],
            packages: [["id": "p", "nodeID": "rp", "ownerVanID": "red"]]
        )
        let wrongRun = Boards.run(try MultiVanEngine(level: wrong))
        XCTAssertEqual(wrongRun.engine.outcome, .failWrongHouse(vanID: "red", houseNodeID: "bh"))
        XCTAssertEqual(wrongRun.engine.vans[0].status, .parked)
        XCTAssertEqual(try MultiVanEngine(level: wrong).previewRoutes[0].ending, .wrongHouse)

        // Red collects, then meets Blue head-on: pickup first, crash after.
        let crash = try Boards.board(
            nodes: [("rs", 0, 0), ("rp", 0, 1), ("rh", 0, 6), ("bs", 0, 5), ("bh", 0, 2)],
            edges: [("r1", "rs", "rp"), ("r2", "rp", "rh"), ("b1", "bs", "bh")],
            vans: [red("rs"), blue("bs")], houses: [("rh", "red"), ("bh", "blue")],
            packages: [["id": "p", "nodeID": "rp", "ownerVanID": "red"]]
        )
        let crashRun = Boards.run(try MultiVanEngine(level: crash))
        guard case .failCrash = crashRun.engine.outcome else { return XCTFail("\(String(describing: crashRun.engine.outcome))") }
        XCTAssertEqual(crashRun.engine.packageStates["p"], .carried)
        let kinds = crashRun.events.compactMap { event -> String? in
            switch event {
            case .pickedUp: "pickup"
            case .crashed: "crash"
            case .delivered, .allDelivered: "celebration"
            default: nil
            }
        }
        XCTAssertEqual(kinds, ["pickup", "crash"])
    }

    // MARK: - Preview

    func testRunningPreviewStartsFromRealCargoAndTheCommittedRoad() throws {
        let level = try Boards.experiment("experiment_pickup_a")
        let engine = try Boards.engine(level, selections: ["fork": "tour"])
        engine.go()
        // On the tour road, before the pickup: the trace still collects at its end.
        engine.advance(by: 1.0)
        XCTAssertEqual(engine.vans[0].currentEdgeID, "tour")
        XCTAssertEqual(engine.previewRoutes[0].edgeIDs, ["tour", "return", "home"])
        XCTAssertEqual(engine.previewRoutes[0].collectedPackageIDs, ["red_parcel"])
        XCTAssertEqual(engine.packageStates["red_parcel"], .atPickup)
        // Past the pickup: nothing left to collect, and the route is complete.
        engine.advance(by: 2.5)
        XCTAssertEqual(engine.vans[0].currentEdgeID, "return")
        XCTAssertEqual(engine.packageStates["red_parcel"], .carried)
        XCTAssertEqual(engine.previewRoutes[0].collectedPackageIDs, [])
        XCTAssertEqual(engine.previewRoutes[0].missingPackageIDs, [])
        XCTAssertEqual(engine.previewRoutes[0].ending, .matchingHouse)
        XCTAssertFalse(MultiVanPickup.pickups(engine: engine)[0].isMissed)
    }

    func testPreviewRebuildsWhenALapCollectsEvenThoughTheVanEndsOnTheSameRoad() throws {
        // One long frame carries Red a whole lap: same road, new cargo.
        let level = try Boards.board(
            nodes: [("start", 0, 0), ("loop", 0, 1), ("pickup", 0, 3), ("back", 2, 3), ("house", 2, 6)],
            edges: [("in", "start", "loop"), ("lap", "loop", "pickup"), ("home", "loop", "house"),
                    ("r3", "pickup", "back"), ("r4", "back", "loop")],
            vans: [red("start")], houses: [("house", "red")],
            packages: [["id": "p", "nodeID": "pickup", "ownerVanID": "red"]],
            initial: ["loop": "lap"], live: ["loop"]
        )
        let engine = try MultiVanEngine(level: level)
        engine.go()
        engine.advance(by: 1.0)
        XCTAssertEqual(engine.vans[0].currentEdgeID, "lap")
        let before = engine.previewRoutes[0]
        XCTAssertEqual(before.collectedPackageIDs, ["p"])
        let lapLength = ["lap", "r3", "r4"].reduce(0.0) { $0 + (engine.runtimeGraph.edgesByID[$1]?.roadPath.totalLength ?? 0) }
        engine.advance(by: lapLength / engine.tuning.vanSpeed)
        XCTAssertEqual(engine.vans[0].currentEdgeID, "lap")
        XCTAssertEqual(engine.packageStates["p"], .carried)
        XCTAssertNotEqual(engine.previewRoutes[0], before)
        XCTAssertEqual(engine.previewRoutes[0].collectedPackageIDs, [])
    }

    func testTracingNeverMutatesAndOtherOwnersCannotConsumeAParcel() throws {
        let level = try Boards.experiment("experiment_pickup_b")
        let engine = try Boards.engine(level, selections: ["red_fork": "red_tour"])
        let states = engine.packageStates
        for _ in 0..<5 {
            XCTAssertEqual(engine.tapSwitch(nodeID: "blue_fork"), .accepted)
            XCTAssertEqual(engine.packageStates, states)
        }
        // Blue's trace over Red's pickup node collects nothing.
        let red = try XCTUnwrap(level.vans.first { $0.id == "red" })
        let asBlue = MultiVanRoutePreview.trace(
            from: red.startNodeID, color: .blue, graph: engine.runtimeGraph, houses: level.houses,
            packages: level.packages(ownedBy: "blue")
        )
        XCTAssertTrue(asBlue.collectedPackageIDs.isEmpty)
        XCTAssertEqual(asBlue.ending, .wrongHouse)
        // A loop that never reaches a house reports what it would still lack.
        let summary = MultiVanRoutePreview.summary(for: red, route: engine.previewRoutes[0], level: level)
        XCTAssertEqual(summary, "Red van collects its parcel, then reaches its house.")
        engine.resetSwitches()
        XCTAssertEqual(
            MultiVanRoutePreview.summary(for: red, route: engine.previewRoutes[0], level: level),
            "Red van reaches its house without its parcel. Route it past the pickup first."
        )
    }

    // MARK: - Presentation state

    func testBothBoardsReadTheSameCargoStateFromTheEngine() throws {
        let level = try Boards.experiment("experiment_pickup_a")
        let engine = try Boards.engine(level, selections: ["fork": "tour"])
        func frame() -> MultiVanDioramaFrame {
            MultiVanDioramaFrame(engine: engine, systemReduceMotion: false, reducesExtraAnimations: false)
        }
        XCTAssertEqual(frame().pickups, MultiVanPickup.pickups(engine: engine))
        XCTAssertEqual(frame().pickups.map(\.state), [.atPickup])
        XCTAssertEqual(frame().vans.map(\.carriesCargo), [false])
        engine.go()
        engine.advance(by: 3.5)
        XCTAssertEqual(frame().pickups.map(\.state), [.carried])
        XCTAssertEqual(frame().vans.map(\.carriesCargo), [true])
        XCTAssertEqual(MultiVanVanView.accessibilityValue(color: .red, status: .driving, isDelivered: false, cargo: engine.cargoStatus(forVanID: "red")),
                       "Driving. Carrying. Destination: red circle house")
        while engine.phase == .run { engine.advance(by: 0.1) }
        XCTAssertEqual(frame().pickups.map(\.state), [.delivered])
        XCTAssertEqual(frame().vans.map(\.carriesCargo), [false])
        XCTAssertEqual(frame().deliveredHouseNodeIDs, ["house"])

        // An empty arrival shows no delivered house on either board.
        engine.retry()
        engine.resetSwitches()
        Boards.run(engine)
        XCTAssertEqual(frame().deliveredHouseNodeIDs, [])
        XCTAssertEqual(frame().vans.map(\.status), [.missingCargo])
        XCTAssertEqual(MultiVanVanView.accessibilityValue(color: .red, status: .missingCargo, isDelivered: false, cargo: engine.cargoStatus(forVanID: "red")),
                       "Stopped at its house without its parcel. Destination: red circle house")
        // A van with nothing to collect reads exactly as it always has.
        XCTAssertEqual(MultiVanVanView.accessibilityValue(color: .blue, status: .waiting, isDelivered: false),
                       "Waiting. Destination: blue triangle house")
    }

    func testPickupMarkersStandBesideTheirNodeClearOfEveryRoad() throws {
        for level in try Boards.experiments() where !level.packages.isEmpty {
            let engine = try MultiVanEngine(level: level)
            for pickup in MultiVanPickup.pickups(engine: engine) {
                let node = try XCTUnwrap(engine.runtimeGraph.nodesByID[pickup.nodeID])
                XCTAssertEqual(abs(pickup.point.x - node.x), MultiVanPickup.markerOffset, accuracy: 1e-9)
                XCTAssertEqual(abs(pickup.point.y - node.y), MultiVanPickup.markerOffset, accuracy: 1e-9)
                for edge in engine.runtimeGraph.edgesByID.values {
                    for distance in stride(from: 0, through: edge.roadPath.totalLength, by: 0.05) {
                        let point = edge.roadPath.point(atDistance: distance)
                        XCTAssertGreaterThan(hypot(point.x - pickup.point.x, point.y - pickup.point.y), 0.3,
                                             "\(level.id): \(pickup.id) sits on road \(edge.id)")
                    }
                }
            }
        }
    }
}
