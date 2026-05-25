import XCTest
@testable import TinyRoutes

final class SaveDataRepositoryTests: XCTestCase {
    private var suiteName: String!
    private var defaults: UserDefaults!
    private var repository: SaveDataRepository!

    override func setUp() {
        super.setUp()
        suiteName = "SaveDataRepositoryTests.\(name)"
        defaults = UserDefaults(suiteName: suiteName)!
        defaults.removePersistentDomain(forName: suiteName)
        repository = SaveDataRepository(userDefaults: defaults)
    }

    override func tearDown() {
        defaults.removePersistentDomain(forName: suiteName)
        repository = nil
        defaults = nil
        suiteName = nil
        super.tearDown()
    }

    func testLoadWithoutExistingSaveReturnsDefaultProfile() {
        XCTAssertEqual(repository.load(), PlayerProfile.defaultValue)
    }

    func testSaveThenLoadRoundTripsProfile() {
        let profile = PlayerProfile(
            playerName: "Tester",
            unlockedLevelIDs: ["level_001", "level_002"],
            completedLevelIDs: ["level_001"],
            bestStarsByLevelID: ["level_001": 3],
            coinTotal: 125
        )

        repository.save(profile)

        XCTAssertEqual(repository.load(), profile.normalized())
    }

    func testCorruptPayloadFallsBackToDefaultProfile() {
        defaults.set(Data("not-json".utf8), forKey: "playerProfile.v1")

        XCTAssertEqual(repository.load(), PlayerProfile.defaultValue)
    }

    func testResetRemovesProfilePayload() {
        repository.save(PlayerProfile(coinTotal: 100))
        XCTAssertTrue(repository.hasSaveData())

        let resetProfile = repository.reset()

        XCTAssertEqual(resetProfile, PlayerProfile.defaultValue)
        XCTAssertFalse(repository.hasSaveData())
        XCTAssertEqual(repository.load(), PlayerProfile.defaultValue)
    }

    func testUpdateMutatesAndPersistsProfile() {
        repository.update { profile in
            profile.coinTotal = 75
        }

        XCTAssertEqual(repository.load().coinTotal, 75)
    }

    func testUpdateNormalizesBadMutationsBeforeSaving() {
        repository.update { profile in
            profile.coinTotal = -20
            profile.bestStarsByLevelID["level_001"] = 9
        }

        let profile = repository.load()
        XCTAssertEqual(profile.coinTotal, 0)
        XCTAssertEqual(profile.bestStarsByLevelID["level_001"], 3)
    }

    func testLegacyBestStarsMigratesIntoProfileWhenNoProfileExists() {
        defaults.set(["level_001": 2, "level_002": 1], forKey: "bestStarsByLevelID")

        let profile = repository.load()

        XCTAssertEqual(profile.bestStarsByLevelID["level_001"], 2)
        XCTAssertEqual(profile.bestStarsByLevelID["level_002"], 1)
        XCTAssertTrue(profile.completedLevelIDs.contains("level_001"))
        XCTAssertTrue(repository.hasSaveData())
    }

    func testLegacyCorruptStarsAreClampedDuringMigration() {
        defaults.set(["level_001": 9, "level_002": -5], forKey: "bestStarsByLevelID")

        let profile = repository.load()

        XCTAssertEqual(profile.bestStarsByLevelID["level_001"], 3)
        XCTAssertEqual(profile.bestStarsByLevelID["level_002"], 0)
    }

    func testProfilePayloadWinsOverLegacyBestStarsWhenBothExist() {
        defaults.set(["level_001": 3], forKey: "bestStarsByLevelID")
        repository.save(PlayerProfile(bestStarsByLevelID: ["level_002": 2]))

        let profile = repository.load()

        XCTAssertNil(profile.bestStarsByLevelID["level_001"])
        XCTAssertEqual(profile.bestStarsByLevelID["level_002"], 2)
    }

    func testSavedProfileIncludesSchemaVersionAfterJSONEncoding() throws {
        repository.save(PlayerProfile(coinTotal: 10))
        let data = try XCTUnwrap(defaults.data(forKey: "playerProfile.v1"))
        let jsonObject = try JSONSerialization.jsonObject(with: data) as? [String: Any]

        XCTAssertEqual(jsonObject?["schemaVersion"] as? Int, PlayerProfile.currentSchemaVersion)
    }

    func testOlderProfilePayloadWithoutDailyBonusFieldDecodesWithDefault() throws {
        repository.save(PlayerProfile(coinTotal: 10, lastDailyBonusClaimDay: "2026-05-24"))
        let data = try XCTUnwrap(defaults.data(forKey: "playerProfile.v1"))
        var jsonObject = try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])
        jsonObject.removeValue(forKey: "lastDailyBonusClaimDay")
        jsonObject["schemaVersion"] = 1
        let olderPayload = try JSONSerialization.data(withJSONObject: jsonObject)
        defaults.set(olderPayload, forKey: "playerProfile.v1")

        let profile = repository.load()

        XCTAssertNil(profile.lastDailyBonusClaimDay)
        XCTAssertEqual(profile.schemaVersion, PlayerProfile.currentSchemaVersion)
    }
}
