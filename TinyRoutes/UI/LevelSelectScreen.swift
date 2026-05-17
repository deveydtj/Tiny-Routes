import SwiftUI

/// Level selection screen.
struct LevelSelectScreen: View {
    let levels: [LevelData]
    let onBackTapped: () -> Void
    let onLevelSelected: (String) -> Void

    var body: some View {
        VStack(spacing: 12) {
            Text("Select a Level")
                .font(.title2)

            ForEach(levels) { level in
                Button(level.name) {
                    onLevelSelected(level.id)
                }
            }

            Button("Back", action: onBackTapped)
        }
    }
}

struct LevelSelectScreen_Previews: PreviewProvider {
    static var previews: some View {
        LevelSelectScreen(
            levels: [
                LevelData(
                    id: "level_001",
                    name: "First Dispatch",
                    graph: RouteGraph(),
                    startNodeID: "start",
                    packageNodeID: "package",
                    destinationNodeID: "destination",
                    timeLimitSeconds: 45,
                    parTaps: 6
                ),
                LevelData(
                    id: "level_002",
                    name: "Loop Pickup",
                    graph: RouteGraph(),
                    startNodeID: "start",
                    packageNodeID: "package",
                    destinationNodeID: "destination",
                    timeLimitSeconds: 55,
                    parTaps: 2
                )
            ],
            onBackTapped: {},
            onLevelSelected: { _ in }
        )
    }
}
