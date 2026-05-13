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
          "name": "Getting Started",
          "graph": {
            "nodes": [
              { "id": "n1", "x": 0.0, "y": 0.0, "outgoingEdgeIDs": ["e1"] },
              { "id": "n2", "x": 1.0, "y": 0.0, "outgoingEdgeIDs": [] }
            ],
            "edges": [
              { "id": "e1", "fromNodeID": "n1", "toNodeID": "n2" }
            ]
          },
          "packageNodeID": "n1",
          "destinationNodeID": "n2",
          "timeLimitSeconds": 30
        }
        """
    }

    // MARK: - Valid JSON decoding (decoder-level)

    func testDecodesValidLevelJSON() throws {
        let data = try XCTUnwrap(validLevelJSON.data(using: .utf8))
        let level = try decoder.decode(LevelData.self, from: data)

        XCTAssertEqual(level.id, "level_001")
        XCTAssertEqual(level.name, "Getting Started")
        XCTAssertEqual(level.graph.nodes.count, 2)
        XCTAssertEqual(level.graph.edges.count, 1)
        XCTAssertEqual(level.packageNodeID, "n1")
        XCTAssertEqual(level.destinationNodeID, "n2")
        XCTAssertEqual(level.timeLimitSeconds, 30)
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
        XCTAssertEqual(level.name, "Getting Started")
        XCTAssertEqual(level.graph.nodes.count, 2)
        XCTAssertEqual(level.graph.edges.count, 1)
        XCTAssertEqual(level.packageNodeID, "n1")
        XCTAssertEqual(level.destinationNodeID, "n2")
        XCTAssertEqual(level.timeLimitSeconds, 30)
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
}

