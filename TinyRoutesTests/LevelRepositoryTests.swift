import XCTest
@testable import TinyRoutes

final class LevelRepositoryTests: XCTestCase {

    private let decoder = JSONDecoder()

    // MARK: - Helpers

    /// Returns a repository whose data-loader always hands back `data`,
    /// bypassing the real bundle lookup.
    private func makeRepo(returning data: Data) -> LevelRepository {
        LevelRepository(
            urlResolver: { _ in URL(string: "fake://level") },
            dataLoader: { _ in data }
        )
    }

    /// Returns a repository whose data-loader always throws `error`.
    private func makeRepo(throwing error: Error) -> LevelRepository {
        LevelRepository(
            urlResolver: { _ in URL(string: "fake://level") },
            dataLoader: { _ in throw error }
        )
    }

    private var validLevelJSON: String {
        """
        {
          "id": "level_001",
          "name": "First Dispatch",
          "graph": {
            "nodes": [
              { "id": "start", "x": 0.0, "y": 0.0, "outgoingEdgeIDs": ["e_start_switch"] },
              { "id": "switch", "x": 1.0, "y": 0.0, "outgoingEdgeIDs": ["e_switch_package", "e_switch_dead_end", "e_switch_destination"] },
              { "id": "package", "x": 2.0, "y": 1.0, "outgoingEdgeIDs": ["e_package_return"] },
              { "id": "dead_end", "x": 2.0, "y": -1.0, "outgoingEdgeIDs": [] },
              { "id": "destination", "x": 3.0, "y": 0.0, "outgoingEdgeIDs": [] }
            ],
            "edges": [
              { "id": "e_start_switch", "fromNodeID": "start", "toNodeID": "switch" },
              { "id": "e_switch_package", "fromNodeID": "switch", "toNodeID": "package" },
              { "id": "e_package_return", "fromNodeID": "package", "toNodeID": "switch" },
              { "id": "e_switch_destination", "fromNodeID": "switch", "toNodeID": "destination" },
              { "id": "e_switch_dead_end", "fromNodeID": "switch", "toNodeID": "dead_end" }
            ]
          },
          "packageNodeID": "package",
          "destinationNodeID": "destination",
          "timeLimitSeconds": 45
        }
        """
    }

    // MARK: - Valid JSON decoding (decoder-level)

    func testDecodesValidLevelJSON() throws {
        let data = try XCTUnwrap(validLevelJSON.data(using: .utf8))
        let level = try decoder.decode(LevelData.self, from: data)

        XCTAssertEqual(level.id, "level_001")
        XCTAssertEqual(level.name, "First Dispatch")
        XCTAssertEqual(level.graph.nodes.count, 5)
        XCTAssertEqual(level.graph.edges.count, 5)
        XCTAssertEqual(level.packageNodeID, "package")
        XCTAssertEqual(level.destinationNodeID, "destination")
        XCTAssertEqual(level.timeLimitSeconds, 45)
    }

    func testSampleLevelContainsRequiredNodesAndValidReferences() throws {
        let data = try sampleLevel001Data()
        let level = try decoder.decode(LevelData.self, from: data)

        let nodesByID = Dictionary(uniqueKeysWithValues: level.graph.nodes.map { ($0.id, $0) })
        let nodeIDs = Set(nodesByID.keys)
        XCTAssertTrue(nodeIDs.contains("start"))
        XCTAssertTrue(nodeIDs.contains("switch"))
        XCTAssertTrue(nodeIDs.contains("package"))
        XCTAssertTrue(nodeIDs.contains("destination"))

        XCTAssertNotNil(nodesByID[level.packageNodeID])
        XCTAssertNotNil(nodesByID[level.destinationNodeID])

        for node in level.graph.nodes {
            try node.validateOutgoingEdges(against: level.graph.edges)
        }
        for edge in level.graph.edges {
            XCTAssertTrue(nodeIDs.contains(edge.fromNodeID), "Missing fromNodeID \(edge.fromNodeID) for edge \(edge.id)")
            XCTAssertTrue(nodeIDs.contains(edge.toNodeID), "Missing toNodeID \(edge.toNodeID) for edge \(edge.id)")
        }

        let switchNode = try XCTUnwrap(nodesByID["switch"])
        XCTAssertGreaterThan(switchNode.outgoingEdgeIDs.count, 1, "Switch node should offer multiple paths")

        let deadEndNode = try XCTUnwrap(nodesByID["dead_end"])
        XCTAssertTrue(deadEndNode.outgoingEdgeIDs.isEmpty, "Wrong path should terminate in a dead-end")

        let adjacency = Dictionary(grouping: level.graph.edges, by: \.fromNodeID)
            .mapValues { edges in edges.map(\.toNodeID) }

        let canReachPackage = isReachable(from: "start", to: level.packageNodeID, adjacency: adjacency)
        XCTAssertTrue(canReachPackage, "Expected a path from start to package")

        let canReachDestination = isReachable(from: level.packageNodeID, to: level.destinationNodeID, adjacency: adjacency)
        XCTAssertTrue(canReachDestination, "Expected a path from package to destination")
    }

