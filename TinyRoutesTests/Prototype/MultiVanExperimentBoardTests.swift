import SceneKit
import XCTest
@testable import TinyRoutes

/// The two-parcel boards, and the experiment boards' pieces on the 3D table.
@MainActor
final class MultiVanExperimentBoardTests: XCTestCase {
    private typealias Boards = MultiVanTestBoards

    // MARK: - Two parcels

    func testAPairOfParcelsNeedsBothAndNamesWhatIsLeft() throws {
        let level = try Boards.experiment("experiment_pair_a")
        XCTAssertEqual(level.packages(ownedBy: "red").map(\.id), ["west", "east"])
        var outcomes: [String: String] = [:]
        for configuration in Boards.configurations(of: level) {
            let engine = try Boards.engine(level, selections: configuration)
            let key = "\(configuration["first_fork"]!) \(configuration["second_fork"]!)"
            // The preview already says what each plan would leave behind.
            let missing = engine.previewRoutes[0].missingPackageIDs
            Boards.run(engine)
            outcomes[key] = Boards.name(engine.outcome) + (missing.isEmpty ? "" : " " + missing.joined(separator: ","))
            if case let .failMissingPackage(_, packageID, _) = engine.outcome {
                XCTAssertEqual(packageID, missing.first, "the failure names the first parcel still out")
            }
        }
        XCTAssertEqual(outcomes, [
            "first_direct second_direct": "missingPackage west,east",
            "first_direct second_tour": "missingPackage west",
            "first_tour second_direct": "missingPackage east",
            "first_tour second_tour": "win",
        ])

        // One parcel aboard is progress, shown as such, and not yet "carrying".
        let engine = try Boards.engine(level, selections: ["first_fork": "first_tour", "second_fork": "second_tour"])
        XCTAssertEqual(engine.cargoStatus(forVanID: "red").label, "2 pickups needed")
        engine.go()
        engine.advance(by: 3.5)
        XCTAssertEqual(engine.packageStates, ["west": .carried, "east": .atPickup])
        XCTAssertEqual(engine.cargoStatus(forVanID: "red"), .pickupNeeded(remaining: [level.packages[1]]))
        XCTAssertEqual(engine.cargoStatus(forVanID: "red").label, "Pickup needed")
        XCTAssertEqual(MultiVanPickup.pickups(engine: engine).map(\.isMissed), [false, false])
        while engine.phase == .run { engine.advance(by: 0.1) }
        XCTAssertEqual(engine.outcome, .win)
        XCTAssertEqual(engine.packageStates, ["west": .delivered, "east": .delivered])
        // Both parcels arrive as one delivery.
        XCTAssertEqual(engine.drainEvents().filter { if case .delivered = $0 { true } else { false } }.count, 1)
        // A single stop leaves the other parcel on the board, and the summary says so.
        let partial = try Boards.engine(level, selections: ["first_fork": "first_tour"])
        XCTAssertEqual(MultiVanRoutePreview.summary(for: level.vans[0], route: partial.previewRoutes[0], level: level),
                       "Red van reaches its house without its parcel. Route it past the pickup first.")
        XCTAssertEqual(MultiVanPickup.pickups(engine: partial).map(\.isMissed), [false, true])
    }

    func testEitherWayRoundHasTwoRealOrdersAndASafeEndlessLoop() throws {
        let level = try Boards.experiment("experiment_pair_b")
        var wins: [[String]] = []
        var table: [String: String] = [:]
        for configuration in Boards.configurations(of: level) {
            let engine = try Boards.engine(level, selections: configuration)
            let run = Boards.run(engine, seconds: 40)
            let key = ["fork", "west_switch", "east_switch"].map { configuration[$0]! }.joined(separator: " ")
            table[key] = Boards.name(engine.outcome)
            if engine.outcome == .win {
                wins.append(run.events.compactMap { if case let .pickedUp(_, packageID, _) = $0 { packageID } else { nil } })
                XCTAssertLessThanOrEqual(engine.changeCount, level.parChanges, "either order earns full stars")
                XCTAssertEqual(MultiVanStars.rating(changes: engine.changeCount, par: level.parChanges), 3)
            }
        }
        XCTAssertEqual(table, [
            "to_west west_home east_home": "missingPackage",
            "to_west west_home east_to_west": "missingPackage",
            "to_west west_to_east east_home": "win",
            "to_west west_to_east east_to_west": "unfinished",
            "to_east west_home east_home": "missingPackage",
            "to_east west_home east_to_west": "win",
            "to_east west_to_east east_home": "missingPackage",
            "to_east west_to_east east_to_west": "unfinished",
        ])
        // Two complete plans, collecting in opposite orders.
        XCTAssertEqual(Set(wins), [["west", "east"], ["east", "west"]])

        // The endless plan is safe: both parcels aboard, the preview says it is
        // unfinished, and Stop returns everything.
        let loop = try Boards.engine(level, selections: ["fork": "to_west", "west_switch": "west_to_east", "east_switch": "east_to_west"])
        XCTAssertEqual(loop.previewRoutes[0].ending, .loopLimit)
        XCTAssertEqual(MultiVanRoutePreview.summary(for: level.vans[0], route: loop.previewRoutes[0], level: level),
                       "Red van collects 2 parcels, then keeps circling: this route is not finished.")
        loop.go()
        loop.advance(by: 30)
        XCTAssertEqual(loop.phase, .run)
        XCTAssertEqual(loop.cargoStatus(forVanID: "red"), .carrying)
        loop.stop()
        XCTAssertEqual(loop.packageStates, ["west": .atPickup, "east": .atPickup])
    }

