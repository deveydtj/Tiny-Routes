import Foundation

struct ProfileCollectionSelection: Identifiable, Equatable {
    let id: String
    let label: String
    let value: String
    let systemImage: String
    let accent: ProfileCollectionAccent
    let isSelected: Bool

    static let conceptDefaults: [ProfileCollectionSelection] = [
        ProfileCollectionSelection(
            id: "favorite-theme",
            label: "Favorite Theme",
            value: "Ocean Drive",
            systemImage: "water.waves",
            accent: .theme,
            isSelected: true
        ),
        ProfileCollectionSelection(
            id: "trail",
            label: "Trail",
            value: "Classic",
            systemImage: "point.topleft.down.curvedto.point.bottomright.up",
            accent: .trail,
            isSelected: true
        ),
        ProfileCollectionSelection(
            id: "destination",
            label: "Destination",
            value: "Home",
            systemImage: "house.fill",
            accent: .destination,
            isSelected: true
        )
    ]
}

enum ProfileCollectionAccent: String, Equatable {
    case theme
    case trail
    case destination
}
