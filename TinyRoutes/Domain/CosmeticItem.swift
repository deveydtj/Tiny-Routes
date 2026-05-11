import Foundation

/// Represents a purchasable or unlockable cosmetic item.
/// Placeholder — fields defined in STORY-003.
struct CosmeticItem: Identifiable {
    let id: String
    var isUnlocked: Bool = false
}
