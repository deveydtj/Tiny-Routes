import SwiftUI

/// The primary gameplay screen shell.
/// NOTE: Contains only placeholder controls for state flow; no gameplay logic.
struct GameplayScreen: View {
    let levelID: String
    let isPaused: Bool
    let onPauseResumeTapped: () -> Void
    let onCompleteTapped: () -> Void
    let onFailTapped: () -> Void
    let onExitTapped: () -> Void

    var body: some View {
        VStack(spacing: 12) {
            Text("Gameplay")
                .font(.title)
            Text("Level: \(levelID)")
            Text(isPaused ? "Paused" : "Running")
                .foregroundColor(isPaused ? .orange : .green)

            Button(isPaused ? "Resume" : "Pause", action: onPauseResumeTapped)
            Button("Simulate Level Complete", action: onCompleteTapped)
            Button("Simulate Level Failed", action: onFailTapped)
            Button("Exit to Menu", action: onExitTapped)
        }
    }
}

#Preview {
    GameplayScreen(
        levelID: "level_001",
        isPaused: false,
        onPauseResumeTapped: {},
        onCompleteTapped: {},
        onFailTapped: {},
        onExitTapped: {}
    )
}
