import SwiftUI

/// Post-level result screen.
struct ResultScreen: View {

    enum ResultType {
        case completed
        case failed
    }

    let levelID: String
    let result: ResultType
    let elapsedTime: TimeInterval
    let failureReason: LevelFailureReason?
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
            Text("Final Time: \(GameTimeFormatter.elapsed(elapsedTime))")
                .font(.subheadline)
                .foregroundColor(.secondary)
            if let failureReason, case .failed = result {
                Text(failureReason.message)
                    .font(.subheadline)
                    .foregroundColor(.secondary)
            }

            Button("Restart", action: onRestartTapped)
            Button("Back to Menu", action: onExitTapped)
        }
    }
}

#Preview {
    ResultScreen(
        levelID: "level_001",
        result: .completed,
        elapsedTime: 18.4,
        failureReason: nil,
        onRestartTapped: {},
        onExitTapped: {}
    )
}
