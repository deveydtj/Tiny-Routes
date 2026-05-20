import SwiftUI

// MARK: - Serpentine Layout Helper

/// Describes the computed visual position of a single level tile on the selection map.
struct TRLevelTilePosition {
    let levelID: String
    let levelNumber: Int
    let row: Int
    let column: Int
    let center: CGPoint
}

/// Computes a four-column serpentine tile layout.
///
/// Odd-numbered visual rows (0, 2, …) run left-to-right; even-numbered rows (1, 3, …) run right-to-left.
struct TRSerpentineLayout {
    var tileSize: CGSize
    var horizontalSpacing: CGFloat
    var verticalSpacing: CGFloat
    var columns: Int = 4

    /// Returns the tile positions for `levels`, sorted by level order.
    func positions(for levels: [LevelData]) -> [TRLevelTilePosition] {
        levels.enumerated().map { index, level in
            let row = index / columns
            let positionInRow = index % columns
            let visualColumn = row.isMultiple(of: 2) ? positionInRow : (columns - 1 - positionInRow)
            let x = CGFloat(visualColumn) * (tileSize.width + horizontalSpacing) + tileSize.width / 2
            let y = CGFloat(row) * (tileSize.height + verticalSpacing) + tileSize.height / 2
            return TRLevelTilePosition(
                levelID: level.id,
                levelNumber: index + 1,
                row: row,
                column: visualColumn,
                center: CGPoint(x: x, y: y)
            )
        }
    }
}

// MARK: - Level Selection Screen

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
