import Foundation

/// Owns top-level navigation and coordinates transitions between app states.
/// Placeholder — implementation added in STORY-002.
final class AppCoordinator: ObservableObject {
    @Published var state: AppState = .boot
}