    func testDecodesEdgeFieldsCorrectly() throws {
        let json = """
        {
          "id": "level_001",
          "name": "Test",
          "graph": {
            "nodes": [
              { "id": "a", "x": 0.0, "y": 0.0, "outgoingEdgeIDs": ["e1"] },
              { "id": "b", "x": 5.0, "y": 3.0, "outgoingEdgeIDs": [] }
            ],
            "edges": [
              { "id": "e1", "fromNodeID": "a", "toNodeID": "b" }
            ]
          },
          "packageNodeID": "a",
          "destinationNodeID": "b",
          "timeLimitSeconds": 60
        }
        """
        let data = try XCTUnwrap(json.data(using: .utf8))
        let level = try decoder.decode(LevelData.self, from: data)

        let edge = try XCTUnwrap(level.graph.edges.first)
        XCTAssertEqual(edge.id, "e1")
        XCTAssertEqual(edge.fromNodeID, "a")
        XCTAssertEqual(edge.toNodeID, "b")
    }

    func testDecodesEmptyGraphLevel() throws {
        let json = """
        {
          "id": "level_empty",
          "name": "Empty",
          "graph": { "nodes": [], "edges": [] },
          "packageNodeID": "",
          "destinationNodeID": "",
          "timeLimitSeconds": 10
        }
        """
        let data = try XCTUnwrap(json.data(using: .utf8))
        let level = try decoder.decode(LevelData.self, from: data)

        XCTAssertTrue(level.graph.nodes.isEmpty)
        XCTAssertTrue(level.graph.edges.isEmpty)
    }

    // MARK: - Malformed JSON (decoder-level)

    func testMalformedJSONThrowsDecodingError() throws {
        let data = try XCTUnwrap("{ not valid json }".data(using: .utf8))
        XCTAssertThrowsError(try decoder.decode(LevelData.self, from: data))
    }

    // MARK: - Missing required fields (decoder-level)

    func testMissingIDFieldThrowsDecodingError() throws {
        let json = """
        {
          "name": "Missing ID",
          "graph": { "nodes": [], "edges": [] },
          "packageNodeID": "n1",
          "destinationNodeID": "n2",
          "timeLimitSeconds": 30
        }
        """
        let data = try XCTUnwrap(json.data(using: .utf8))
        XCTAssertThrowsError(try decoder.decode(LevelData.self, from: data))
    }

    func testMissingGraphFieldThrowsDecodingError() throws {
        let json = """
        {
          "id": "level_001",
          "name": "No Graph",
          "packageNodeID": "n1",
          "destinationNodeID": "n2",
          "timeLimitSeconds": 30
        }
        """
        let data = try XCTUnwrap(json.data(using: .utf8))
        XCTAssertThrowsError(try decoder.decode(LevelData.self, from: data))
    }

    func testMissingNodesKeyInGraphThrowsDecodingError() throws {
        let json = """
        {
          "id": "level_001",
          "name": "No Nodes",
          "graph": { "edges": [] },
          "packageNodeID": "n1",
          "destinationNodeID": "n2",
          "timeLimitSeconds": 30
        }
        """
        let data = try XCTUnwrap(json.data(using: .utf8))
        XCTAssertThrowsError(try decoder.decode(LevelData.self, from: data))
    }

    func testMissingEdgesKeyInGraphThrowsDecodingError() throws {
        let json = """
        {
          "id": "level_001",
          "name": "No Edges",
          "graph": { "nodes": [] },
          "packageNodeID": "n1",
          "destinationNodeID": "n2",
          "timeLimitSeconds": 30
        }
        """
        let data = try XCTUnwrap(json.data(using: .utf8))
        XCTAssertThrowsError(try decoder.decode(LevelData.self, from: data))
    }

    // MARK: - LevelRepository: successful load path

    func testLoadLevelViaRepositorySucceedsWithValidData() throws {
        let data = try XCTUnwrap(validLevelJSON.data(using: .utf8))
        let repo = makeRepo(returning: data)
        let level = try repo.loadLevel(id: "level_001")

        XCTAssertEqual(level.id, "level_001")
        XCTAssertEqual(level.name, "First Dispatch")
        XCTAssertEqual(level.graph.nodes.count, 5)
        XCTAssertEqual(level.graph.edges.count, 5)
        XCTAssertEqual(level.packageNodeID, "package")
        XCTAssertEqual(level.destinationNodeID, "destination")
        XCTAssertEqual(level.timeLimitSeconds, 45)
    }

    // MARK: - LevelRepository: .fileNotFound error

    func testLoadLevelReturnsFileNotFoundForUnknownID() {
        // Use the test bundle, which does not contain level JSON files.
        let repo = LevelRepository(bundle: Bundle(for: LevelRepositoryTests.self))

        XCTAssertThrowsError(try repo.loadLevel(id: "nonexistent_level")) { error in
            guard case LevelRepositoryError.fileNotFound(let id) = error else {
                return XCTFail("Expected fileNotFound, got \(error)")
            }
            XCTAssertEqual(id, "nonexistent_level")
        }
    }

