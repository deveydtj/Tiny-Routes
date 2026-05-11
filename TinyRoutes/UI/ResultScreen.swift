import SwiftUI

/// Post-level result screen.
struct ResultScreen: View {

    enum ResultType {
        case completed
        case failed
    }

    let levelID: String
    let result: ResultType
    let onRestartTapped: () -> Void
    let onExitTapped: () -> Void

    private var titleText: String {
        switch result {
        case .completed: "Level Complete"
        case .failed: "Level Failed"
        }
    }

    var body: some View {
        VStack(spacing: 12) {
            Text(titleText)
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
