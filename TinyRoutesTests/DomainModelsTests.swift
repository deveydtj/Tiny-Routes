import XCTest
@testable import TinyRoutes

final class DomainModelsTests: XCTestCase {
    private let decoder = JSONDecoder()
    private let encoder = JSONEncoder()

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

    func testVersionOneJSONUsesEffectiveLegacyRules() throws {
        let level = try decoder.decode(LevelData.self, from: Data(Self.versionOneJSON.utf8))

        XCTAssertNil(level.schemaVersion)
        XCTAssertNil(level.rules)
        XCTAssertEqual(level.effectiveRules, .legacyDefaults)
    }

    func testVersionTwoJSONLoadsExplicitLiveRulesAndUnknownFields() throws {
        let level = try decoder.decode(LevelData.self, from: Data(Self.versionTwoJSON.utf8))

        XCTAssertEqual(level.schemaVersion, 2)
        XCTAssertEqual(level.effectiveRules.switchInteractionMode, .liveLookahead)
        XCTAssertEqual(level.effectiveRules.switchLookaheadSeconds, 1.75)
        XCTAssertEqual(level.effectiveRules.switchTapCooldownSeconds, 0.2)
        XCTAssertEqual(level.tutorialMessage, "Tap the highlighted switch.")
    }

    func testVersionTwoRulesRoundTrip() throws {
        let original = try decoder.decode(LevelData.self, from: Data(Self.versionTwoJSON.utf8))
        let decoded = try decoder.decode(LevelData.self, from: encoder.encode(original))

        XCTAssertEqual(decoded.schemaVersion, 2)
        XCTAssertEqual(decoded.rules, original.rules)
    }

    func testRoadAvailabilityDefaultsToAlwaysWhenMissing() throws {
        let json = #"{"id":"edge","fromNodeID":"a","toNodeID":"b"}"#

        let edge = try decoder.decode(RouteEdge.self, from: Data(json.utf8))

        XCTAssertEqual(edge.availability, .always)
    }

    func testRoadAvailabilityValuesRoundTrip() throws {
        for availability in RoadAvailability.allCases {
            let edge = RouteEdge(
                id: "edge_\(availability.rawValue)",
                fromNodeID: "a",
                toNodeID: "b",
                availability: availability
            )

            let decoded = try decoder.decode(RouteEdge.self, from: encoder.encode(edge))

            XCTAssertEqual(decoded.availability, availability)
        }
    }

    func testUnknownRoadAvailabilityFailsDecoding() {
        let json = #"{"id":"edge","fromNodeID":"a","toNodeID":"b","availability":"sometimes"}"#

        XCTAssertThrowsError(
            try decoder.decode(RouteEdge.self, from: Data(json.utf8))
        )
    }

    func testInvalidRuleNumbersProduceValidationIssues() throws {
        var level = try decoder.decode(LevelData.self, from: Data(Self.versionTwoJSON.utf8))
        level.rules = LevelRules(
            switchInteractionMode: .liveLookahead,
            switchLookaheadSeconds: -.infinity,
            switchTapCooldownSeconds: -0.1
        )

        let messages = Set(LevelValidator().validate(level: level).map(\.message))
        XCTAssertTrue(messages.contains("rules.switchLookaheadSeconds must be finite and greater than 0"))
        XCTAssertTrue(messages.contains("rules.switchTapCooldownSeconds must be finite and greater than or equal to 0"))
    }

    private static let versionOneJSON = """
    {
      "id": "legacy", "name": "Legacy",
      "graph": {"nodes": [{"id": "n", "x": 0, "y": 0, "outgoingEdgeIDs": []}], "edges": []},
      "startNodeID": "n", "packageNodeID": "n", "destinationNodeID": "n",
      "timeLimitSeconds": 30, "parTaps": 0
    }
    """

    private static let versionTwoJSON = """
    {
      "schemaVersion": 2,
      "rules": {
        "switchInteractionMode": "liveLookahead",
        "switchLookaheadSeconds": 1.75,
        "switchTapCooldownSeconds": 0.2
      },
      "id": "modern", "name": "Modern",
      "graph": {"nodes": [{"id": "n", "x": 0, "y": 0, "outgoingEdgeIDs": []}], "edges": []},
      "startNodeID": "n", "packageNodeID": "n", "destinationNodeID": "n",
      "timeLimitSeconds": 30, "parTaps": 0,
      "tutorialMessage": "Tap the highlighted switch.",
      "futureExtension": {"ignored": true}
    }
    """

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
