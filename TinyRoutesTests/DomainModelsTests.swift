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
        XCTAssertNil(level.objectives)
        XCTAssertEqual(level.effectiveRules, .legacyDefaults)
    }

    func testVersionTwoJSONLoadsExplicitLiveRulesAndUnknownFields() throws {
        let level = try decoder.decode(LevelData.self, from: Data(Self.versionTwoJSON.utf8))

        XCTAssertEqual(level.schemaVersion, 2)
        XCTAssertEqual(level.effectiveRules.switchInteractionMode, .liveLookahead)
        XCTAssertEqual(level.effectiveRules.switchLookaheadSeconds, 1.75)
        XCTAssertEqual(level.effectiveRules.switchTapCooldownSeconds, 0.2)
        XCTAssertEqual(level.tutorialMessage, "Tap the highlighted switch.")
        XCTAssertNil(level.objectives)
    }

    func testVersionTwoRulesRoundTrip() throws {
        let original = try decoder.decode(LevelData.self, from: Data(Self.versionTwoJSON.utf8))
        let decoded = try decoder.decode(LevelData.self, from: encoder.encode(original))

        XCTAssertEqual(decoded.schemaVersion, 2)
        XCTAssertEqual(decoded.rules, original.rules)
    }

    func testVersionThreeObjectivesDecodeAllKindsAndDisplayMetadata() throws {
        let level = try decoder.decode(LevelData.self, from: Data(Self.versionThreeJSON.utf8))
        let objectives = try XCTUnwrap(level.objectives)

        XCTAssertEqual(level.schemaVersion, 3)
        XCTAssertEqual(objectives.map(\.kind), RouteObjectiveKind.allCases)
        XCTAssertEqual(objectives.map(\.sequenceIndex), [0, 1, 2, 3])
        XCTAssertEqual(objectives[0].displayMetadata?["title"], .string("Collect the parcel"))
        XCTAssertEqual(
            objectives[0].displayMetadata?["marker"],
            .object(["priority": .integer(1), "visible": .boolean(true)])
        )
        XCTAssertEqual(
            objectives[0].additionalFields["futureBehavior"],
            .object(["pulse": .boolean(true)])
        )
    }

    func testVersionThreeObjectivesPreserveUnknownFieldsWhenRoundTripped() throws {
        let original = try decoder.decode(LevelData.self, from: Data(Self.versionThreeJSON.utf8))
        let encoded = try encoder.encode(original)
        let decoded = try decoder.decode(LevelData.self, from: encoded)
        let objectives = try XCTUnwrap(decoded.objectives)

        XCTAssertEqual(objectives, original.objectives)
        XCTAssertEqual(
            objectives[0].additionalFields["futureBehavior"],
            .object(["pulse": .boolean(true)])
        )
        XCTAssertEqual(objectives[3].displayMetadata, nil)

        let json = try XCTUnwrap(JSONSerialization.jsonObject(with: encoded) as? [String: Any])
        let encodedObjectives = try XCTUnwrap(json["objectives"] as? [[String: Any]])
        XCTAssertTrue(encodedObjectives[3].keys.contains("displayMetadata"))
        XCTAssertTrue(encodedObjectives[3]["displayMetadata"] is NSNull)
    }

    func testUnknownRouteObjectiveKindFailsDecoding() {
        let json = """
        {
          "id": "unknown", "nodeID": "node", "kind": "mystery",
          "sequenceIndex": 0, "revealPolicy": "always"
        }
        """

        XCTAssertThrowsError(
            try decoder.decode(RouteObjective.self, from: Data(json.utf8))
        )
    }

    func testLegacyPackageAndDestinationAdaptToEffectiveObjectivesWithoutRewriting() throws {
        for json in [Self.versionOneJSON, Self.versionTwoJSON] {
            let level = try decoder.decode(LevelData.self, from: Data(json.utf8))
            let objectives = level.effectiveObjectives

            XCTAssertEqual(objectives.map(\.id), ["legacy_pickup", "legacy_destination"])
            XCTAssertEqual(objectives.map(\.nodeID), [level.packageNodeID, level.destinationNodeID])
            XCTAssertEqual(objectives.map(\.kind), [.pickup, .destination])
            XCTAssertEqual(objectives.map(\.sequenceIndex), [0, 1])
            XCTAssertNil(level.objectives)

            let encoded = try XCTUnwrap(
                JSONSerialization.jsonObject(with: encoder.encode(level)) as? [String: Any]
            )
            XCTAssertNil(encoded["objectives"])
        }
    }

    func testSchemaThreeUsesAuthoredEffectiveObjectivesAndPassesValidation() throws {
        let level = try decoder.decode(LevelData.self, from: Data(Self.versionThreeJSON.utf8))

        XCTAssertEqual(level.effectiveObjectives, level.objectives)
        XCTAssertTrue(level.validateObjectives().isEmpty)
    }

    func testSchemaThreeObjectiveValidationRejectsContractViolations() throws {
        let original = try decoder.decode(LevelData.self, from: Data(Self.versionThreeJSON.utf8))

        var duplicate = original
        let firstObjectiveID = duplicate.objectives?[0].id ?? "collect"
        duplicate.objectives?[1].id = firstObjectiveID
        XCTAssertTrue(duplicate.validateObjectives().map(\.code).contains("duplicate_objective_id"))

        var noncontiguous = original
        noncontiguous.objectives?[1].sequenceIndex = 4
        XCTAssertTrue(noncontiguous.validateObjectives().map(\.code).contains(
            "noncontiguous_objective_sequence_indices"
        ))

        var missingNode = original
        missingNode.objectives?[0].nodeID = "missing"
        XCTAssertTrue(missingNode.validateObjectives().map(\.code).contains("objective_node_not_found"))

        var noTerminal = original
        noTerminal.objectives?[3].kind = .checkpoint
        XCTAssertTrue(noTerminal.validateObjectives().map(\.code).contains(
            "invalid_terminal_objective_count"
        ))

        var terminalNotFinal = original
        terminalNotFinal.objectives?.swapAt(2, 3)
        terminalNotFinal.objectives?[2].sequenceIndex = 2
        terminalNotFinal.objectives?[3].sequenceIndex = 3
        XCTAssertTrue(terminalNotFinal.validateObjectives().map(\.code).contains(
            "terminal_objective_not_final"
        ))
    }

    func testObjectiveValidationRejectsSchemaAndLegacyAliasConflicts() throws {
        var legacy = try decoder.decode(LevelData.self, from: Data(Self.versionThreeJSON.utf8))
        legacy.schemaVersion = 2
        XCTAssertEqual(legacy.validateObjectives().map(\.code), ["objectives_require_schema_3"])

        var missing = try decoder.decode(LevelData.self, from: Data(Self.versionThreeJSON.utf8))
        missing.objectives = nil
        XCTAssertEqual(missing.validateObjectives().map(\.code), ["schema_3_objectives_required"])

        var conflicts = try decoder.decode(LevelData.self, from: Data(Self.versionThreeJSON.utf8))
        conflicts.packageNodeID = "start"
        conflicts.destinationNodeID = "delivery"
        let codes = Set(conflicts.validateObjectives().map(\.code))
        XCTAssertTrue(codes.contains("legacy_package_objective_conflict"))
        XCTAssertTrue(codes.contains("legacy_destination_objective_conflict"))

        let messages = Set(LevelValidator().validate(level: conflicts).map(\.message))
        XCTAssertTrue(messages.contains(
            "packageNodeID must match the first schema 3 pickup objective nodeID."
        ))
        XCTAssertTrue(messages.contains(
            "destinationNodeID must match the schema 3 destination objective nodeID."
        ))
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

    func testStructuredEdgeAvailabilityRuleRoundTrips() throws {
        let rule = EdgeAvailabilityRule(
            requiredCompletedObjectiveIDs: ["collect"],
            forbiddenCompletedObjectiveIDs: ["finish"],
            minimumObjectiveIndex: 1,
            maximumObjectiveIndex: 2,
            usageLimit: 1
        )
        let edge = RouteEdge(
            id: "objective_gate",
            fromNodeID: "a",
            toNodeID: "b",
            availabilityRule: rule
        )

        let decoded = try decoder.decode(RouteEdge.self, from: encoder.encode(edge))

        XCTAssertEqual(decoded.availabilityRule, rule)
    }

    func testLegacyRoadAvailabilityAdaptsToObjectiveRules() throws {
        let level = try decoder.decode(LevelData.self, from: Data(Self.versionThreeJSON.utf8))
        let legacyLevel = try decoder.decode(LevelData.self, from: Data(Self.versionTwoJSON.utf8))

        let always = level.effectiveAvailabilityRule(for: RouteEdge(
            id: "always", fromNodeID: "a", toNodeID: "b"
        ))
        let before = level.effectiveAvailabilityRule(for: RouteEdge(
            id: "before", fromNodeID: "a", toNodeID: "b", availability: .beforePackage
        ))
        let after = level.effectiveAvailabilityRule(for: RouteEdge(
            id: "after", fromNodeID: "a", toNodeID: "b", availability: .afterPackage
        ))

        XCTAssertEqual(always, EdgeAvailabilityRule())
        XCTAssertEqual(before.forbiddenCompletedObjectiveIDs, ["collect"])
        XCTAssertEqual(before.requiredCompletedObjectiveIDs, [])
        XCTAssertEqual(after.requiredCompletedObjectiveIDs, ["collect"])
        XCTAssertEqual(after.forbiddenCompletedObjectiveIDs, [])
        XCTAssertEqual(
            legacyLevel.effectiveAvailabilityRule(for: RouteEdge(
                id: "legacy_after",
                fromNodeID: "a",
                toNodeID: "b",
                availability: .afterPackage
            )).requiredCompletedObjectiveIDs,
            [RouteObjective.legacyPickupID]
        )
    }

    func testStructuredRuleTakesPrecedenceOverLegacyAvailability() throws {
        let level = try decoder.decode(LevelData.self, from: Data(Self.versionThreeJSON.utf8))
        let authored = EdgeAvailabilityRule(requiredCompletedObjectiveIDs: ["scan"])
        let edge = RouteEdge(
            id: "authored",
            fromNodeID: "a",
            toNodeID: "b",
            availability: .beforePackage,
            availabilityRule: authored
        )

        XCTAssertEqual(level.effectiveAvailabilityRule(for: edge), authored)
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

    private static let versionThreeJSON = """
    {
      "schemaVersion": 3,
      "rules": {
        "switchInteractionMode": "liveLookahead",
        "switchLookaheadSeconds": 1.75,
        "switchTapCooldownSeconds": 0.2
      },
      "id": "ordered", "name": "Ordered Objectives",
      "graph": {
        "nodes": [
          {"id": "start", "x": 0, "y": 0, "outgoingEdgeIDs": []},
          {"id": "pickup", "x": 1, "y": 0, "outgoingEdgeIDs": []},
          {"id": "checkpoint", "x": 2, "y": 0, "outgoingEdgeIDs": []},
          {"id": "delivery", "x": 3, "y": 0, "outgoingEdgeIDs": []},
          {"id": "destination", "x": 4, "y": 0, "outgoingEdgeIDs": []}
        ],
        "edges": []
      },
      "startNodeID": "start", "packageNodeID": "pickup",
      "destinationNodeID": "destination", "timeLimitSeconds": 30, "parTaps": 0,
      "objectives": [
        {
          "id": "collect", "nodeID": "pickup", "kind": "pickup",
          "sequenceIndex": 0, "revealPolicy": "always",
          "displayMetadata": {
            "title": "Collect the parcel",
            "marker": {"priority": 1, "visible": true}
          },
          "futureBehavior": {"pulse": true}
        },
        {
          "id": "scan", "nodeID": "checkpoint", "kind": "checkpoint",
          "sequenceIndex": 1, "revealPolicy": "whenActive"
        },
        {
          "id": "dropoff", "nodeID": "delivery", "kind": "delivery",
          "sequenceIndex": 2, "revealPolicy": "whenActive"
        },
        {
          "id": "finish", "nodeID": "destination", "kind": "destination",
          "sequenceIndex": 3, "revealPolicy": "whenActive", "displayMetadata": null
        }
      ]
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
