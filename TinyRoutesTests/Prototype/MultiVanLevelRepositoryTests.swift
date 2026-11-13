import XCTest
@testable import TinyRoutes

final class MultiVanLevelRepositoryTests: XCTestCase {
    private func authoredFiles() throws -> [String: String] {
        let resources = URL(fileURLWithPath: #filePath).deletingLastPathComponent()
            .deletingLastPathComponent().deletingLastPathComponent()
            .appendingPathComponent("TinyRoutes/Resources/PrototypeLevels")
        return try Dictionary(uniqueKeysWithValues: ["level_001", "level_002", "level_003", "level_004", "level_005", "level_006", "level_007", "level_008", "level_009", "level_010", "level_011", "level_012", "level_013", "level_014"].map { id in
            ("PrototypeLevels/\(id).json", try String(contentsOf: resources.appendingPathComponent("\(id).json"), encoding: .utf8))
        })
    }

    func testAuthoredLevelsDecodeLoadInOrderAndHaveValidGraphs() throws {
        let files = try authoredFiles()
        for json in files.values {
            _ = try JSONDecoder().decode(MultiVanLevel.self, from: Data(json.utf8))
        }
        let levels = try MultiVanLevelRepository(bundle: makeBundle(files: files)).loadAllLevels()
        XCTAssertEqual(levels.map(\.id), ["level_001", "level_002", "level_003", "level_004", "level_005", "level_006", "level_007", "level_008", "level_009", "level_010", "level_011", "level_012", "level_013", "level_014"])
        XCTAssertEqual(levels.map(\.name), ["Go!", "Pick a Lane", "Two Turns", "Roundabout", "Two Colours", "Wait for It", "Convoy", "Merge", "Take a Lap", "Hold the Loop", "Split", "Three's Company", "Rush", "Big Delivery"])
        XCTAssertEqual(levels.map(\.parChanges), [0, 1, 2, 2, 2, 1, 1, 1, 1, 2, 2, 3, 5, 7])
        for level in levels {
            let nodeIDs = Set(level.graph.nodes.map(\.id))
            XCTAssertEqual(nodeIDs.count, level.graph.nodes.count)
            XCTAssertEqual(Set(level.graph.edges.map(\.id)).count, level.graph.edges.count)
            for node in level.graph.nodes {
                XCTAssertEqual(node.x, node.x.rounded())
                XCTAssertEqual(node.y, node.y.rounded())
                XCTAssertTrue((0...4).contains(node.x) && (0...6).contains(node.y))
                try node.validateOutgoingEdges(against: level.graph.edges)
            }
            for edge in level.graph.edges {
                XCTAssertTrue(nodeIDs.contains(edge.fromNodeID) && nodeIDs.contains(edge.toNodeID))
                XCTAssertEqual(edge.availability, .always)
                XCTAssertNil(edge.availabilityRule)
            }
            XCTAssertEqual(level.vans.count, level.id < "level_005" ? 1 : (level.id < "level_012" ? 2 : (level.id == "level_014" ? 4 : 3)))
            XCTAssertEqual(level.houses.count, level.vans.count)
            for van in level.vans {
                XCTAssertTrue(nodeIDs.contains(van.startNodeID))
                XCTAssertEqual(van.departDelay, level.id == "level_007" && van.color == .blue ? 0.83 : 0)
                XCTAssertTrue(level.houses.contains { $0.color == van.color })
            }
            for house in level.houses {
                let node = try XCTUnwrap(level.graph.nodes.first { $0.id == house.nodeID })
                XCTAssertTrue(node.outgoingEdgeIDs.isEmpty)
            }
            let switches = level.graph.nodes.filter { $0.outgoingEdgeIDs.count > 1 }
            XCTAssertEqual(Set(level.initialSwitchEdges.keys), Set(switches.map(\.id)))
            for node in switches {
                XCTAssertEqual(node.outgoingEdgeIDs.count, (level.id == "level_004" || (level.id == "level_013" && node.id == "yellow_switch") || (level.id == "level_014" && node.id == "route_switch")) ? 3 : 2)
                XCTAssertTrue(node.outgoingEdgeIDs.contains(try XCTUnwrap(level.initialSwitchEdges[node.id])))
            }
            let liveSwitches = ["level_006": ["switch"], "level_007": ["switch"], "level_009": ["loop_switch"], "level_010": ["loop_switch"], "level_011": ["switch"], "level_013": ["split_switch"], "level_014": ["split_switch"]]
            XCTAssertEqual(level.liveSwitchNodeIDs, liveSwitches[level.id] ?? [])
        }

        // The plan leaves exact coordinates open. Use one bent road for Go!,
        // and a red van with straight approach/barrier/house roads for Pick a Lane.
        let first = levels[0]
        let start = try XCTUnwrap(first.graph.nodes.first { $0.id == first.vans[0].startNodeID })
        let house = try XCTUnwrap(first.graph.nodes.first { $0.id == first.houses[0].nodeID })
        XCTAssertEqual([start.x, start.y, house.x, house.y], [0, 0, 4, 6])
        XCTAssertEqual(first.graph.edges.count, 1)
        let delivery = try XCTUnwrap(first.graph.edges.first)
        XCTAssertEqual(delivery.fromNodeID, start.id)
        XCTAssertEqual(delivery.toNodeID, house.id)
        XCTAssertEqual(delivery.roadShape, .verticalFirst)

        let second = levels[1]
        XCTAssertEqual(second.graph.nodes.count, 4)
        XCTAssertEqual(second.graph.edges.count, 3)
        let fork = try XCTUnwrap(second.graph.nodes.first { $0.outgoingEdgeIDs.count == 2 })
        let approach = try XCTUnwrap(second.graph.edges.first { $0.fromNodeID == second.vans[0].startNodeID })
        XCTAssertEqual(approach.toNodeID, fork.id)
        let initial = try XCTUnwrap(second.graph.edges.first { $0.id == second.initialSwitchEdges[fork.id] })
        let barrier = try XCTUnwrap(second.graph.nodes.first { $0.id == initial.toNodeID })
        XCTAssertTrue(barrier.outgoingEdgeIDs.isEmpty)
        XCTAssertFalse(second.houses.contains { $0.nodeID == barrier.id })
        // One tap advances from the barrier exit to the terminal matching house.
        XCTAssertEqual(fork.outgoingEdgeIDs.first, initial.id)
        let next = try XCTUnwrap(second.graph.edges.first { $0.id == fork.outgoingEdgeIDs[1] })
        XCTAssertEqual(next.toNodeID, second.houses[0].nodeID)
    }

    private func levelJSON(id: String) -> String {
        """
        {
          "id": "\(id)", "name": "Repository fixture",
          "graph": { "nodes": [], "edges": [] },
          "vans": [{ "id": "van", "color": "blue", "startNodeID": "start" }],
          "houses": [{ "nodeID": "house", "color": "blue" }],
          "initialSwitchEdges": {}, "parChanges": 2
        }
        """
    }

    /// Each test gets a unique, disposable bundle; no level JSON is shipped by these tests.
    private func makeBundle(files: [String: String] = [:]) throws -> Bundle {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent(UUID().uuidString).appendingPathExtension("bundle")
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        addTeardownBlock { try FileManager.default.removeItem(at: root) }
        for (path, json) in files {
            let url = root.appendingPathComponent(path)
            try FileManager.default.createDirectory(at: url.deletingLastPathComponent(), withIntermediateDirectories: true)
            try Data(json.utf8).write(to: url)
        }
        return try XCTUnwrap(Bundle(path: root.path))
    }

    func testLoadsPrototypeJSON() throws {
        let bundle = try makeBundle(files: ["PrototypeLevels/level_fixture.json": levelJSON(id: "level_test")])
        let level = try XCTUnwrap(MultiVanLevelRepository(bundle: bundle).loadAllLevels().first)
        XCTAssertEqual(level.id, "level_test")
        XCTAssertEqual(level.vans.first?.color, .blue)
        XCTAssertEqual(level.parChanges, 2)
    }

    func testSortsByDecodedIDRatherThanFilename() throws {
        let bundle = try makeBundle(files: [
            "PrototypeLevels/level_a.json": levelJSON(id: "level_002"),
            "PrototypeLevels/level_z.json": levelJSON(id: "level_001")
        ])
        XCTAssertEqual(try MultiVanLevelRepository(bundle: bundle).loadAllLevels().map(\.id), ["level_001", "level_002"])
    }

    func testIgnoresOtherNamesExtensionsAndDirectories() throws {
        let bundle = try makeBundle(files: [
            "PrototypeLevels/level_valid.json": levelJSON(id: "level_valid"),
            "PrototypeLevels/other.json": "malformed",
            "PrototypeLevels/level_other.txt": "malformed",
            "level_root.json": "malformed",
            "Levels/level_wrong_directory.json": "malformed"
        ])
        XCTAssertEqual(try MultiVanLevelRepository(bundle: bundle).loadAllLevels().map(\.id), ["level_valid"])
    }

    func testMissingPrototypeDirectoryReturnsEmpty() throws {
        XCTAssertTrue(try MultiVanLevelRepository(bundle: makeBundle()).loadAllLevels().isEmpty)
    }

    func testDirectoryWithoutPrototypeFilesReturnsEmpty() throws {
        let bundle = try makeBundle(files: ["PrototypeLevels/other.json": "malformed"])
        XCTAssertTrue(try MultiVanLevelRepository(bundle: bundle).loadAllLevels().isEmpty)
    }

    func testMalformedPrototypeReportsFilenameAndDecodingError() throws {
        let bundle = try makeBundle(files: ["PrototypeLevels/level_broken.json": "{"])
        XCTAssertThrowsError(try MultiVanLevelRepository(bundle: bundle).loadAllLevels()) { error in
            guard case let LevelRepositoryError.decodingFailed(id, underlying) = error else {
                return XCTFail("Expected decodingFailed, got \(error)")
            }
            XCTAssertEqual(id, "level_broken")
            XCTAssertTrue(underlying is DecodingError)
        }
    }

    func testAppBundleContainsAuthoredPrototypeLevelsInOrder() throws {
        guard !(try MultiVanLevelRepository(bundle: .main).loadAllLevels()).isEmpty else {
            throw XCTSkip("Requires the iOS app bundle; isolated Foundation tests do not verify app packaging.")
        }
        XCTAssertEqual(try MultiVanLevelRepository(bundle: .main).loadAllLevels().map(\.id), ["level_001", "level_002", "level_003", "level_004", "level_005", "level_006", "level_007", "level_008", "level_009", "level_010", "level_011", "level_012", "level_013", "level_014", "level_015", "level_016", "level_017", "level_018", "level_019"])
        for number in 1...19 {
            XCTAssertNil(Bundle.main.url(forResource: String(format: "level_%03d", number), withExtension: "json"))
        }
    }
}
