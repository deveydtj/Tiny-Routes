import SwiftUI

/// Level selection screen.
struct LevelSelectScreen: View {
    let onBackTapped: () -> Void
    let onLevelSelected: (String) -> Void

    private static let levelIDs: [String] = ["level_001", "level_002", "level_003"]

    var body: some View {
        VStack(spacing: 12) {
            Text("Select a Level")
                .font(.title2)

            ForEach(Self.levelIDs, id: \.self) { levelID in
                Button(levelID.replacingOccurrences(of: "_", with: " ").capitalized) {
                    onLevelSelected(levelID)
                }
            }

            Button("Back", action: onBackTapped)
        }
    }
}

struct LevelSelectScreen_Previews: PreviewProvider {
    static var previews: some View {
        LevelSelectScreen(onBackTapped: {}, onLevelSelected: { _ in })
    }
}
