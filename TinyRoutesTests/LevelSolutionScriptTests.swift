import XCTest
@testable import TinyRoutes

final class LevelSolutionScriptTests: XCTestCase {
    private let decoder = JSONDecoder()

    func testSampleScriptDecodes() throws {
        let json = """
        {
          "levelID": "level_001",
          "description": "Known-good completion path for level_001.",
          "expectedOutcome": "completed",
          "maxTaps": 1,
          "requiresWithinTimeLimit": true,
          "actions": [
            {
              "timeSeconds": 0.25,
              "tapNodeID": "switch_a"
            }
          ]
        }
        """

        let data = Data(json.utf8)
        let script = try decoder.decode(LevelSolutionScript.self, from: data)

        XCTAssertEqual(script.levelID, "level_001")
        XCTAssertEqual(script.description, "Known-good completion path for level_001.")
        XCTAssertEqual(script.expectedOutcome, .completed)
        XCTAssertEqual(script.maxTaps, 1)
        XCTAssertTrue(script.requiresWithinTimeLimit)
        XCTAssertEqual(script.actions.count, 1)
        XCTAssertEqual(script.actions[0].timeSeconds, 0.25)
        XCTAssertEqual(script.actions[0].tapNodeID, "switch_a")
    }

    func testLevel001ScriptDecodesFromRepository() throws {
        let repository = LevelSolutionRepository()
        let script = try repository.loadScript(levelID: "level_001")

        XCTAssertEqual(script.levelID, "level_001")
        XCTAssertEqual(script.expectedOutcome, .completed)
        XCTAssertFalse((script.description ?? "").isEmpty)
        XCTAssertLessThanOrEqual(script.actions.count, script.maxTaps)
        XCTAssertTrue(script.actions.allSatisfy { !$0.tapNodeID.isEmpty })
        XCTAssertTrue(script.actions.allSatisfy { $0.timeSeconds >= 0 })
    }

    func testEveryProductionLevelHasMatchingSolutionScript() throws {
        let productionLevelIDs = try TestLevelCatalog().loadAllProductionLevels().map(\.id).sorted()
        XCTAssertFalse(productionLevelIDs.isEmpty, "Expected at least one production level")
        let repository = LevelSolutionRepository()
        var failures: [String] = []

        for levelID in productionLevelIDs {
            do {
                let script = try repository.loadScript(levelID: levelID)
                if script.levelID != levelID {
                    failures.append("\(levelID): script payload levelID is '\(script.levelID)'")
                }
            } catch {
                failures.append("\(levelID): \(error.localizedDescription)")
            }
        }

        XCTAssertTrue(
            failures.isEmpty,
            "Every production level must have a matching solution script:\n\(failures.joined(separator: "\n"))"
        )
    }

    func testBundledProductionLevelsHaveCorrespondingDecodedScripts() throws {
        let levelsByID = try productionLevelsByID()
        let scripts = try LevelSolutionRepository().loadAllScripts()

        XCTAssertFalse(scripts.isEmpty, "Expected at least one solution script in LevelSolutions/")

        let scriptIDs = Set(scripts.map(\.levelID))
        let missingScripts = levelsByID.keys
            .filter { !scriptIDs.contains($0) }
            .sorted()

        XCTAssertTrue(
            missingScripts.isEmpty,
            "Every bundled production level must have a decoded solution script:\n\(missingScripts.joined(separator: "\n"))"
        )
    }

    func testMissingSolutionScriptFailsClearly() {
        let repository = LevelSolutionRepository()

        XCTAssertThrowsError(try repository.loadScript(levelID: "level_999")) { error in
            guard case let LevelSolutionRepositoryError.fileNotFound(levelID) = error else {
                XCTFail("Expected fileNotFound error, got \(error)")
                return
            }
            XCTAssertEqual(levelID, "level_999")
            XCTAssertTrue(
                error.localizedDescription.contains("level_999.solution.json"),
                "Expected missing script error to include expected filename"
            )
        }
    }

    func testSolutionActionTimesAreNonNegative() throws {
        let scripts = try LevelSolutionRepository().loadAllScripts()

        let invalidActions = scripts.flatMap { script in
            script.actions.enumerated().compactMap { index, action in
                action.timeSeconds < 0 ? "\(script.levelID) action[\(index)] has negative time \(action.timeSeconds)" : nil
            }
        }

        XCTAssertTrue(
            invalidActions.isEmpty,
            "Solution action times must be non-negative:\n\(invalidActions.joined(separator: "\n"))"
        )
    }

