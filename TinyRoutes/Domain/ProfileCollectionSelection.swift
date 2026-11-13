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
            label: "Table Theme",
            value: "Ocean Drive",
            systemImage: "square.stack.3d.up.fill",
            accent: .theme,
            isSelected: true
        ),
        ProfileCollectionSelection(
            id: "confetti",
            label: "Confetti",
            value: "Classic Paper",
            systemImage: "party.popper.fill",
            accent: .trail,
            isSelected: true
        )
    ]
}

enum ProfileCollectionAccent: String, Equatable {
    case theme
    case trail
    case destination
}
