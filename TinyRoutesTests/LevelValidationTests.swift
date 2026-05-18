import XCTest
@testable import TinyRoutes

final class LevelValidationTests: XCTestCase {
    private let decoder = JSONDecoder()

    func testDuplicateNodeIDsProduceError() throws {
        let level = try decodeBrokenLevelFixture(named: "duplicate_node_ids")
        let issues = LevelValidator().validate(level: level)

        XCTAssertTrue(
            issues.contains {
                $0.severity == .error
                    && $0.levelID == level.id
                    && $0.message == "Duplicate node ID: dup_node"
            }
        )
    }

    func testDuplicateEdgeIDsProduceError() throws {
        let level = try decodeBrokenLevelFixture(named: "duplicate_edge_ids")
        let issues = LevelValidator().validate(level: level)

        XCTAssertTrue(
            issues.contains {
                $0.severity == .error
                    && $0.levelID == level.id
                    && $0.message == "Duplicate edge ID: dup_edge"
            }
        )
    }

    func testMissingStartNodeProducesError() throws {
        let level = try decodeBrokenLevelFixture(named: "missing_start_node")
        let issues = LevelValidator().validate(level: level)

        XCTAssertTrue(
            issues.contains {
                $0.severity == .error
                    && $0.levelID == level.id
                    && $0.message == "startNodeID 'start_missing' does not exist in the graph."
            }
        )
    }

    func testMissingPackageNodeProducesError() throws {
        let level = try decodeBrokenLevelFixture(named: "missing_package_node")
        let issues = LevelValidator().validate(level: level)

        XCTAssertTrue(
            issues.contains {
                $0.severity == .error
                    && $0.levelID == level.id
                    && $0.message == "packageNodeID 'package_missing' does not exist in the graph."
            }
        )
    }

    func testMissingDestinationNodeProducesError() throws {
        let level = try decodeBrokenLevelFixture(named: "missing_destination_node")
        let issues = LevelValidator().validate(level: level)

        XCTAssertTrue(
            issues.contains {
                $0.severity == .error
                    && $0.levelID == level.id
                    && $0.message == "destinationNodeID 'destination_missing' does not exist in the graph."
            }
        )
    }

    func testValidationReturnsAllDuplicateIssuesNotOnlyFirst() {
        let level = makeLevelWithMultipleDuplicateIDs()
        let issues = LevelValidator().validate(level: level)
        let messages = Set(issues.map(\.message))

        XCTAssertEqual(issues.count, 3)
        XCTAssertEqual(
            messages,
            Set([
                "Duplicate node ID: dup_node_a",
                "Duplicate node ID: dup_node_b",
                "Duplicate edge ID: dup_edge"
            ])
        )
    }

    private func decodeBrokenLevelFixture(named fixtureName: String) throws -> LevelData {
        let fixtureURL = URL(fileURLWithPath: #filePath)
            .deletingLastPathComponent()
            .appendingPathComponent("Fixtures")
            .appendingPathComponent("BrokenLevels")
            .appendingPathComponent("\(fixtureName).json")
        let data = try Data(contentsOf: fixtureURL)
        return try decoder.decode(LevelData.self, from: data)
    }

    private func makeLevelWithMultipleDuplicateIDs() -> LevelData {
        let nodes = [
            RouteNode(id: "start", x: 0, y: 0, outgoingEdgeIDs: ["dup_edge"]),
            RouteNode(id: "dup_node_a", x: 1, y: 0, outgoingEdgeIDs: []),
            RouteNode(id: "dup_node_a", x: 2, y: 0, outgoingEdgeIDs: []),
            RouteNode(id: "dup_node_b", x: 3, y: 0, outgoingEdgeIDs: []),
            RouteNode(id: "dup_node_b", x: 4, y: 0, outgoingEdgeIDs: [])
        ]
        let edges = [
            RouteEdge(id: "dup_edge", fromNodeID: "start", toNodeID: "dup_node_a"),
            RouteEdge(id: "dup_edge", fromNodeID: "start", toNodeID: "dup_node_b")
        ]

        return LevelData(
            id: "level_multiple_duplicates",
            name: "Multiple Duplicate IDs",
            graph: RouteGraph(nodes: nodes, edges: edges),
            startNodeID: "start",
            packageNodeID: "dup_node_a",
            destinationNodeID: "dup_node_b",
            timeLimitSeconds: 30,
            parTaps: 2
        )
    }
}
