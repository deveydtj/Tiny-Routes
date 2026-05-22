import SwiftUI

enum TRBottomTab: CaseIterable, Equatable {
    case home
    case levels
    case shop
    case profile

    var title: String {
        switch self {
        case .home:
            "Home"
        case .levels:
            "Levels"
        case .shop:
            "Shop"
        case .profile:
            "Profile"
        }
    }

    var systemImage: String {
        switch self {
        case .home:
            "house"
        case .levels:
            "map"
        case .shop:
            "bag"
        case .profile:
            "person"
        }
    }
}
