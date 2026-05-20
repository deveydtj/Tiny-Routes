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
          "startNodeID": "start",
          "packageNodeID": "package",
          "destinationNodeID": "destination",
          "timeLimitSeconds": 45,
          "parTaps": 6
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
        XCTAssertEqual(level.startNodeID, "start")
        XCTAssertEqual(level.packageNodeID, "package")
        XCTAssertEqual(level.destinationNodeID, "destination")
        XCTAssertEqual(level.timeLimitSeconds, 45)
        XCTAssertEqual(level.parTaps, 6)
    }

    func testSampleLevelContainsRequiredNodesAndValidReferences() throws {
        let data = try sampleLevel001Data()
        let level = try decoder.decode(LevelData.self, from: data)

        let duplicateNodeIDs = Dictionary(grouping: level.graph.nodes.map(\.id), by: { $0 })
            .filter { $1.count > 1 }
            .map(\.key)
            .sorted()
        XCTAssertTrue(duplicateNodeIDs.isEmpty, "Duplicate node IDs found: \(duplicateNodeIDs)")
        guard duplicateNodeIDs.isEmpty else {
            return
        }

        let nodesByID = Dictionary(uniqueKeysWithValues: level.graph.nodes.map { ($0.id, $0) })
        let nodeIDs = Set(nodesByID.keys)
        XCTAssertTrue(nodeIDs.contains("start"))
        XCTAssertTrue(nodeIDs.contains("package"))
        XCTAssertTrue(nodeIDs.contains("destination"))
        XCTAssertTrue(nodeIDs.contains(level.startNodeID))

        XCTAssertNotNil(nodesByID[level.startNodeID])
        XCTAssertNotNil(nodesByID[level.packageNodeID])
        XCTAssertNotNil(nodesByID[level.destinationNodeID])

        for node in level.graph.nodes {
            try node.validateOutgoingEdges(against: level.graph.edges)
        }
        for edge in level.graph.edges {
            XCTAssertTrue(nodeIDs.contains(edge.fromNodeID), "Missing fromNodeID \(edge.fromNodeID) for edge \(edge.id)")
            XCTAssertTrue(nodeIDs.contains(edge.toNodeID), "Missing toNodeID \(edge.toNodeID) for edge \(edge.id)")
        }

        let startNode = try XCTUnwrap(nodesByID["start"])
        XCTAssertEqual(startNode.outgoingEdgeIDs, ["e_start_package"], "Level 1 should first route to the package")

        let packageNode = try XCTUnwrap(nodesByID["package"])
        XCTAssertEqual(packageNode.outgoingEdgeIDs, ["e_package_destination"], "Level 1 should route from the package to the destination")

        let adjacency = Dictionary(grouping: level.graph.edges, by: \.fromNodeID)
            .mapValues { edges in edges.map(\.toNodeID) }

        let canReachPackage = isReachable(from: "start", to: level.packageNodeID, adjacency: adjacency)
        XCTAssertTrue(canReachPackage, "Expected a path from start to package")

        let canReachDestination = isReachable(from: level.packageNodeID, to: level.destinationNodeID, adjacency: adjacency)
        XCTAssertTrue(canReachDestination, "Expected a path from package to destination")
    }

    func testLevelTwoUsesCurvedChoiceRoads() throws {
        let data = try levelData(forResource: "level_002")
        let level = try decoder.decode(LevelData.self, from: data)
        let nodesByID = Dictionary(uniqueKeysWithValues: level.graph.nodes.map { ($0.id, $0) })
        let edgesByID = Dictionary(uniqueKeysWithValues: level.graph.edges.map { ($0.id, $0) })

        let choice = try XCTUnwrap(nodesByID["choice"])
        let package = try XCTUnwrap(nodesByID["package"])
        let bypass = try XCTUnwrap(nodesByID["bypass"])
        let destination = try XCTUnwrap(nodesByID["destination"])
        let packageEdge = try XCTUnwrap(edgesByID["e_choice_package"])
        let bypassEdge = try XCTUnwrap(edgesByID["e_choice_bypass"])

        XCTAssertEqual(choice.outgoingEdgeIDs, ["e_choice_bypass", "e_choice_package"])
        XCTAssertEqual(packageEdge.roadShape, .horizontalFirst)
        XCTAssertEqual(bypassEdge.roadShape, .horizontalFirst)
        XCTAssertGreaterThan(package.x, choice.x)
        XCTAssertGreaterThan(bypass.x, choice.x)
        XCTAssertGreaterThan(package.y, choice.y)
        XCTAssertLessThan(bypass.y, choice.y)
        XCTAssertEqual(package.x, destination.x, accuracy: 0.0001)
        XCTAssertGreaterThan(destination.y, package.y)
        XCTAssertEqual(level.parTaps, 1)

        let packageRoadPath = RoadPath.make(
            from: RoadPoint(x: choice.x, y: choice.y),
            to: RoadPoint(x: package.x, y: package.y),
            shape: packageEdge.roadShape
        )
        let bypassRoadPath = RoadPath.make(
            from: RoadPoint(x: choice.x, y: choice.y),
            to: RoadPoint(x: bypass.x, y: bypass.y),
            shape: bypassEdge.roadShape
        )

        XCTAssertTrue(packageRoadPath.segments.contains { $0.kind == .quarterTurn })
        XCTAssertTrue(bypassRoadPath.segments.contains { $0.kind == .quarterTurn })
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
          "startNodeID": "a",
          "packageNodeID": "a",
          "destinationNodeID": "b",
          "timeLimitSeconds": 60,
          "parTaps": 3
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
          "startNodeID": "",
          "packageNodeID": "",
          "destinationNodeID": "",
          "timeLimitSeconds": 10,
          "parTaps": 1
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
          "startNodeID": "n0",
          "packageNodeID": "n1",
          "destinationNodeID": "n2",
          "timeLimitSeconds": 30,
          "parTaps": 5
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
          "startNodeID": "n0",
          "packageNodeID": "n1",
          "destinationNodeID": "n2",
          "timeLimitSeconds": 30,
          "parTaps": 5
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
          "startNodeID": "n0",
          "packageNodeID": "n1",
          "destinationNodeID": "n2",
          "timeLimitSeconds": 30,
          "parTaps": 5
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
          "startNodeID": "n0",
          "packageNodeID": "n1",
          "destinationNodeID": "n2",
          "timeLimitSeconds": 30,
          "parTaps": 5
        }
        """
        let data = try XCTUnwrap(json.data(using: .utf8))
        XCTAssertThrowsError(try decoder.decode(LevelData.self, from: data))
    }

    func testMissingParTapsFieldThrowsDecodingError() throws {
        let json = """
        {
          "id": "level_001",
          "name": "Missing Par Taps",
          "graph": { "nodes": [], "edges": [] },
          "startNodeID": "n0",
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
        let repo = LevelRepository(bundle: try sampleLevel001Bundle())
        let level = try repo.loadLevel(id: "level_001")

        XCTAssertEqual(level.id, "level_001")
        XCTAssertEqual(level.name, "First Pickup")
        XCTAssertEqual(level.graph.nodes.count, 3)
        XCTAssertEqual(level.graph.edges.count, 2)
        XCTAssertEqual(level.startNodeID, "start")
        XCTAssertEqual(level.packageNodeID, "package")
        XCTAssertEqual(level.destinationNodeID, "destination")
        XCTAssertEqual(level.timeLimitSeconds, 30)
        XCTAssertEqual(level.parTaps, 0)
    }

    func testLoadLevelViaRepositorySucceedsWhenLevelFileIsAtBundleRoot() throws {
        let data = try XCTUnwrap(validLevelJSON.data(using: .utf8))
        let repo = LevelRepository(
            urlResolver: { _ in URL(string: "fake://level_001.json") },
            dataLoader: { _ in data }
        )

        let level = try repo.loadLevel(id: "level_001")
        XCTAssertEqual(level.id, "level_001")
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
          "startNodeID": "n0",
          "packageNodeID": "n1",
          "destinationNodeID": "n2",
          "timeLimitSeconds": 30,
          "parTaps": 5
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

    func testLoadLevelThrowsDecodingFailedForMissingParTapsField() throws {
        let missingParTapsJSON = """
        {
          "id": "level_001",
          "name": "Missing Par Taps",
          "graph": { "nodes": [], "edges": [] },
          "startNodeID": "n0",
          "packageNodeID": "n1",
          "destinationNodeID": "n2",
          "timeLimitSeconds": 30
        }
        """
        let data = try XCTUnwrap(missingParTapsJSON.data(using: .utf8))
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

    func testLoadAllLevelsDecodesShippedBundleLevels() throws {
        let repo = LevelRepository(bundle: try bundledLevelsBundle())

        let levels = try repo.loadAllLevels().sorted { $0.id < $1.id }

        XCTAssertEqual(levels.map(\.id), expectedBundledLevelIDs)
    }

    func testBundledLevelsHaveUniqueIDsAndValidReferences() throws {
        let resources = try bundledLevelResources()
        let levels = try resources.map { resource in
            try decoder.decode(LevelData.self, from: Data(contentsOf: resource.url))
        }

        let duplicateLevelIDs = Dictionary(grouping: levels.map(\.id), by: { $0 })
            .filter { $1.count > 1 }
            .map(\.key)
            .sorted()
        XCTAssertTrue(duplicateLevelIDs.isEmpty, "Duplicate level IDs found: \(duplicateLevelIDs)")

        for (resource, level) in zip(resources, levels) {
            XCTAssertEqual(resource.url.deletingPathExtension().lastPathComponent, level.id)
            assertLevelGraphIntegrity(level)
        }
    }

    func testBundledLevelsAreCompletableWithinTimeLimit() throws {
        let resources = try bundledLevelResources()
        let levels = try resources.map { resource in
            try decoder.decode(LevelData.self, from: Data(contentsOf: resource.url))
        }

        for level in levels {
            let validator = LevelSolvabilityValidator(level: level)
            let solution = validator.shortestCompletion()
            XCTAssertNotNil(solution, "Expected \(level.id) to be completable before its \(level.timeLimitSeconds)s time limit")
        }
    }

    func testBundledLevelParTapsAreAchievable() throws {
        let resources = try bundledLevelResources()
        let levels = try resources.map { resource in
            try decoder.decode(LevelData.self, from: Data(contentsOf: resource.url))
        }

        for level in levels {
            let validator = LevelSolvabilityValidator(level: level)
            let solution = validator.lowestTapCompletion()
            XCTAssertNotNil(solution, "Expected \(level.id) to be completable")
            XCTAssertLessThanOrEqual(
                solution?.tapCount ?? Int.max,
                level.parTaps,
                "Expected \(level.id) parTaps \(level.parTaps) to be achievable, but best solution was \(solution?.tapCount.description ?? "none") taps"
            )
        }
    }

    func testBundledLevelsHaveReplayableRouteEngineSolutions() throws {
        let resources = try bundledLevelResources()

        for resource in resources {
            let data = try Data(contentsOf: resource.url)
            let level = try decoder.decode(LevelData.self, from: data)
            let authoredSolution = try decoder.decode(AuthoredLevelSolutionEnvelope.self, from: data).solution
            let solver = LevelSolvabilityValidator(level: level, dotSpeed: solutionReplayDotSpeed)
            let solution = try XCTUnwrap(
                solver.lowestTapCompletion(),
                "Expected \(level.id) to have a solver-produced completion plan"
            )

            if let authoredTapNodeIDs = authoredSolution?.tapNodeIDs {
                XCTAssertEqual(
                    solution.tapNodeIDs,
                    authoredTapNodeIDs,
                    "Authored tap plan for \(level.id) should match the lowest-tap solver plan"
                )
            }

            try assertSolution(solution, completes: level)
            XCTAssertLessThanOrEqual(
                solution.tapCount,
                level.parTaps,
                "Expected replayable solution for \(level.id) to be at or under par"
            )
        }
    }

    func testSolvabilityValidatorRejectsGraphReachableLevelThatCannotCollectPackageBeforeDestination() {
        let nodes = [
            RouteNode(id: "start", x: 0, y: 0, outgoingEdgeIDs: ["e_start_destination"]),
            RouteNode(id: "package", x: 1, y: 1, outgoingEdgeIDs: ["e_package_destination"]),
            RouteNode(id: "destination", x: 1, y: 0, outgoingEdgeIDs: [])
        ]
        let edges = [
            RouteEdge(id: "e_start_destination", fromNodeID: "start", toNodeID: "destination"),
            RouteEdge(id: "e_package_destination", fromNodeID: "package", toNodeID: "destination")
        ]
        let level = LevelData(
            id: "destination_first",
            name: "Destination First",
            graph: RouteGraph(nodes: nodes, edges: edges),
            startNodeID: "start",
            packageNodeID: "package",
            destinationNodeID: "destination",
            timeLimitSeconds: 30,
            parTaps: 0
        )

        XCTAssertNil(LevelSolvabilityValidator(level: level).shortestCompletion())
    }

    func testSolvabilityValidatorRejectsPlayableRouteThatExceedsTimeLimit() {
        let nodes = [
            RouteNode(id: "start", x: 0, y: 0, outgoingEdgeIDs: ["e_start_package"]),
            RouteNode(id: "package", x: 2, y: 0, outgoingEdgeIDs: ["e_package_destination"]),
            RouteNode(id: "destination", x: 4, y: 0, outgoingEdgeIDs: [])
        ]
        let edges = [
            RouteEdge(id: "e_start_package", fromNodeID: "start", toNodeID: "package"),
            RouteEdge(id: "e_package_destination", fromNodeID: "package", toNodeID: "destination")
        ]
        let level = LevelData(
            id: "too_slow",
            name: "Too Slow",
            graph: RouteGraph(nodes: nodes, edges: edges),
            startNodeID: "start",
            packageNodeID: "package",
            destinationNodeID: "destination",
            timeLimitSeconds: 3,
            parTaps: 0
        )

        XCTAssertNil(LevelSolvabilityValidator(level: level).shortestCompletion())
    }

    func testBundledLevelsSortIntoExpectedNextLevelOrder() throws {
        let repo = LevelRepository(bundle: try bundledLevelsBundle())
        let sortedLevelIDs = try repo.loadAllLevels()
            .map(\.id)
            .sorted()

        XCTAssertEqual(sortedLevelIDs, expectedBundledLevelIDs)

        for (index, levelID) in sortedLevelIDs.enumerated() {
            let expectedNextLevelID = index < sortedLevelIDs.count - 1
                ? sortedLevelIDs[index + 1]
                : nil
            XCTAssertEqual(nextLevelID(after: levelID, in: sortedLevelIDs), expectedNextLevelID)
        }
    }

    private func assertLevelGraphIntegrity(_ level: LevelData) {
        let duplicateNodeIDs = Dictionary(grouping: level.graph.nodes.map(\.id), by: { $0 })
            .filter { $1.count > 1 }
            .map(\.key)
            .sorted()
        XCTAssertTrue(duplicateNodeIDs.isEmpty, "Duplicate node IDs found in \(level.id): \(duplicateNodeIDs)")
        guard duplicateNodeIDs.isEmpty else {
            return
        }

        let nodesByID = Dictionary(uniqueKeysWithValues: level.graph.nodes.map { ($0.id, $0) })
        let nodeIDs = Set(nodesByID.keys)

        XCTAssertNotNil(nodesByID[level.startNodeID], "Missing start node \(level.startNodeID) in \(level.id)")
        XCTAssertNotNil(nodesByID[level.packageNodeID], "Missing package node \(level.packageNodeID) in \(level.id)")
        XCTAssertNotNil(nodesByID[level.destinationNodeID], "Missing destination node \(level.destinationNodeID) in \(level.id)")

        for node in level.graph.nodes {
            XCTAssertNoThrow(try node.validateOutgoingEdges(against: level.graph.edges), "Invalid outgoing edges for node \(node.id) in \(level.id)")
        }

        for edge in level.graph.edges {
            XCTAssertTrue(nodeIDs.contains(edge.fromNodeID), "Missing fromNodeID \(edge.fromNodeID) for edge \(edge.id) in \(level.id)")
            XCTAssertTrue(nodeIDs.contains(edge.toNodeID), "Missing toNodeID \(edge.toNodeID) for edge \(edge.id) in \(level.id)")
        }

        let adjacency = Dictionary(grouping: level.graph.edges, by: \.fromNodeID)
            .mapValues { edges in edges.map(\.toNodeID) }
        XCTAssertTrue(
            isReachable(from: level.startNodeID, to: level.packageNodeID, adjacency: adjacency),
            "Expected a path from start to package in \(level.id)"
        )
        XCTAssertTrue(
            isReachable(from: level.packageNodeID, to: level.destinationNodeID, adjacency: adjacency),
            "Expected a path from package to destination in \(level.id)"
        )
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

    private var expectedBundledLevelIDs: [String] {
        (1...10).map { String(format: "level_%03d", $0) }
    }

    private func nextLevelID(after currentLevelID: String, in sortedLevelIDs: [String]) -> String? {
        guard let currentIndex = sortedLevelIDs.firstIndex(of: currentLevelID),
              currentIndex < sortedLevelIDs.count - 1 else {
            return nil
        }

        return sortedLevelIDs[currentIndex + 1]
    }

    private func sampleLevel001Bundle() throws -> Bundle {
        try sampleLevel001Resource().bundle
    }

    private func sampleLevel001Data() throws -> Data {
        try levelData(forResource: "level_001")
    }

    private func levelData(forResource resourceName: String) throws -> Data {
        try Data(contentsOf: levelResource(named: resourceName).url)
    }

    private func sampleLevel001Resource() throws -> (bundle: Bundle, url: URL) {
        try levelResource(named: "level_001")
    }

    private func levelResource(named resourceName: String) throws -> (bundle: Bundle, url: URL) {
        let bundles = [Bundle(for: LevelRepositoryTests.self), Bundle.main]
        for bundle in bundles {
            if let levelURL = bundle.url(forResource: resourceName, withExtension: "json", subdirectory: "Levels") {
                return (bundle, levelURL)
            }
            if let levelURL = bundle.url(forResource: resourceName, withExtension: "json") {
                return (bundle, levelURL)
            }
        }

        throw LevelRepositoryError.fileNotFound(id: resourceName)
    }

    private func bundledLevelsBundle() throws -> Bundle {
        try sampleLevel001Bundle()
    }

    private func bundledLevelResources() throws -> [(bundle: Bundle, url: URL)] {
        let bundle = try bundledLevelsBundle()
        let nestedURLs = bundle.urls(forResourcesWithExtension: "json", subdirectory: "Levels") ?? []
        let rootURLs = bundle.urls(forResourcesWithExtension: "json", subdirectory: nil) ?? []

        var seen = Set<URL>()
        let urls = (nestedURLs + rootURLs)
            .filter { seen.insert($0).inserted }
            .filter { $0.deletingPathExtension().lastPathComponent.hasPrefix("level_") }
            .sorted { $0.lastPathComponent < $1.lastPathComponent }

        return urls.map { (bundle: bundle, url: $0) }
    }

    private var solutionReplayDotSpeed: Double { 100 }

    private func assertSolution(
        _ solution: LevelSolvabilityValidator.Solution,
        completes level: LevelData,
        file: StaticString = #filePath,
        line: UInt = #line
    ) throws {
        let engine = RouteEngine(dotSpeed: solutionReplayDotSpeed)
        try engine.buildGraph(from: level)
        XCTAssertTrue(engine.startDotMovement(), "Expected \(level.id) to start movement", file: file, line: line)

        var actionIndex = 0
        while actionIndex < solution.actions.count {
            switch solution.actions[actionIndex] {
            case let .tap(nodeID):
                XCTAssertTrue(
                    engine.rotateSwitchNode(nodeID: nodeID),
                    "Expected \(level.id) tap on \(nodeID) to rotate a switch",
                    file: file,
                    line: line
                )
                actionIndex += 1
            case let .move(edgeID):
                let edge = try XCTUnwrap(
                    engine.runtimeGraph?.edgesByID[edgeID],
                    "Expected \(level.id) to contain solver edge \(edgeID)",
                    file: file,
                    line: line
                )

                while actionIndex + 1 < solution.actions.count,
                      case let .tap(nodeID) = solution.actions[actionIndex + 1],
                      nodeID == edge.toNodeID {
                    XCTAssertTrue(
                        engine.rotateSwitchNode(nodeID: nodeID),
                        "Expected \(level.id) pre-arrival tap on \(nodeID) to rotate a switch",
                        file: file,
                        line: line
                    )
                    actionIndex += 1
                }

                XCTAssertTrue(
                    isReplayCommitted(to: edgeID, in: engine.deliveryDot),
                    "Expected \(level.id) replay to be traversing or smoothly entering \(edgeID)",
                    file: file,
                    line: line
                )
                let replayDistance = remainingReplayDistance(for: edgeID, edge: edge, in: engine.deliveryDot)
                engine.updateDot(deltaTime: (replayDistance / solutionReplayDotSpeed) + 0.000001)
                actionIndex += 1
            }
        }

        XCTAssertEqual(engine.levelOutcome, .completed, "Expected \(level.id) authored replay to complete", file: file, line: line)
        XCTAssertEqual(engine.tapCount, solution.tapCount, "Expected \(level.id) replay tap count to match solver", file: file, line: line)
    }

    private func isReplayCommitted(to edgeID: String, in dot: DeliveryDot?) -> Bool {
        dot?.currentEdgeID == edgeID || dot?.transition?.toEdgeID == edgeID
    }

    private func remainingReplayDistance(for edgeID: String, edge: RuntimeRouteEdge, in dot: DeliveryDot?) -> Double {
        let edgeLength = edge.roadPath.totalLength

        if dot?.currentEdgeID == edgeID {
            let progress = max(0, min(dot?.progressAlongEdge ?? 0, 1))
            return (1 - progress) * edgeLength
        }

        if let transition = dot?.transition, transition.toEdgeID == edgeID {
            let transitionLength = transition.roadPath.totalLength
            let transitionProgress = max(0, min(transition.progressAlongTransition, 1))
            let transitionRemaining = (1 - transitionProgress) * transitionLength
            let edgeRemaining = max(edgeLength - transition.exitDistanceAlongToEdge, 0)
            return transitionRemaining + edgeRemaining
        }

        return edgeLength
    }
}

private struct AuthoredLevelSolutionEnvelope: Decodable {
    struct Solution: Decodable {
        let tapNodeIDs: [String]
    }

    let solution: Solution?
}

private struct LevelSolvabilityValidator {
    enum Action: Equatable {
        case tap(nodeID: String)
        case move(edgeID: String)
    }

    private struct State: Hashable {
        var nodeID: String
        var hasPackage: Bool
        var switchEdgeIndices: [Int]
    }

    struct Solution {
        var elapsedTime: TimeInterval
        var tapCount: Int
        var tapNodeIDs: [String]
        var actions: [Action]
    }

    private struct SearchEntry {
        var state: State
        var elapsedTime: TimeInterval
        var tapCount: Int
        var tapNodeIDs: [String]
        var actions: [Action]
    }

    private struct BestCost: Comparable {
        var elapsedTime: TimeInterval
        var tapCount: Int

        static func < (lhs: BestCost, rhs: BestCost) -> Bool {
            if lhs.elapsedTime != rhs.elapsedTime {
                return lhs.elapsedTime < rhs.elapsedTime
            }

            return lhs.tapCount < rhs.tapCount
        }
    }

    private let level: LevelData
    private let nodesByID: [String: RouteNode]
    private let edgesByID: [String: RouteEdge]
    private let switchNodeIDs: [String]
    private let timeLimit: TimeInterval
    private let dotSpeed: Double

    init(level: LevelData, dotSpeed: Double = 1) {
        self.level = level
        self.nodesByID = Dictionary(uniqueKeysWithValues: level.graph.nodes.map { ($0.id, $0) })
        self.edgesByID = Dictionary(uniqueKeysWithValues: level.graph.edges.map { ($0.id, $0) })
        self.switchNodeIDs = level.graph.nodes
            .filter { $0.outgoingEdgeIDs.count > 1 }
            .map(\.id)
            .sorted()
        self.timeLimit = max(TimeInterval(level.timeLimitSeconds), 0)
        self.dotSpeed = max(dotSpeed, 0)
    }

    func shortestCompletion() -> Solution? {
        completion(preferLowestTapCount: false)
    }

    func lowestTapCompletion() -> Solution? {
        completion(preferLowestTapCount: true)
    }

    private func completion(preferLowestTapCount: Bool) -> Solution? {
        guard dotSpeed > 0,
              nodesByID[level.startNodeID] != nil,
              nodesByID[level.packageNodeID] != nil,
              nodesByID[level.destinationNodeID] != nil else {
            return nil
        }

        let initialState = State(
            nodeID: level.startNodeID,
            hasPackage: level.startNodeID == level.packageNodeID,
            switchEdgeIndices: Array(repeating: 0, count: switchNodeIDs.count)
        )
        var bestCostByState: [State: BestCost] = [
            initialState: BestCost(elapsedTime: 0, tapCount: 0)
        ]
        var queue: [SearchEntry] = [
            SearchEntry(
                state: initialState,
                elapsedTime: 0,
                tapCount: 0,
                tapNodeIDs: [],
                actions: []
            )
        ]
        var bestSolution: Solution?

        while !queue.isEmpty {
            let bestQueueIndex = bestEntryIndex(in: queue, preferLowestTapCount: preferLowestTapCount)
            let entry = queue.remove(at: bestQueueIndex)

            if let knownCost = bestCostByState[entry.state],
               BestCost(elapsedTime: entry.elapsedTime, tapCount: entry.tapCount) > knownCost {
                continue
            }

            if entry.state.nodeID == level.destinationNodeID {
                if entry.state.hasPackage {
                    let solution = Solution(
                        elapsedTime: entry.elapsedTime,
                        tapCount: entry.tapCount,
                        tapNodeIDs: entry.tapNodeIDs,
                        actions: entry.actions
                    )
                    if isBetter(solution, than: bestSolution, preferLowestTapCount: preferLowestTapCount) {
                        bestSolution = solution
                    }
                }
                continue
            }

            for nextEntry in nextEntries(from: entry) {
                guard nextEntry.elapsedTime <= timeLimit else {
                    continue
                }

                let nextCost = BestCost(elapsedTime: nextEntry.elapsedTime, tapCount: nextEntry.tapCount)
                if let currentBestCost = bestCostByState[nextEntry.state],
                   currentBestCost <= nextCost {
                    continue
                }

                bestCostByState[nextEntry.state] = nextCost
                queue.append(nextEntry)
            }
        }

        return bestSolution
    }

    private func nextEntries(from entry: SearchEntry) -> [SearchEntry] {
        var entries: [SearchEntry] = rotationEntries(from: entry)

        if let movementEntry = movementEntry(from: entry) {
            entries.append(movementEntry)
        }

        return entries
    }

    private func rotationEntries(from entry: SearchEntry) -> [SearchEntry] {
        switchNodeIDs.enumerated().compactMap { index, nodeID in
            guard let node = nodesByID[nodeID], node.outgoingEdgeIDs.count > 1 else {
                return nil
            }

            var nextState = entry.state
            nextState.switchEdgeIndices[index] = (nextState.switchEdgeIndices[index] + 1) % node.outgoingEdgeIDs.count
            return SearchEntry(
                state: nextState,
                elapsedTime: entry.elapsedTime,
                tapCount: entry.tapCount + 1,
                tapNodeIDs: entry.tapNodeIDs + [nodeID],
                actions: entry.actions + [.tap(nodeID: nodeID)]
            )
        }
    }

    private func movementEntry(from entry: SearchEntry) -> SearchEntry? {
        guard let node = nodesByID[entry.state.nodeID],
              let activeEdgeID = activeEdgeID(for: node, in: entry.state),
              let edge = edgesByID[activeEdgeID],
              edge.fromNodeID == entry.state.nodeID,
              nodesByID[edge.toNodeID] != nil else {
            return nil
        }

        let nextState = State(
            nodeID: edge.toNodeID,
            hasPackage: entry.state.hasPackage || edge.toNodeID == level.packageNodeID,
            switchEdgeIndices: entry.state.switchEdgeIndices
        )
        let travelTime = roadLength(for: edge) / dotSpeed

        return SearchEntry(
            state: nextState,
            elapsedTime: entry.elapsedTime + travelTime,
            tapCount: entry.tapCount,
            tapNodeIDs: entry.tapNodeIDs,
            actions: entry.actions + [.move(edgeID: edge.id)]
        )
    }

    private func activeEdgeID(for node: RouteNode, in state: State) -> String? {
        guard !node.outgoingEdgeIDs.isEmpty else {
            return nil
        }

        guard let switchIndex = switchNodeIDs.firstIndex(of: node.id) else {
            return node.outgoingEdgeIDs.first
        }

        return node.outgoingEdgeIDs[state.switchEdgeIndices[switchIndex]]
    }

    private func roadLength(for edge: RouteEdge) -> Double {
        guard let fromNode = nodesByID[edge.fromNodeID],
              let toNode = nodesByID[edge.toNodeID] else {
            return .infinity
        }

        return RoadPath.make(
            from: RoadPoint(x: fromNode.x, y: fromNode.y),
            to: RoadPoint(x: toNode.x, y: toNode.y),
            shape: edge.roadShape
        )
        .totalLength
    }

    private func bestEntryIndex(in queue: [SearchEntry], preferLowestTapCount: Bool) -> Int {
        queue.indices.min { lhsIndex, rhsIndex in
            let lhs = queue[lhsIndex]
            let rhs = queue[rhsIndex]

            if preferLowestTapCount, lhs.tapCount != rhs.tapCount {
                return lhs.tapCount < rhs.tapCount
            }
            if lhs.elapsedTime != rhs.elapsedTime {
                return lhs.elapsedTime < rhs.elapsedTime
            }

            return lhs.tapCount < rhs.tapCount
        } ?? queue.startIndex
    }

    private func isBetter(_ solution: Solution, than currentBest: Solution?, preferLowestTapCount: Bool) -> Bool {
        guard let currentBest else {
            return true
        }

        if preferLowestTapCount, solution.tapCount != currentBest.tapCount {
            return solution.tapCount < currentBest.tapCount
        }
        if solution.elapsedTime != currentBest.elapsedTime {
            return solution.elapsedTime < currentBest.elapsedTime
        }

        return solution.tapCount < currentBest.tapCount
    }
}
