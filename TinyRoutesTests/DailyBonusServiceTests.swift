import XCTest
@testable import TinyRoutes

final class DailyBonusServiceTests: XCTestCase {
    private var suiteName: String!
    private var defaults: UserDefaults!
    private var repository: SaveDataRepository!
    private var economyService: EconomyService!
    private var service: DailyBonusService!

    override func setUp() {
        super.setUp()
        suiteName = "DailyBonusServiceTests.\(name)"
        defaults = UserDefaults(suiteName: suiteName)!
        defaults.removePersistentDomain(forName: suiteName)
        repository = SaveDataRepository(userDefaults: defaults)
        economyService = EconomyService(repository: repository)
        service = DailyBonusService(
            repository: repository,
            economyService: economyService,
            calendar: gregorianUTC
        )
    }

    override func tearDown() {
        defaults.removePersistentDomain(forName: suiteName)
        service = nil
        economyService = nil
        repository = nil
        defaults = nil
        suiteName = nil
        super.tearDown()
    }

    func testDailyBonusCanBeClaimedOncePerDay() throws {
        let now = try date("2026-05-24T12:00:00Z")

        XCTAssertTrue(service.canClaimDailyBonus(now: now))

        let result = service.claimDailyBonus(now: now)

        XCTAssertEqual(result, .claimed(amount: 50, coinTotal: 50))
        XCTAssertEqual(economyService.coinTotal(), 50)
        XCTAssertFalse(service.canClaimDailyBonus(now: now))
    }

    func testDailyBonusCannotBeClaimedTwiceOnSameLocalDay() throws {
        let morning = try date("2026-05-24T09:00:00Z")
        let evening = try date("2026-05-24T22:00:00Z")

        XCTAssertEqual(service.claimDailyBonus(now: morning), .claimed(amount: 50, coinTotal: 50))

        let secondResult = service.claimDailyBonus(now: evening)

        guard case .alreadyClaimed = secondResult else {
            return XCTFail("Expected alreadyClaimed, got \(secondResult)")
        }
        XCTAssertEqual(economyService.coinTotal(), 50)
    }

    func testDailyBonusCanBeClaimedAgainOnNextLocalDay() throws {
        let firstDay = try date("2026-05-24T23:59:00Z")
        let nextDay = try date("2026-05-25T00:01:00Z")

        XCTAssertEqual(service.claimDailyBonus(now: firstDay), .claimed(amount: 50, coinTotal: 50))
        XCTAssertEqual(service.claimDailyBonus(now: nextDay), .claimed(amount: 50, coinTotal: 100))
    }

    private var gregorianUTC: Calendar {
        var calendar = Calendar(identifier: .gregorian)
        calendar.timeZone = TimeZone(secondsFromGMT: 0)!
        return calendar
    }

    private func date(_ iso8601String: String) throws -> Date {
        try XCTUnwrap(ISO8601DateFormatter().date(from: iso8601String))
    }
}