    func testSolutionActionTimesAreFinite() throws {
        let scripts = try LevelSolutionRepository().loadAllScripts()

        let invalidActions = scripts.flatMap { script in
            script.actions.enumerated().compactMap { index, action in
                action.timeSeconds.isFinite
                    ? nil
                    : "\(script.levelID) action[\(index)] has non-finite time \(action.timeSeconds)"
            }
        }

        XCTAssertTrue(
            invalidActions.isEmpty,
            "Solution action times must be finite:\n\(invalidActions.joined(separator: "\n"))"
        )
    }

    func testSolutionTapNodeIDsAreNonEmpty() throws {
        let scripts = try LevelSolutionRepository().loadAllScripts()

        let invalidActions = scripts.flatMap { script in
            script.actions.enumerated().compactMap { index, action in
                action.tapNodeID.isEmpty
                    ? "\(script.levelID) action[\(index)] has an empty tapNodeID"
                    : nil
            }
        }

        XCTAssertTrue(
            invalidActions.isEmpty,
            "Solution tap node IDs must be non-empty:\n\(invalidActions.joined(separator: "\n"))"
        )
    }

    func testSolutionActionsAreSortedByTime() throws {
        let scripts = try LevelSolutionRepository().loadAllScripts()

        let orderingIssues = scripts.flatMap { script in
            zip(script.actions, script.actions.dropFirst()).enumerated().compactMap { index, pair in
                let (previous, current) = pair
                return previous.timeSeconds > current.timeSeconds
                    ? "\(script.levelID) action[\(index)] time \(previous.timeSeconds) is after action[\(index + 1)] time \(current.timeSeconds)"
                    : nil
            }
        }

        XCTAssertTrue(
            orderingIssues.isEmpty,
            "Solution actions must be sorted by timeSeconds:\n\(orderingIssues.joined(separator: "\n"))"
        )
    }

    func testSolutionMaxTapsIsNonNegative() throws {
        let scripts = try LevelSolutionRepository().loadAllScripts()

        let invalidMaxTaps = scripts
            .filter { $0.maxTaps < 0 }
            .map { "\($0.levelID) has maxTaps \($0.maxTaps)" }

        XCTAssertTrue(
            invalidMaxTaps.isEmpty,
            "Solution maxTaps must be non-negative:\n\(invalidMaxTaps.joined(separator: "\n"))"
        )
    }

    func testEveryTappedNodeExistsInReferencedLevel() throws {
        let levelsByID = try productionLevelsByID()
        let scripts = try LevelSolutionRepository().loadAllScripts()

        let invalidTapNodes = scripts.flatMap { script -> [String] in
            guard let level = levelsByID[script.levelID] else {
                return []
            }

            let nodeIDs = Set(level.graph.nodes.map(\.id))
            return script.actions.enumerated().compactMap { index, action in
                nodeIDs.contains(action.tapNodeID)
                    ? nil
                    : "\(script.levelID) action[\(index)] references missing node '\(action.tapNodeID)'"
            }
        }

        XCTAssertTrue(
            invalidTapNodes.isEmpty,
            "Tapped nodes must exist in the referenced level:\n\(invalidTapNodes.joined(separator: "\n"))"
        )
    }

    func testEveryTappedNodeHasMoreThanOneOutgoingEdge() throws {
        let levelsByID = try productionLevelsByID()
        let scripts = try LevelSolutionRepository().loadAllScripts()

        let invalidTapTargets = scripts.flatMap { script -> [String] in
            guard let level = levelsByID[script.levelID] else {
                return []
            }

            let nodesByID = Dictionary(uniqueKeysWithValues: level.graph.nodes.map { ($0.id, $0) })
            return script.actions.enumerated().compactMap { index, action in
                guard let node = nodesByID[action.tapNodeID] else {
                    return "\(script.levelID) action[\(index)] references missing node '\(action.tapNodeID)'"
                }
                return node.outgoingEdgeIDs.count > 1
                    ? nil
                    : "\(script.levelID) action[\(index)] taps '\(action.tapNodeID)' with only \(node.outgoingEdgeIDs.count) outgoing edge(s)"
            }
        }

        XCTAssertTrue(
            invalidTapTargets.isEmpty,
            "Tapped nodes must have more than one outgoing edge:\n\(invalidTapTargets.joined(separator: "\n"))"
        )
    }

    private func productionLevelsByID() throws -> [String: LevelData] {
        let levels = try TestLevelCatalog().loadAllProductionLevels()
        XCTAssertFalse(levels.isEmpty, "Expected at least one production level")
        return Dictionary(uniqueKeysWithValues: levels.map { ($0.id, $0) })
    }
}