    // MARK: - LevelRepository: .readFailed error

    func testLoadLevelThrowsReadFailedForIOError() {
        let ioError = NSError(domain: NSCocoaErrorDomain, code: NSFileNoSuchFileError)
        let repo = makeRepo(throwing: ioError)

        XCTAssertThrowsError(try repo.loadLevel(id: "level_001")) { error in
            guard case LevelRepositoryError.readFailed(let id, _) = error else {
                return XCTFail("Expected readFailed, got \(error)")
            }
            XCTAssertEqual(id, "level_001")
        }
    }

    // MARK: - LevelRepository: .decodingFailed error

    func testLoadLevelThrowsDecodingFailedForMalformedJSON() throws {
        let data = try XCTUnwrap("{ not valid json }".data(using: .utf8))
        let repo = makeRepo(returning: data)

        XCTAssertThrowsError(try repo.loadLevel(id: "level_001")) { error in
            guard case LevelRepositoryError.decodingFailed(let id, _) = error else {
                return XCTFail("Expected decodingFailed, got \(error)")
            }
            XCTAssertEqual(id, "level_001")
        }
    }

    func testLoadLevelThrowsDecodingFailedForMissingRequiredField() throws {
        let missingIDJSON = """
        {
          "name": "Missing ID",
          "graph": { "nodes": [], "edges": [] },
          "packageNodeID": "n1",
          "destinationNodeID": "n2",
          "timeLimitSeconds": 30
        }
        """
        let data = try XCTUnwrap(missingIDJSON.data(using: .utf8))
        let repo = makeRepo(returning: data)

        XCTAssertThrowsError(try repo.loadLevel(id: "level_001")) { error in
            guard case LevelRepositoryError.decodingFailed(let id, _) = error else {
                return XCTFail("Expected decodingFailed, got \(error)")
            }
            XCTAssertEqual(id, "level_001")
        }
    }

    // MARK: - LevelRepository: loadAllLevels

    func testLoadAllLevelsReturnsEmptyWhenNoBundledLevels() throws {
        let repo = LevelRepository(
            urlResolver: { _ in nil },
            dataLoader: { _ in Data() },
            allLevelURLs: { [] }
        )
        let levels = try repo.loadAllLevels()
        XCTAssertTrue(levels.isEmpty)
    }

    func testLoadAllLevelsReturnsDecodedLevels() throws {
        let data = try XCTUnwrap(validLevelJSON.data(using: .utf8))
        let url = try XCTUnwrap(URL(string: "fake://levels/level_001.json"))
        let repo = LevelRepository(
            urlResolver: { _ in nil },
            dataLoader: { _ in data },
            allLevelURLs: { [url] }
        )
        let levels = try repo.loadAllLevels()
        XCTAssertEqual(levels.count, 1)
        XCTAssertEqual(levels.first?.id, "level_001")
    }

    func testLoadAllLevelsThrowsReadFailedOnIOError() throws {
        let ioError = NSError(domain: NSCocoaErrorDomain, code: NSFileNoSuchFileError)
        let url = try XCTUnwrap(URL(string: "fake://levels/level_001.json"))
        let repo = LevelRepository(
            urlResolver: { _ in nil },
            dataLoader: { _ in throw ioError },
            allLevelURLs: { [url] }
        )
        XCTAssertThrowsError(try repo.loadAllLevels()) { error in
            guard case LevelRepositoryError.readFailed(let id, _) = error else {
                return XCTFail("Expected readFailed, got \(error)")
            }
            XCTAssertEqual(id, "level_001")
        }
    }

    func testLoadAllLevelsThrowsDecodingFailedForMalformedJSON() throws {
        let badData = try XCTUnwrap("{ not valid json }".data(using: .utf8))
        let url = try XCTUnwrap(URL(string: "fake://levels/level_001.json"))
        let repo = LevelRepository(
            urlResolver: { _ in nil },
            dataLoader: { _ in badData },
            allLevelURLs: { [url] }
        )
        XCTAssertThrowsError(try repo.loadAllLevels()) { error in
            guard case LevelRepositoryError.decodingFailed(let id, _) = error else {
                return XCTFail("Expected decodingFailed, got \(error)")
            }
            XCTAssertEqual(id, "level_001")
        }
    }

    private func isReachable(from startID: String, to targetID: String, adjacency: [String: [String]]) -> Bool {
        var visited = Set<String>()
        var queue: [String] = [startID]

        while !queue.isEmpty {
            let currentID = queue.removeFirst()
            if currentID == targetID {
                return true
            }

            guard visited.insert(currentID).inserted else {
                continue
            }

            queue.append(contentsOf: adjacency[currentID, default: []])
        }

        return false
    }

    private func sampleLevel001Data() throws -> Data {
        let bundles = [Bundle.main, Bundle(for: LevelRepositoryTests.self)]
        for bundle in bundles {
            if let levelURL = bundle.url(forResource: "level_001", withExtension: "json", subdirectory: "Levels") {
                return try Data(contentsOf: levelURL)
            }
        }

        throw LevelRepositoryError.fileNotFound(id: "level_001")
    }
}
