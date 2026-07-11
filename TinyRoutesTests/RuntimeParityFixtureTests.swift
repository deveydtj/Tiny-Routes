import Foundation
import XCTest

final class RuntimeParityFixtureTests: XCTestCase {
    func testSharedRuntimeParityFixturesAreDiscoverableAndValidJSON() throws {
        let testFile = URL(fileURLWithPath: #filePath)
        let root = testFile.deletingLastPathComponent().deletingLastPathComponent()
            .appendingPathComponent("SharedFixtures/RuntimeParity")
        let manifestData = try Data(contentsOf: root.appendingPathComponent("manifest.json"))
        let manifest = try XCTUnwrap(JSONSerialization.jsonObject(with: manifestData) as? [String: Any])
        let fixtures = try XCTUnwrap(manifest["fixtures"] as? [[String: Any]])
        XCTAssertEqual(fixtures.count, 13)
        for fixture in fixtures {
            for key in ["level", "events", "expected"] {
                let relativePath = try XCTUnwrap(fixture[key] as? String)
                let data = try Data(contentsOf: root.appendingPathComponent(relativePath))
                XCTAssertTrue(JSONSerialization.isValidJSONObject(try JSONSerialization.jsonObject(with: data)))
            }
        }
    }
}
