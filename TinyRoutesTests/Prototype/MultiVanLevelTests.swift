import XCTest
@testable import TinyRoutes

final class MultiVanLevelTests: XCTestCase {
    // Keep diagnostics as data so negative fixtures exercise the same checks as authored levels.
    private func validationIssues(in level: MultiVanLevel) -> [String] {
        var issues: [String] = []
        func reject(_ message: String) { issues.append("\(level.id): \(message)") }
        let graph = level.graph
        let tuning = MultiVanTuning.default
        let nodes = Dictionary(grouping: graph.nodes, by: \.id)
        let edges = Dictionary(grouping: graph.edges, by: \.id)
        for id in nodes.keys.sorted() where nodes[id]!.count > 1 { reject("duplicate node \(id)") }
        for id in edges.keys.sorted() where edges[id]!.count > 1 { reject("duplicate edge \(id)") }

        for node in graph.nodes {
            do {
                try node.validateOutgoingEdges(against: graph.edges)
            } catch {
                reject("node \(node.id): \(error.localizedDescription)")
            }
            let exits = graph.edges.filter { $0.fromNodeID == node.id }.count
            if exits > 4 { reject("node \(node.id) has \(exits) exits") }
            if !node.x.isFinite || !node.y.isFinite || node.x != node.x.rounded() || node.y != node.y.rounded() {
                reject("node \(node.id) coordinates must be whole numbers")
            }
            if !(0...Double(tuning.gridColumns - 1)).contains(node.x) || !(0...Double(tuning.gridRows - 1)).contains(node.y) {
                reject("node \(node.id) is outside grid bounds")
            }
        }
        for edge in graph.edges {
            for id in [edge.fromNodeID, edge.toNodeID] where nodes[id] == nil {
                reject("edge \(edge.id) references unknown node \(id)")
            }
            guard let start = nodes[edge.fromNodeID]?.first, let end = nodes[edge.toNodeID]?.first,
                  start.x.isFinite, start.y.isFinite, end.x.isFinite, end.y.isFinite else { continue }
            let path = RoadPath.make(from: RoadPoint(x: start.x, y: start.y),
                                     to: RoadPoint(x: end.x, y: end.y), shape: edge.roadShape)
            if !path.totalLength.isFinite || path.totalLength < 1 {
                reject("road \(edge.id) is shorter than one grid unit")
            }
        }
        // Switch identity comes from real graph connectivity, not potentially stale node references.
        let switches = Set(graph.nodes.filter { node in
            (2...4).contains(graph.edges.filter { $0.fromNodeID == node.id }.count)
        }.map(\.id))
        for id in level.initialSwitchEdges.keys.sorted() {
            let selection = level.initialSwitchEdges[id]!
            if !switches.contains(id) { reject("initial switch \(id) is not a real switch") }
            if let candidates = edges[selection] {
                if !candidates.contains(where: { $0.fromNodeID == id }) {
                    reject("initial switch \(id) selects edge \(selection) belonging to another node")
                }
            } else {
                reject("initial switch \(id) references unknown edge \(selection)")
            }
        }
        for id in level.liveSwitchNodeIDs where !switches.contains(id) {
            reject("live switch \(id) is not a real switch")
        }
        for tip in level.tutorial {
            if level.tutorial.filter({ $0.trigger == tip.trigger }).count > 1 {
                reject("more than one \(tip.trigger.rawValue) tip")
            }
            if tip.title.trimmingCharacters(in: .whitespaces).isEmpty || tip.body.trimmingCharacters(in: .whitespaces).isEmpty {
                reject("\(tip.trigger.rawValue) tip needs a title and body")
            }
            for id in tip.focusNodeIDs where nodes[id] == nil {
                reject("\(tip.trigger.rawValue) tip focuses unknown node \(id)")
            }
        }
        for van in level.vans {
            if nodes[van.startNodeID] == nil { reject("van \(van.id) references unknown start node \(van.startNodeID)") }
            let count = level.houses.filter { $0.color == van.color }.count
            if count == 0 { reject("\(van.color.rawValue) van \(van.id) has no matching house") }
            if count > 1 { reject("\(van.color.rawValue) van \(van.id) has \(count) matching houses") }
        }
        var houseNodes = Set<String>()
        var houseColors = Set<String>()
        for house in level.houses {
            if !houseNodes.insert(house.nodeID).inserted {
                reject("house node \(house.nodeID) has duplicate or conflicting destinations")
            }
            if !houseColors.insert(house.color.rawValue).inserted {
                reject("\(house.color.rawValue) house \(house.nodeID) duplicates a destination color")
            }
            guard let node = nodes[house.nodeID]?.first else {
                reject("\(house.color.rawValue) house references unknown node \(house.nodeID)")
                continue
            }
            if !node.outgoingEdgeIDs.isEmpty || graph.edges.contains(where: { $0.fromNodeID == node.id }) {
                reject("house node \(node.id) has outgoing edges")
            }
        }
        return issues
    }

