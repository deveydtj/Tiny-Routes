import SwiftUI
import UIKit

/// The table a board stands on: the soil bands of its base and the studio sky
/// behind it. Never the lawn, a road or a piece, so nothing a player plans with
/// changes. Raw values are the shop's cosmetic IDs.
enum MultiVanTableTheme: String, CaseIterable {
    case classic = "themeClassic"
    case oceanDrive = "themeOceanDrive"
    case forestPath = "themeForestPath"
    case sunsetBlvd = "themeSunsetBlvd"
    case neonNights = "themeNeonNights"
    case candyLane = "themeCandyLane"

    /// The look every board had before themes; a new player starts with it.
    static let standard = oceanDrive

    /// The upper band of the base.
    var soilHex: UInt32 {
        switch self {
        case .classic: 0xC49A6C
        case .oceanDrive: 0xA26E48
        case .forestPath: 0x6F6A45
        case .sunsetBlvd: 0xC0664A
        case .neonNights: 0x5B4E9C
        case .candyLane: 0xE58FB0
        }
    }

    /// The lower band of the base.
    var deepSoilHex: UInt32 {
        switch self {
        case .classic: 0x9C7446
        case .oceanDrive: 0x7B5339
        case .forestPath: 0x4D4A2F
        case .sunsetBlvd: 0x8F4433
        case .neonNights: 0x3D3373
        case .candyLane: 0xC76A93
        }
    }

    /// The sky behind the table, from overhead down to the horizon.
    var skyHexes: [UInt32] {
        switch self {
        case .classic: [0xE9E2D0, 0xF3EDDF, 0xFBF5EA]
        case .oceanDrive: [0xBFE1F2, 0xE4F3F6, 0xFBF1E3]
        case .forestPath: [0xBCDDC3, 0xDDEEDB, 0xF6F3E0]
        case .sunsetBlvd: [0xF5B98F, 0xFAD9BC, 0xFDF0DC]
        case .neonNights: [0x8E86D6, 0xC3B4E8, 0xF0DDF0]
        case .candyLane: [0xF8C6DC, 0xFBE2EC, 0xFFF6E8]
        }
    }
}

/// The paper thrown when every van is home. A delivery's own little pop keeps
/// the van's colour. Raw values are the shop's cosmetic IDs.
enum MultiVanConfettiStyle: String, CaseIterable {
    case paper = "confettiStars"
    case sparkPop = "confettiSpark"
    case leaves = "confettiGarden"
    case sugarBurst = "confettiCandy"

    static let standard = paper

    /// The win burst's colours on the 3D table; nil keeps the vans' colours and
    /// white. The flat board's burst uses the same palette for the same ID.
    var winColors: [UIColor]? {
        self == .paper ? nil : TRConfettiScene.colors(forConfettiID: rawValue)
    }
}

/// What the player has chosen in the shop, as the boards draw it. Art only: no
/// cosmetic changes a route, a timing, a hint or a star.
struct MultiVanCosmetics: Equatable {
    var table = MultiVanTableTheme.standard
    var confetti = MultiVanConfettiStyle.standard

    static let standard = MultiVanCosmetics()

    init(table: MultiVanTableTheme = .standard, confetti: MultiVanConfettiStyle = .standard) {
        self.table = table
        self.confetti = confetti
    }

    /// The profile's selections, where the player owns them.
    init(profile: PlayerProfile) {
        func owned(_ categoryID: String) -> String? {
            profile.selectedCosmeticIDByCategoryID[categoryID].flatMap { profile.ownedCosmeticIDs.contains($0) ? $0 : nil }
        }
        table = owned(ShopCosmeticCategoryID.routeThemes).flatMap(MultiVanTableTheme.init) ?? .standard
        confetti = owned(ShopCosmeticCategoryID.confetti).flatMap(MultiVanConfettiStyle.init) ?? .standard
    }

    /// As it would look with `option` in use: the shop's preview.
    func trying(_ option: ShopCosmeticOption) -> MultiVanCosmetics {
        var cosmetics = self
        if let table = MultiVanTableTheme(rawValue: option.id) { cosmetics.table = table }
        if let confetti = MultiVanConfettiStyle(rawValue: option.id) { cosmetics.confetti = confetti }
        return cosmetics
    }
}

private struct MultiVanCosmeticsKey: EnvironmentKey {
    static let defaultValue = MultiVanCosmetics.standard
}

extension EnvironmentValues {
    /// The cosmetics both boards draw with.
    var multiVanCosmetics: MultiVanCosmetics {
        get { self[MultiVanCosmeticsKey.self] }
        set { self[MultiVanCosmeticsKey.self] = newValue }
    }
}
