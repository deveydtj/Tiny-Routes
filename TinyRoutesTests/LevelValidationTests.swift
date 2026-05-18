import XCTest
@testable import TinyRoutes

final class LevelValidationTests: XCTestCase {
    private let decoder = JSONDecoder()

    func testEmptyLevelIDProducesError() throws {
        let level = try decodeBrokenLevelFixture(named: "empty_level_id")
        let issues = LevelValidator().validate(level: level)

        XCTAssertTrue(
            issues.contains {
                $0.severity == .error
                    && $0.levelID == level.id
                    && $0.message == "Level id must not be empty"
            }
        )
    }

    func testEmptyLevelNameProducesError() throws {
        let level = try decodeBrokenLevelFixture(named: "empty_level_name")
        let issues = LevelValidator().validate(level: level)

        XCTAssertTrue(
            issues.contains {
                $0.severity == .error
                    && $0.levelID == level.id
                    && $0.message == "Level name must not be empty"
            }
        )
    }

    func testNonPositiveTimeLimitProducesError() throws {
        let level = try decodeBrokenLevelFixture(named: "non_positive_time_limit")
        let issues = LevelValidator().validate(level: level)

        XCTAssertTrue(
            issues.contains {
                $0.severity == .error
                    && $0.levelID == level.id
                    && $0.message == "timeLimitSeconds must be greater than 0"
            }
        )
    }

    func testNegativeParTapsProducesError() throws {
        let level = try decodeBrokenLevelFixture(named: "negative_par_taps")
        let issues = LevelValidator().validate(level: level)

        XCTAssertTrue(
            issues.contains {
                $0.severity == .error
                    && $0.levelID == level.id
                    && $0.message == "parTaps must be greater than or equal to 0"
            }
        )
    }

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
                    && $0.message == "startNodeID 'start_missing' does not exist in the graph"
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
                    && $0.message == "packageNodeID 'package_missing' does not exist in the graph"
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
                    && $0.message == "destinationNodeID 'destination_missing' does not exist in the graph"
            }
        )
    }

    func testEdgeWithUnknownFromNodeIDProducesError() throws {
        let level = try decodeBrokenLevelFixture(named: "edge_unknown_from_node")
        let issues = LevelValidator().validate(level: level)

        XCTAssertTrue(
            issues.contains {
                $0.severity == .error
                    && $0.levelID == level.id
                    && $0.message == "Edge 'e_ghost_package' references unknown fromNodeID 'ghost_node'"
            }
        )
    }

    func testEdgeWithUnknownToNodeIDProducesError() throws {
        let level = try decodeBrokenLevelFixture(named: "edge_unknown_to_node")
        let issues = LevelValidator().validate(level: level)

        XCTAssertTrue(
            issues.contains {
                $0.severity == .error
                    && $0.levelID == level.id
                    && $0.message == "Edge 'e_start_ghost' references unknown toNodeID 'ghost_dest'"
            }
        )
    }

    func testDuplicateOutgoingEdgeIDsProduceError() throws {
        let level = try decodeBrokenLevelFixture(named: "duplicate_outgoing_edge_ids")
        let issues = LevelValidator().validate(level: level)

        XCTAssertTrue(
            issues.contains {
                $0.severity == .error
                    && $0.levelID == level.id
                    && $0.message == "Node 'start' has duplicate outgoingEdgeIDs: e_start_package"
            }
        )
    }

    func testUnknownOutgoingEdgeIDProducesError() throws {
        let level = try decodeBrokenLevelFixture(named: "missing_outgoing_edge_id")
        let issues = LevelValidator().validate(level: level)

        XCTAssertTrue(
            issues.contains {
                $0.severity == .error
                    && $0.levelID == level.id
                    && $0.message == "Node 'start' lists unknown outgoing edge ID 'e_missing_edge'"
            }
        )
    }

    func testOmittedOutgoingGraphEdgeProducesError() throws {
        let level = try decodeBrokenLevelFixture(named: "omitted_outgoing_graph_edge")
        let issues = LevelValidator().validate(level: level)

        XCTAssertTrue(
            issues.contains {
                $0.severity == .error
                    && $0.levelID == level.id
                    && $0.message == "Node 'start' is missing outgoing edge 'e_start_package' in outgoingEdgeIDs"
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

    func testUnreachablePackageProducesError() throws {
        let level = try decodeBrokenLevelFixture(named: "unreachable_package")
        let issues = LevelValidator().validate(level: level)

        XCTAssertTrue(
            issues.contains {
                $0.severity == .error
                    && $0.levelID == level.id
                    && $0.message == "packageNodeID 'package' is unreachable from startNodeID 'start'"
            }
        )
        XCTAssertTrue(
            issues.contains {
                $0.severity == .error
                    && $0.levelID == level.id
                    && $0.message == "No directed path can satisfy start → package → destination"
            }
        )
    }

    func testUnreachableDestinationFromPackageProducesError() throws {
        let level = try decodeBrokenLevelFixture(named: "unreachable_destination_from_package")
        let issues = LevelValidator().validate(level: level)

        XCTAssertTrue(
            issues.contains {
                $0.severity == .error
                    && $0.levelID == level.id
                    && $0.message == "destinationNodeID 'destination' is unreachable from packageNodeID 'package'"
            }
        )
        XCTAssertTrue(
            issues.contains {
                $0.severity == .error
                    && $0.levelID == level.id
                    && $0.message == "No directed path can satisfy start → package → destination"
            }
        )
    }

    func testProductionLevelsPassReachabilityValidation() throws {
        let levels = try decodeProductionLevels()
        XCTAssertFalse(levels.isEmpty, "Expected production level files in TinyRoutes/Resources/Levels")

        let validator = LevelValidator()
        var failures: [String] = []

        for level in levels {
            let reachabilityIssues = validator
                .validate(level: level)
                .filter {
                    $0.message.contains("unreachable from startNodeID")
                        || $0.message.contains("unreachable from packageNodeID")
                        || $0.message == "No directed path can satisfy start → package → destination"
                }

            if !reachabilityIssues.isEmpty {
                let issueDescriptions = reachabilityIssues
                    .map(\.message)
                    .sorted()
                    .joined(separator: "; ")
                failures.append("\(level.id): \(issueDescriptions)")
            }
        }

        XCTAssertTrue(
            failures.isEmpty,
            "Production levels failed reachability validation:\n\(failures.joined(separator: "\n"))"
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

    private func decodeProductionLevels() throws -> [LevelData] {
        let levelsDirectoryURL = URL(fileURLWithPath: #filePath)
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .appendingPathComponent("TinyRoutes")
            .appendingPathComponent("Resources")
            .appendingPathComponent("Levels")

        let levelFileURLs = try FileManager.default
            .contentsOfDirectory(at: levelsDirectoryURL, includingPropertiesForKeys: nil)
            .filter { $0.pathExtension == "json" && $0.deletingPathExtension().lastPathComponent.hasPrefix("level_") }
            .sorted { $0.lastPathComponent < $1.lastPathComponent }

        return try levelFileURLs.map { fileURL in
            let data = try Data(contentsOf: fileURL)
            return try decoder.decode(LevelData.self, from: data)
        }
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