    private func makeBundle(files: [String: Data]) throws -> Bundle {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent(UUID().uuidString).appendingPathExtension("bundle")
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        addTeardownBlock { try FileManager.default.removeItem(at: root) }
        for path in files.keys.sorted() {
            let url = root.appendingPathComponent(path)
            try FileManager.default.createDirectory(at: url.deletingLastPathComponent(), withIntermediateDirectories: true)
            try files[path]!.write(to: url)
        }
        return try XCTUnwrap(Bundle(path: root.path), "Could not open validation fixture bundle \(root.path)")
    }

    func testEveryAuthoredPrototypeLevelDecodesAndIsValid() throws {
        let directory = URL(fileURLWithPath: #filePath).deletingLastPathComponent()
            .deletingLastPathComponent().deletingLastPathComponent()
            .appendingPathComponent("TinyRoutes/Resources/PrototypeLevels")
        let urls = try FileManager.default.contentsOfDirectory(at: directory, includingPropertiesForKeys: nil)
            .filter { $0.pathExtension == "json" && $0.lastPathComponent.hasPrefix("level_") }
            .sorted { $0.lastPathComponent < $1.lastPathComponent }
        XCTAssertEqual(urls.map(\.lastPathComponent), (1...19).map { String(format: "level_%03d.json", $0) })
        XCTAssertTrue(urls.contains { $0.lastPathComponent == "level_001.json" }, "level_001: Go! is missing")
        XCTAssertTrue(urls.contains { $0.lastPathComponent == "level_002.json" }, "level_002: Pick a Lane is missing")
        XCTAssertTrue(urls.contains { $0.lastPathComponent == "level_003.json" }, "level_003: Two Turns is missing")
        XCTAssertTrue(urls.contains { $0.lastPathComponent == "level_004.json" }, "level_004: Roundabout is missing")
        XCTAssertTrue(urls.contains { $0.lastPathComponent == "level_005.json" }, "level_005: Two Colours is missing")
        XCTAssertTrue(urls.contains { $0.lastPathComponent == "level_006.json" }, "level_006: Wait for It is missing")
        XCTAssertTrue(urls.contains { $0.lastPathComponent == "level_007.json" }, "level_007: Convoy is missing")
        // Load separately: a malformed file must not hide failures in subsequent levels.
        for url in urls {
            do {
                let bundle = try makeBundle(files: ["PrototypeLevels/\(url.lastPathComponent)": Data(contentsOf: url)])
                let levels = try MultiVanLevelRepository(bundle: bundle).loadAllLevels()
                XCTAssertEqual(levels.count, 1, "\(url.lastPathComponent): repository did not load exactly one level")
                for level in levels {
                    XCTAssertEqual(level.id, url.deletingPathExtension().lastPathComponent,
                                   "\(url.lastPathComponent): decoded level ID is \(level.id)")
                    let issues = validationIssues(in: level)
                    XCTAssertTrue(issues.isEmpty, issues.joined(separator: "\n"))
                }
            } catch {
                XCTFail("\(url.lastPathComponent): \(error.localizedDescription)")
            }
        }
    }

    private func fixtureGraph() -> RouteGraph {
        RouteGraph(nodes: [
            RouteNode(id: "start", x: 0, y: 0, outgoingEdgeIDs: ["approach"]),
            RouteNode(id: "s1", x: 0, y: 2, outgoingEdgeIDs: ["delivery", "barrier"]),
            RouteNode(id: "house", x: 4, y: 2, outgoingEdgeIDs: []),
            RouteNode(id: "end", x: 0, y: 6, outgoingEdgeIDs: [])
        ], edges: [
            RouteEdge(id: "approach", fromNodeID: "start", toNodeID: "s1"),
            RouteEdge(id: "delivery", fromNodeID: "s1", toNodeID: "house"),
            RouteEdge(id: "barrier", fromNodeID: "s1", toNodeID: "end")
        ])
    }

    private func fixture(graph: RouteGraph, overrides: [String: Any] = [:]) throws -> MultiVanLevel {
        var json: [String: Any] = [
            "id": "level_fixture", "name": "Validation fixture",
            "graph": try JSONSerialization.jsonObject(with: JSONEncoder().encode(graph)),
            "vans": [["id": "red", "color": "red", "startNodeID": "start"]],
            "houses": [["nodeID": "house", "color": "red"]],
            "initialSwitchEdges": ["s1": "delivery"], "liveSwitchNodeIDs": ["s1"], "parChanges": 0
        ]
        json.merge(overrides) { _, new in new }
        return try JSONDecoder().decode(MultiVanLevel.self, from: JSONSerialization.data(withJSONObject: json))
    }

    func testValidFixturesAcceptGridBoundariesAndTwoThroughFourExits() throws {
        for exits in 2...4 {
            var graph = fixtureGraph()
            for index in 2..<exits {
                let id = "extra_\(index)"
                graph.nodes[1].outgoingEdgeIDs.append(id)
                graph.edges.append(RouteEdge(id: id, fromNodeID: "s1", toNodeID: "end"))
            }
            let issues = validationIssues(in: try fixture(graph: graph))
            XCTAssertTrue(issues.isEmpty, "\(exits)-exit fixture: \(issues.joined(separator: "\n"))")
        }
    }

    func testInvalidGraphFixturesIdentifyLevelAndObject() throws {
        let cases: [(String, (inout RouteGraph) -> Void)] = [
            ("edge bad references unknown node missing", { $0.edges.append(RouteEdge(id: "bad", fromNodeID: "missing", toNodeID: "end")) }),
            ("edge delivery references unknown node missing", { $0.edges[1] = RouteEdge(id: "delivery", fromNodeID: "s1", toNodeID: "missing") }),
            ("node s1: RouteNode s1 has inconsistent outgoingEdgeIDs", { $0.nodes[1].outgoingEdgeIDs = ["delivery"] }),
            ("node s1: RouteNode s1 has inconsistent outgoingEdgeIDs", { $0.nodes[1].outgoingEdgeIDs = ["delivery", "approach"] }),
            ("node s1: RouteNode s1 has inconsistent outgoingEdgeIDs", { $0.nodes[1].outgoingEdgeIDs.append("unknown") }),
            ("node s1: RouteNode s1 has duplicate outgoingEdgeIDs", { $0.nodes[1].outgoingEdgeIDs.append("delivery") }),
            ("node s1 has 5 exits", { graph in
                for index in 0..<3 {
                    let id = "extra_\(index)"
                    graph.nodes[1].outgoingEdgeIDs.append(id)
                    graph.edges.append(RouteEdge(id: id, fromNodeID: "s1", toNodeID: "end"))
                }
            }),
            ("node s1 is outside grid bounds", { $0.nodes[1].x = 5 }),
            ("node s1 is outside grid bounds", { $0.nodes[1].x = -1 }),
            ("node s1 is outside grid bounds", { $0.nodes[1].y = 7 }),
            ("node s1 is outside grid bounds", { $0.nodes[1].y = -1 }),
            ("node s1 coordinates must be whole numbers", { $0.nodes[1].x = 0.5 }),
            ("node s1 coordinates must be whole numbers", { $0.nodes[1].y = 2.5 }),
            ("road approach is shorter than one grid unit", { $0.nodes[1].y = 0.5 }),
            ("road approach is shorter than one grid unit", { $0.nodes[1].y = 0 }),
            ("house node house has outgoing edges", { graph in
                graph.nodes[2].outgoingEdgeIDs = ["exit"]
                graph.edges.append(RouteEdge(id: "exit", fromNodeID: "house", toNodeID: "end"))
            }),
            ("duplicate node s1", { $0.nodes.append($0.nodes[1]) }),
            ("duplicate edge delivery", { $0.edges.append($0.edges[1]) })
        ]
        for (expected, mutate) in cases {
            var graph = fixtureGraph()
            mutate(&graph)
            let issues = validationIssues(in: try fixture(graph: graph))
            XCTAssertTrue(issues.contains { $0.hasPrefix("level_fixture: \(expected)") },
                          "Expected level_fixture: \(expected); got \(issues)")
        }
    }

    func testInvalidDestinationAndSwitchFixturesIdentifyLevelAndObject() throws {
        let cases: [(String, [String: Any])] = [
            ("red van red has no matching house", ["houses": []]),
            ("red van red has 2 matching houses", ["houses": [["nodeID": "house", "color": "red"], ["nodeID": "end", "color": "red"]]]),
            ("house node house has duplicate or conflicting destinations", ["houses": [["nodeID": "house", "color": "red"], ["nodeID": "house", "color": "blue"]]]),
            ("red house references unknown node missing", ["houses": [["nodeID": "missing", "color": "red"]]]),
            ("van red references unknown start node missing", ["vans": [["id": "red", "color": "red", "startNodeID": "missing"]]]),
            ("initial switch s1 references unknown edge e9", ["initialSwitchEdges": ["s1": "e9"]]),
            ("initial switch s1 selects edge approach belonging to another node", ["initialSwitchEdges": ["s1": "approach"]]),
            ("initial switch missing is not a real switch", ["initialSwitchEdges": ["missing": "delivery"]]),
            ("initial switch start is not a real switch", ["initialSwitchEdges": ["start": "approach"]]),
            ("live switch missing is not a real switch", ["liveSwitchNodeIDs": ["missing"]]),
            ("live switch start is not a real switch", ["liveSwitchNodeIDs": ["start"]])
        ]
        for (expected, overrides) in cases {
            let issues = validationIssues(in: try fixture(graph: fixtureGraph(), overrides: overrides))
            XCTAssertTrue(issues.contains("level_fixture: \(expected)"),
                          "Expected level_fixture: \(expected); got \(issues)")
        }
    }

    func testInvalidJSONReportsLevelFilenameAndDecodingCause() throws {
        for json in ["{", "{}"] {
            let bundle = try makeBundle(files: ["PrototypeLevels/level_broken.json": Data(json.utf8)])
            XCTAssertThrowsError(try MultiVanLevelRepository(bundle: bundle).loadAllLevels()) { error in
                guard case let LevelRepositoryError.decodingFailed(id, underlying) = error else {
                    return XCTFail("level_broken: expected decodingFailed, got \(error)")
                }
                XCTAssertEqual(id, "level_broken", "Malformed prototype diagnostic lost its filename")
                XCTAssertTrue(error.localizedDescription.contains("level_broken"), "Diagnostic lost level_broken: \(error)")
                XCTAssertTrue(underlying is DecodingError, "level_broken: missing JSON decoding cause: \(error)")
            }
        }
    }
}
