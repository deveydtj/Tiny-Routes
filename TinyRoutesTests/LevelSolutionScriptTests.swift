import XCTest

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
}
