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
