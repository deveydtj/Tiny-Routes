import Foundation
import XCTest
@testable import TinyRoutes

/// Shared helpers for tests that drive boards by switch settings rather than by
/// a recorded script: fixtures built in code, runs to an outcome, and every
/// static configuration of a small board.
enum MultiVanTestBoards {
    static let appBundle = Bundle(for: MultiVanEngine.self)

    static func experiments() throws -> [MultiVanLevel] {
        try MultiVanLevelRepository(bundle: appBundle).loadExperimentLevels()
    }

    static func experiment(_ id: String) throws -> MultiVanLevel {
        try XCTUnwrap(experiments().first { $0.id == id }, "\(id): missing experiment board")
    }

    /// The level's JSON as a dictionary, for building variants.
    static func json(_ id: String) throws -> [String: Any] {
        let url = try XCTUnwrap(appBundle.url(forResource: id, withExtension: "json", subdirectory: "PrototypeLevels"))
        return try XCTUnwrap(JSONSerialization.jsonObject(with: Data(contentsOf: url)) as? [String: Any])
    }

    static func level(_ json: [String: Any]) throws -> MultiVanLevel {
        try JSONDecoder().decode(MultiVanLevel.self, from: JSONSerialization.data(withJSONObject: json))
    }

    /// A board from a compact description. Nodes are `id: (x, y)`; edges are
    /// `(id, from, to)` and default to a vertical-first bend.
    static func board(
        id: String = "fixture",
        nodes: [(String, Double, Double)],
        edges: [(String, String, String)],
        vans: [[String: Any]],
        houses: [(String, String)],
        packages: [[String: Any]] = [],
        initial: [String: String] = [:],
        live: [String] = [],
        extra: [String: Any] = [:]
    ) throws -> MultiVanLevel {
        var json: [String: Any] = [
            "id": id, "name": "Fixture",
            "graph": [
                "nodes": nodes.map { node in
                    ["id": node.0, "x": node.1, "y": node.2,
                     "outgoingEdgeIDs": edges.filter { $0.1 == node.0 }.map(\.0)] as [String: Any]
                },
                "edges": edges.map { ["id": $0.0, "fromNodeID": $0.1, "toNodeID": $0.2, "roadShape": "verticalFirst"] },
            ],
            "vans": vans,
            "houses": houses.map { ["nodeID": $0.0, "color": $0.1] },
            "initialSwitchEdges": initial, "liveSwitchNodeIDs": live, "parChanges": 0,
        ]
        if !packages.isEmpty {
            json["packages"] = packages
            json["schemaVersion"] = 2
        }
        json.merge(extra) { _, new in new }
        return try level(json)
    }

    /// A fresh engine with `selections` made by planning taps, as a player would.
    static func engine(_ level: MultiVanLevel, selections: [String: String] = [:]) throws -> MultiVanEngine {
        let engine = try MultiVanEngine(level: level)
        try select(selections, in: engine)
        // Planning taps are not part of the run a test goes on to record.
        _ = engine.drainEvents()
        return engine
    }

    static func select(_ selections: [String: String], in engine: MultiVanEngine) throws {
        for (nodeID, edgeID) in selections.sorted(by: { $0.key < $1.key }) {
            var taps = 0
            while engine.runtimeGraph.nodesByID[nodeID]?.activeOutgoingEdgeID != edgeID {
                XCTAssertEqual(engine.tapSwitch(nodeID: nodeID), .accepted, "\(engine.level.id): \(nodeID)")
                taps += 1
                if taps > 4 { throw PrototypeSolutionError("\(engine.level.id): \(nodeID) has no exit \(edgeID)") }
            }
        }
    }

    /// What a run did, with every event in the order the engine produced it.
    struct Run {
        let engine: MultiVanEngine
        var events: [MultiVanEvent] = []
        /// The closest any two driving vans came, in grid units.
        var closestApproach = Double.infinity
    }

    /// Presses Go and steps to an outcome, or for `seconds` of simulation.
    @discardableResult
    static func run(_ engine: MultiVanEngine, seconds: Double = 60, frame: Double? = nil) -> Run {
        var run = Run(engine: engine)
        engine.go()
        run.events += engine.drainEvents()
        let step = frame ?? engine.tuning.stepDuration
        var elapsed = 0.0
        while engine.phase == .run, elapsed < seconds {
            engine.advance(by: step)
            elapsed += step
            run.events += engine.drainEvents()
            let driving = engine.vans.filter { $0.status == .driving }
            for first in driving.indices {
                for second in driving.indices where second > first {
                    let a = driving[first].position, b = driving[second].position
                    run.closestApproach = min(run.closestApproach, hypot(a.x - b.x, a.y - b.y))
                }
            }
        }
        return run
    }

    /// Every combination of exits over the level's switches, in a stable order.
    static func configurations(of level: MultiVanLevel) -> [[String: String]] {
        let switches = level.graph.nodes.filter { $0.outgoingEdgeIDs.count > 1 }.sorted { $0.id < $1.id }
        var configurations: [[String: String]] = [[:]]
        for node in switches {
            configurations = configurations.flatMap { partial in
                node.outgoingEdgeIDs.map { edgeID in partial.merging([node.id: edgeID]) { _, new in new } }
            }
        }
        return configurations
    }

    /// A short name for an outcome, for tables of expected results.
    static func name(_ outcome: MultiVanEngine.Outcome?) -> String {
        switch outcome {
        case .win: "win"
        case .failCrash: "crash"
        case .failWrongHouse: "wrongHouse"
        case .failStuck: "stuck"
        case .failMissingPackage: "missingPackage"
        case nil: "unfinished"
        }
    }
}
