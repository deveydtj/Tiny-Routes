import SwiftUI

enum ResultType {
    case completed
    case failed
}

/// Post-level result screen.
struct ResultScreen: View {
    let levelID: String
    let result: ResultType
    let onRestartTapped: () -> Void
    let onExitTapped: () -> Void

    var body: some View {
        VStack(spacing: 12) {
            Text(result == .completed ? "Level Complete" : "Level Failed")
                .font(.title)
            Text("Level: \(levelID)")

            Button("Restart", action: onRestartTapped)
            Button("Back to Menu", action: onExitTapped)
        }
    }
}

#Preview {
    ResultScreen(levelID: "level_001", result: .completed, onRestartTapped: {}, onExitTapped: {})
}
