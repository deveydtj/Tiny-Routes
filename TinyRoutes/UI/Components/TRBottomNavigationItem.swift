import SwiftUI

enum TRBottomTab: CaseIterable, Equatable {
    case home
    case levels
    case shop
    case profile

    var title: String {
        switch self {
        case .home:
            return "Home"
        case .levels:
            return "Levels"
        case .shop:
            return "Shop"
        case .profile:
            return "Profile"
        }
    }

    var systemImage: String {
        switch self {
        case .home:
            return "house"
        case .levels:
            return "map"
        case .shop:
            return "bag"
        case .profile:
            return "person"
        }
    }
}
