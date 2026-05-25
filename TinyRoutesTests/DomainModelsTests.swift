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
            startNodeID: "n1",
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
        let profile = PlayerProfile.defaultValue
        let cosmetic = CosmeticItem(id: "trail_basic", type: .trail)

        XCTAssertTrue(profile.unlockedLevelIDs.contains("level_001"))
        XCTAssertEqual(profile.coinTotal, 0)
        XCTAssertTrue(profile.ownedCosmeticIDs.contains("themeOceanDrive"))
        XCTAssertTrue(profile.ownedCosmeticIDs.contains("dotCourierBlue"))
        XCTAssertTrue(profile.ownedCosmeticIDs.contains("trailClean"))
        XCTAssertTrue(profile.ownedCosmeticIDs.contains("confettiStars"))
        XCTAssertTrue(profile.ownedCosmeticIDs.contains("destinationFlag"))
        XCTAssertEqual(
            profile.selectedCosmeticIDByCategoryID[ShopCosmeticCategoryID.routeThemes],
            "themeOceanDrive"
        )
        XCTAssertFalse(cosmetic.isUnlocked)
        XCTAssertEqual(cosmetic.type, .trail)
    }

    func testPlayerProfileNormalizesCorruptStarValuesAndCompletedLevels() {
        let profile = PlayerProfile(
            unlockedLevelIDs: ["level_001", ""],
            completedLevelIDs: [""],
            bestStarsByLevelID: [
                "level_001": 9,
                "level_002": -4,
                "": 2
            ]
        ).normalized()

        XCTAssertEqual(profile.bestStarsByLevelID["level_001"], 3)
        XCTAssertEqual(profile.bestStarsByLevelID["level_002"], 0)
        XCTAssertNil(profile.bestStarsByLevelID[""])
        XCTAssertTrue(profile.completedLevelIDs.contains("level_001"))
        XCTAssertFalse(profile.completedLevelIDs.contains(""))
    }

    func testPlayerProfileNormalizesNegativeCoinsAndTimingValues() {
        let profile = PlayerProfile(
            coinTotal: -100,
            lifetimeCoinsEarned: -200,
            lifetimeCoinsSpent: -300,
            bestStreakDays: -7,
            currentStreakDays: -2,
            fastestCompletionTimeByLevelID: ["level_001": -1, "level_002": 18]
        ).normalized()

        XCTAssertEqual(profile.coinTotal, 0)
        XCTAssertEqual(profile.lifetimeCoinsEarned, 0)
        XCTAssertEqual(profile.lifetimeCoinsSpent, 0)
        XCTAssertEqual(profile.bestStreakDays, 0)
        XCTAssertEqual(profile.currentStreakDays, 0)
        XCTAssertNil(profile.fastestCompletionTimeByLevelID["level_001"])
        XCTAssertEqual(profile.fastestCompletionTimeByLevelID["level_002"], 18)
    }

    func testPlayerProfileFallsBackWhenSelectedCosmeticIsInvalid() {
        let profile = PlayerProfile(
            ownedCosmeticIDs: ["themeClassic"],
            selectedCosmeticIDByCategoryID: [
                ShopCosmeticCategoryID.routeThemes: "missingTheme",
                ShopCosmeticCategoryID.trails: ""
            ]
        ).normalized()

        XCTAssertEqual(
            profile.selectedCosmeticIDByCategoryID[ShopCosmeticCategoryID.routeThemes],
            "themeOceanDrive"
        )
        XCTAssertEqual(
            profile.selectedCosmeticIDByCategoryID[ShopCosmeticCategoryID.trails],
            "trailClean"
        )
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