    func testOneCollectorOneNeighborTheOrderDecidesWhichRoadBlueCanUse() throws {
        let level = try Boards.experiment("experiment_pair_c")
        XCTAssertEqual(level.packages(ownedBy: "red").map(\.id), ["west", "east"])
        XCTAssertTrue(level.packages(ownedBy: "blue").isEmpty)
        let switches = ["fork", "west_switch", "east_switch", "blue_fork"]
        var table: [String: String] = [:]
        var wins: [String: [String]] = [:]
        for configuration in Boards.configurations(of: level) {
            let engine = try Boards.engine(level, selections: configuration)
            let run = Boards.run(engine, seconds: 40)
            let key = switches.map { configuration[$0]! }.joined(separator: " ")
            table[key] = Boards.name(engine.outcome)
            switch engine.outcome {
            case .win:
                wins[configuration["blue_fork"]!] = run.events.compactMap {
                    if case let .pickedUp(_, packageID, _) = $0 { packageID } else { nil }
                }
                // Not a near miss, and either order earns full stars.
                XCTAssertGreaterThan(run.closestApproach, 1.0, key)
                XCTAssertEqual(engine.changeCount, level.parChanges, key)
                XCTAssertEqual(MultiVanStars.rating(changes: engine.changeCount, par: level.parChanges), 3)
                XCTAssertEqual(engine.cargoStatus(forVanID: "blue"), .ready)
            case let .failCrash(vanIDs, point):
                // Every crash is the one marked crossing, with both parcels aboard.
                XCTAssertEqual(vanIDs, ["red", "blue"], key)
                XCTAssertEqual(point.x, 3, accuracy: 0.3, key)
                XCTAssertEqual(point.y, 5, accuracy: 0.3, key)
                XCTAssertEqual(engine.packageStates, ["west": .carried, "east": .carried], key)
                let planned = try Boards.engine(level, selections: configuration)
                XCTAssertTrue(planned.previewRoutes.allSatisfy(\.isComplete), "\(key): both routes read as complete")
            case .failMissingPackage:
                // A one-parcel trip says so at the house, with no crash on the way.
                XCTAssertEqual(engine.vans[1].status, .driving, "\(key): Blue is still on its way")
            default:
                break
            }
        }
        XCTAssertEqual(table, [
            "to_west west_home east_home blue_short": "missingPackage",
            "to_west west_home east_home blue_long": "missingPackage",
            "to_west west_home east_to_west blue_short": "missingPackage",
            "to_west west_home east_to_west blue_long": "missingPackage",
            "to_west west_to_east east_home blue_short": "win",
            "to_west west_to_east east_home blue_long": "crash",
            "to_west west_to_east east_to_west blue_short": "unfinished",
            "to_west west_to_east east_to_west blue_long": "unfinished",
            "to_east west_home east_home blue_short": "missingPackage",
            "to_east west_home east_home blue_long": "missingPackage",
            "to_east west_home east_to_west blue_short": "crash",
            "to_east west_home east_to_west blue_long": "win",
            "to_east west_to_east east_home blue_short": "missingPackage",
            "to_east west_to_east east_home blue_long": "missingPackage",
            "to_east west_to_east east_to_west blue_short": "unfinished",
            "to_east west_to_east east_to_west blue_long": "unfinished",
        ])
        // Each order has its own road for Blue: the long way round lets Blue go
        // first, the short way round sends Blue the long way.
        XCTAssertEqual(wins, ["blue_short": ["west", "east"], "blue_long": ["east", "west"]])
    }

    // MARK: - The 3D table

    private func part(_ node: SCNNode?, _ name: String) -> SCNNode? {
        node?.childNode(withName: name, recursively: true)
    }

