import XCTest
@testable import TinyRoutes

final class LevelRepositoryTests: XCTestCase {

    private let decoder = JSONDecoder()

    // MARK: - Valid JSON decoding

    func testDecodesValidLevelJSON() throws {
        let json = """
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
        let data = try XCTUnwrap(json.data(using: .utf8))
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

    // MARK: - Malformed JSON

    func testMalformedJSONThrowsDecodingError() throws {
        let json = "{ not valid json }"
        let data = try XCTUnwrap(json.data(using: .utf8))

        XCTAssertThrowsError(try decoder.decode(LevelData.self, from: data))
    }

    // MARK: - Missing required fields

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

    // MARK: - LevelRepository file-not-found error

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
}
