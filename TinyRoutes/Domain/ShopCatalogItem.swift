import Foundation

enum ShopCosmeticCategoryID {
    static let routeThemes = "routeThemes"
    static let deliveryDots = "deliveryDots"
    static let trails = "trails"
    static let confetti = "confetti"
    static let destinations = "destinations"
}

struct ShopFeaturedOffer: Identifiable, Equatable {
    let id: String
    let title: String
    let subtitle: String
    let badgeText: String?
    let displayPrice: String
    let style: ShopFeaturedOfferStyle
}

enum ShopFeaturedOfferStyle: Equatable {
    case starterPack
    case removeAds
}

struct ShopCosmeticCategory: Identifiable, Equatable {
    let id: String
    let title: String
    let systemImage: String
}

struct ShopCosmeticOption: Identifiable, Equatable {
    let id: String
    let categoryID: String
    let title: String
    let price: Int?
    let isUnlocked: Bool
    let isSelected: Bool
    let accent: ShopCosmeticAccent
}

enum ShopCosmeticAccent: Equatable {
    case classic
    case oceanDrive
    case forestPath
    case sunsetBlvd
    case neonNights
    case candyLane
}

struct ShopGoodieAction: Identifiable, Equatable {
    let id: String
    let title: String
    let subtitle: String
    let buttonTitle: String
    let icon: ShopGoodieIcon
}

enum ShopGoodieIcon: Equatable {
    case coins
    case gems
    case dailyDeals
    case dailyBonus
}