    func testDioramaShowsEachParcelWhereTheEngineHasIt() throws {
        let level = try Boards.experiment("experiment_pickup_a")
        let engine = try Boards.engine(level, selections: ["fork": "tour"])
        let scene = MultiVanDioramaScene()
        scene.load(level, graph: engine.runtimeGraph)
        let sync = { scene.sync(MultiVanDioramaFrame(engine: engine, systemReduceMotion: true, reducesExtraAnimations: false)) }
        typealias Part = MultiVanDioramaPieces.CargoPart
        let pad = try XCTUnwrap(scene.pickups["red_parcel"])
        let van = try XCTUnwrap(scene.vans["red"])
        XCTAssertEqual(scene.pickups.count, 1)
        // The pad stands where the flat board puts its marker.
        let marker = MultiVanPickup.pickups(engine: engine)[0].point
        XCTAssertEqual(pad.simdPosition, SIMD3<Float>(MultiVanDioramaGeometry.world(gridX: marker.x, gridY: marker.y)))

        sync()
        XCTAssertEqual(part(pad, Part.waitingParcel)?.isHidden, false)
        XCTAssertEqual(part(van, Part.roofParcel)?.isHidden, true)
        engine.go()
        engine.advance(by: 3.5)
        sync()
        XCTAssertEqual(part(pad, Part.waitingParcel)?.isHidden, true, "collected: only the pad is left")
        XCTAssertEqual(part(van, Part.roofParcel)?.isHidden, false, "and the parcel rides on the roof")
        while engine.phase == .run { engine.advance(by: 0.1) }
        sync()
        XCTAssertEqual(part(van, Part.roofParcel)?.isHidden, true, "delivered")
        XCTAssertEqual(scene.deliveredBadges["house"]?.isHidden, false)
        // Retry puts the parcel back on its pad.
        engine.retry()
        sync()
        XCTAssertEqual(part(pad, Part.waitingParcel)?.isHidden, false)

        // An empty arrival shows no delivered badge, and the van keeps its place upright.
        engine.resetSwitches()
        Boards.run(engine)
        sync()
        XCTAssertEqual(scene.deliveredBadges["house"]?.isHidden, true)
        // A van with nothing to collect carries no hidden parcel at all.
        let plain = MultiVanDioramaScene()
        let control = try Boards.experiment("experiment_pickup_c")
        plain.load(control, graph: try MultiVanEngine(level: control).runtimeGraph)
        XCTAssertNil(part(plain.vans["red"], Part.roofParcel))
        XCTAssertTrue(plain.pickups.isEmpty)
    }

    func testDioramaLampsFollowTheSameSignalStateAsTheFlatBoard() throws {
        typealias Part = MultiVanDioramaPieces.CargoPart
        for id in ["experiment_signal_a", "experiment_drawbridge_a"] {
            let level = try Boards.experiment(id)
            let engine = try Boards.engine(level, selections: ["blue_fork": "blue_short"])
            let scene = MultiVanDioramaScene()
            scene.load(level, graph: engine.runtimeGraph)
            XCTAssertEqual(scene.signalPosts.count, level.signals.flatMap(\.approaches).count, id)
            var seen = Set<Bool>()
            let check = {
                scene.sync(MultiVanDioramaFrame(engine: engine, systemReduceMotion: true, reducesExtraAnimations: false))
                for approach in MultiVanSignalApproach.approaches(engine: engine) {
                    let post = scene.signalPosts[approach.id]
                    XCTAssertEqual(self.part(post, Part.goLamp)?.isHidden, !approach.isOpen, "\(id) \(approach.id)")
                    XCTAssertEqual(self.part(post, Part.stopLamp)?.isHidden, approach.isOpen, "\(id) \(approach.id)")
                    seen.insert(approach.isOpen)
                }
            }
            check()
            engine.go()
            while engine.phase == .run {
                engine.advance(by: 0.1)
                check()
            }
            XCTAssertEqual(engine.outcome, .win, id)
            XCTAssertEqual(seen, [true, false], "\(id): every lamp was seen both ways")
            // Only a drawbridge has an arm across its road.
            let hasArm = scene.signalPosts.values.contains { self.part($0, Part.bridgeDeck) != nil }
            XCTAssertEqual(hasArm, level.signals[0].kind == .drawbridge, id)
        }
    }

    func testSceneryKeepsClearOfParcelsLampsAndWaterAndCampaignLawnsAreUnchanged() throws {
        for level in try Boards.experiments() {
            let graph = try MultiVanEngine(level: level).runtimeGraph
            let features = MultiVanDioramaLawn.Features(level: level, graph: graph)
            let scenery = MultiVanDioramaScenery(level: level, graph: graph)
            XCTAssertEqual(features.canals.count, level.signals.filter { $0.kind == .drawbridge }.count, level.id)
            for item in scenery.items where item.height > 0 {
                for reserved in features.reserved {
                    XCTAssertGreaterThan(hypot(item.point.x - reserved.point.x, item.point.y - reserved.point.y), reserved.radius,
                                         "\(level.id): scenery stands on a parcel, a lamp or the water")
                }
            }
            // The lawn paints without trouble for every biome and feature.
            let lawn = MultiVanDioramaLawn.image(for: level, graph: graph, scenery: scenery)
            XCTAssertEqual(lawn.size, MultiVanDioramaLawn.imageSize, level.id)
        }
        // The original fourteen; the content pack's lawns make room for its parcels.
        for level in try MultiVanLevelRepository(bundle: Boards.appBundle).loadAllLevels().prefix(14) {
            let features = MultiVanDioramaLawn.Features(level: level, graph: try MultiVanEngine(level: level).runtimeGraph)
            XCTAssertTrue(features.reserved.isEmpty && features.canals.isEmpty, level.id)
        }
        // Every biome has a name; only the meadow keeps the plain lawn.
        XCTAssertEqual(MultiVanBiome.allCases.filter { $0.groundWash == nil }, [.meadow])
        XCTAssertEqual(Set(try Boards.experiments().map(\.biome)), [.depot, .market, .harbor, .snow])
    }
}
