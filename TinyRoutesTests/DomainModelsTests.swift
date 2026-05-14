import XCTest
@testable import TinyRoutes

final class DomainModelsTests: XCTestCase {
    func testLevelDataAndGraphCanBeInstantiated() {
        let nodes = [
            RouteNode(id: "n1", x: 0, y: 0, outgoingEdgeIDs: ["e1"]),
            RouteNode(id: "n2", x: 1, y: 0, outgoingEdgeIDs: [])
        ]
        let edges = [
            RouteEdge(id: "e1", fromNodeID: "n1", toNodeID: "n2")
        ]

        let graph = RouteGraph(nodes: nodes, edges: edges)
        let levelData = LevelData(
            id: "level_001",
            name: "Getting Started",
            graph: graph,
            packageNodeID: "n1",
            destinationNodeID: "n2",
            timeLimitSeconds: 30,
            parTaps: 4
        )

        XCTAssertEqual(levelData.id, "level_001")
        XCTAssertEqual(levelData.graph.nodes.count, 2)
        XCTAssertEqual(levelData.graph.edges.count, 1)
    }

    func testGraphEdgesReferenceExistingNodes() {
        let nodes = [
            RouteNode(id: "start", x: 0, y: 0, outgoingEdgeIDs: ["e1"]),
            RouteNode(id: "finish", x: 1, y: 0, outgoingEdgeIDs: [])
        ]
        let edges = [
            RouteEdge(id: "e1", fromNodeID: "start", toNodeID: "finish")
        ]

        let graph = RouteGraph(nodes: nodes, edges: edges)
        let validNodeIDs = Set(graph.nodes.map(\.id))

        for edge in graph.edges {
            XCTAssertTrue(validNodeIDs.contains(edge.fromNodeID))
            XCTAssertTrue(validNodeIDs.contains(edge.toNodeID))
        }
    }

    func testProfileAndCosmeticDefaults() {
        let profile = PlayerProfile()
        let cosmetic = CosmeticItem(id: "trail_basic", type: .trail)

        XCTAssertTrue(profile.unlockedLevelIDs.contains("level_001"))
        XCTAssertEqual(profile.coinTotal, 0)
        XCTAssertFalse(cosmetic.isUnlocked)
        XCTAssertEqual(cosmetic.type, .trail)
    }

    func testValidateOutgoingEdgesThrowsForDuplicateOutgoingEdgeIDs() {
        let node = RouteNode(id: "n1", x: 0, y: 0, outgoingEdgeIDs: ["e1", "e1"])
        let edges = [
            RouteEdge(id: "e1", fromNodeID: "n1", toNodeID: "n2")
        ]

        XCTAssertThrowsError(try node.validateOutgoingEdges(against: edges)) { error in
            guard case let RouteNodeValidationError.duplicateOutgoingEdgeIDs(nodeID, duplicateEdgeIDs) = error else {
                return XCTFail("Expected duplicateOutgoingEdgeIDs, got \(error)")
            }

            XCTAssertEqual(nodeID, "n1")
            XCTAssertEqual(duplicateEdgeIDs, ["e1"])
        }
    }

    func testValidateOutgoingEdgesThrowsForDuplicateOutgoingGraphEdgeIDs() {
        let node = RouteNode(id: "n1", x: 0, y: 0, outgoingEdgeIDs: ["e1"])
        let edges = [
            RouteEdge(id: "e1", fromNodeID: "n1", toNodeID: "n2"),
            RouteEdge(id: "e1", fromNodeID: "n1", toNodeID: "n3")
        ]

        XCTAssertThrowsError(try node.validateOutgoingEdges(against: edges)) { error in
            guard case let RouteNodeValidationError.duplicateOutgoingGraphEdgeIDs(nodeID, duplicateEdgeIDs) = error else {
                return XCTFail("Expected duplicateOutgoingGraphEdgeIDs, got \(error)")
            }

            XCTAssertEqual(nodeID, "n1")
            XCTAssertEqual(duplicateEdgeIDs, ["e1"])
        }
    }
}
