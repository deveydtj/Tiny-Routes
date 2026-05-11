import Foundation

/// Represents lightweight metadata for a cosmetic unlock item.
struct CosmeticItem: Identifiable, Codable {
    let id: String
    var type: CosmeticType
    var isUnlocked: Bool = false
}

/// Defines the type category for a cosmetic item.
enum CosmeticType: String, Codable {
    case dot
    case trail
    case theme
}
