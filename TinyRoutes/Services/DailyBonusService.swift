import Foundation

enum DailyBonusClaimResult: Equatable {
    case claimed(amount: Int, coinTotal: Int)
    case alreadyClaimed(nextClaimDate: Date?)
}

final class DailyBonusService {
    static let defaultCoinAward = 50

    private let repository: SaveDataRepository
    private let economyService: EconomyService
    private let calendar: Calendar
    private let coinAward: Int

    init(
        repository: SaveDataRepository = SaveDataRepository(),
        economyService: EconomyService? = nil,
        calendar: Calendar = .current,
        coinAward: Int = DailyBonusService.defaultCoinAward
    ) {
        self.repository = repository
        self.economyService = economyService ?? EconomyService(repository: repository)
        self.calendar = calendar
        self.coinAward = coinAward
    }

    func canClaimDailyBonus(now: Date = Date()) -> Bool {
        repository.load().lastDailyBonusClaimDay != dayKey(for: now)
    }

    @discardableResult
    func claimDailyBonus(now: Date = Date()) -> DailyBonusClaimResult {
        let claimDay = dayKey(for: now)
        guard repository.load().lastDailyBonusClaimDay != claimDay else {
            return .alreadyClaimed(nextClaimDate: nextClaimDate(after: now))
        }

        let updatedCoinTotal = economyService.addCoins(coinAward, reason: .dailyBonus)
        repository.update { profile in
            profile.lastDailyBonusClaimDay = claimDay
        }

        return .claimed(amount: coinAward, coinTotal: updatedCoinTotal)
    }

    private func dayKey(for date: Date) -> String {
        let components = calendar.dateComponents([.year, .month, .day], from: date)
        return String(
            format: "%04d-%02d-%02d",
            components.year ?? 0,
            components.month ?? 0,
            components.day ?? 0
        )
    }

    private func nextClaimDate(after date: Date) -> Date? {
        guard let startOfNextDay = calendar.date(
            byAdding: .day,
            value: 1,
            to: calendar.startOfDay(for: date)
        ) else {
            return nil
        }

        return startOfNextDay
    }
}
