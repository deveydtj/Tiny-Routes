import Foundation
@testable import TinyRoutes
import XCTest

final class RuntimeParityFixtureTests: XCTestCase {
    func testSharedRuntimeParityFixturesAreDiscoverableAndValidJSON() throws {
        let testFile = URL(fileURLWithPath: #filePath)
        let root = testFile.deletingLastPathComponent().deletingLastPathComponent()
            .appendingPathComponent("SharedFixtures/RuntimeParity")
        let manifestData = try Data(contentsOf: root.appendingPathComponent("manifest.json"))
        let manifest = try XCTUnwrap(JSONSerialization.jsonObject(with: manifestData) as? [String: Any])
        let fixtures = try XCTUnwrap(manifest["fixtures"] as? [[String: Any]])
        XCTAssertEqual(fixtures.count, 15)
        for fixture in fixtures {
            for key in ["level", "events", "expected"] {
                let relativePath = try XCTUnwrap(fixture[key] as? String)
                let data = try Data(contentsOf: root.appendingPathComponent(relativePath))
                XCTAssertTrue(JSONSerialization.isValidJSONObject(try JSONSerialization.jsonObject(with: data)))
            }
        }
    }

    func testPackageGateFixturesMatchSharedExpectedState() throws {
        for fixtureID in ["package_gate_normalization", "package_gate_revisit_rotation"] {
            let fixture = try loadFixture(id: fixtureID)
            let engine = RouteEngine(dotSpeed: 0.6)
            try engine.buildGraph(from: fixture.level)
            _ = engine.startDotMovement()

            var elapsed = 0.0
            for action in fixture.actions.sorted(by: { $0.timeSeconds < $1.timeSeconds }) {
                engine.updateDot(deltaTime: action.timeSeconds - elapsed)
                elapsed = action.timeSeconds
                XCTAssertTrue(
                    engine.rotateSwitchNode(nodeID: action.tapNodeID).didRotate,
                    "Expected shared fixture \(fixtureID) tap on \(action.tapNodeID) to be accepted."
                )
            }
            while engine.levelOutcome == nil, elapsed < TimeInterval(fixture.level.timeLimitSeconds) {
                let step = min(1.0 / 120.0, TimeInterval(fixture.level.timeLimitSeconds) - elapsed)
                engine.updateDot(deltaTime: step)
                elapsed += step
            }

            XCTAssertEqual(engine.levelOutcome, .completed)
            XCTAssertEqual(engine.tapCount, fixture.expectedAcceptedTapCount)
            XCTAssertEqual(engine.deliveryDot?.hasCollectedPackage, true)
            let active = engine.runtimeGraph?.nodesByID.compactMapValues { node in
                node.activeOutgoingEdgeID
            }
            XCTAssertEqual(active, fixture.expectedFinalActiveEdgeIDs)
        }
    }

    private func loadFixture(id: String) throws -> PackageGateFixture {
        let testFile = URL(fileURLWithPath: #filePath)
        let directory = testFile.deletingLastPathComponent().deletingLastPathComponent()
            .appendingPathComponent("SharedFixtures/RuntimeParity/\(id)")
        let decoder = JSONDecoder()
        let level = try decoder.decode(LevelData.self, from: Data(contentsOf: directory.appendingPathComponent("level.json")))
        let eventsData = try Data(contentsOf: directory.appendingPathComponent("events.json"))
        let events = try XCTUnwrap(JSONSerialization.jsonObject(with: eventsData) as? [String: Any])
        let actions = (events["actions"] as? [[String: Any]] ?? []).compactMap { action -> FixtureAction? in
            guard let time = action["timeSeconds"] as? Double,
                  let nodeID = action["tapNodeID"] as? String else { return nil }
            return FixtureAction(timeSeconds: time, tapNodeID: nodeID)
        }
        let expectedData = try Data(contentsOf: directory.appendingPathComponent("expected.json"))
        let expected = try XCTUnwrap(JSONSerialization.jsonObject(with: expectedData) as? [String: Any])
        return PackageGateFixture(
            level: level,
            actions: actions,
            expectedAcceptedTapCount: try XCTUnwrap(expected["acceptedTapCount"] as? Int),
            expectedFinalActiveEdgeIDs: try XCTUnwrap(expected["finalActiveEdgeIDs"] as? [String: String])
        )
    }
}

private struct FixtureAction {
    let timeSeconds: TimeInterval
    let tapNodeID: String
}

private struct PackageGateFixture {
    let level: LevelData
    let actions: [FixtureAction]
    let expectedAcceptedTapCount: Int
    let expectedFinalActiveEdgeIDs: [String: String]
}
