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

/// Computes a serpentine tile layout with configurable columns (default: 4).
///
/// Even-numbered rows (0, 2, …) run left-to-right; odd-numbered rows (1, 3, …) run right-to-left.
struct TRSerpentineLayout {
    var tileSize: CGSize
    var horizontalSpacing: CGFloat
    var verticalSpacing: CGFloat
    var columns: Int = 4

    /// Returns the tile positions for `levels` in input order.
    func positions(for levels: [LevelData]) -> [TRLevelTilePosition] {
        precondition(columns > 0, "columns must be greater than 0")
        return levels.enumerated().map { index, level in
            let row = index / columns
            let positionInRow = index % columns
            let visualColumn = row.isMultiple(of: 2) ? positionInRow : (columns - 1 - positionInRow)
            let x = CGFloat(visualColumn) * (tileSize.width + horizontalSpacing) + tileSize.width / 2
            let y = CGFloat(row) * (tileSize.height + verticalSpacing) + tileSize.height / 2
            return TRLevelTilePosition(
                levelID: level.id,
                levelNumber: levelNumber(for: level, fallback: index + 1),
                row: row,
                column: visualColumn,
                center: CGPoint(x: x, y: y)
            )
        }
    }

    private func levelNumber(for level: LevelData, fallback: Int) -> Int {
        guard let suffix = level.id.split(separator: "_").last,
              let parsed = Int(suffix) else {
            return fallback
        }
        return parsed
    }
}

struct TRLevelProgressSnapshot {
    let bestStarsByLevelID: [String: Int]
    let firstIncompleteIndex: Int

    init(levels: [LevelData], progressService: ProgressService) {
        var starsByLevelID: [String: Int] = [:]
        starsByLevelID.reserveCapacity(levels.count)

        for level in levels {
            starsByLevelID[level.id] = progressService.bestStars(for: level.id)
        }

        self.bestStarsByLevelID = starsByLevelID
        self.firstIncompleteIndex = levels.firstIndex { (starsByLevelID[$0.id] ?? 0) == 0 } ?? levels.count
    }

    func stars(for levelID: String) -> Int {
        bestStarsByLevelID[levelID] ?? 0
    }

    func tileState(at index: Int, levelID: String) -> TRLevelTileState {
        if stars(for: levelID) > 0 { return .completed }
        if index == firstIncompleteIndex { return .current }
        return .locked
    }
}

// MARK: - Level Selection Screen

/// Level selection screen.
struct LevelSelectScreen: View {
    let levels: [LevelData]
    let onBackTapped: () -> Void
    let onLevelSelected: (String) -> Void
    private let progressService: ProgressService

    init(
        levels: [LevelData],
        onBackTapped: @escaping () -> Void,
        onLevelSelected: @escaping (String) -> Void,
        progressService: ProgressService = ProgressService()
    ) {
        self.levels = levels
        self.onBackTapped = onBackTapped
        self.onLevelSelected = onLevelSelected
        self.progressService = progressService
    }

    private let layout = TRSerpentineLayout(
        tileSize: TRLevelTile.size,
        horizontalSpacing: 16,
        verticalSpacing: 24
    )

    var body: some View {
        let positions = layout.positions(for: levels)
        let contentWidth = mapContentWidth(levelCount: levels.count)
        let contentHeight = mapContentHeight(positions: positions)
        let progressSnapshot = TRLevelProgressSnapshot(levels: levels, progressService: progressService)
        let tileStates = positions.enumerated().map { index, position in
            progressSnapshot.tileState(at: index, levelID: position.levelID)
        }
        let tileStatesByLevelID = Dictionary(uniqueKeysWithValues: zip(positions.map(\.levelID), tileStates))

        return VStack(spacing: 12) {
            HStack {
                Button("Back", action: onBackTapped)
                Spacer()
            }
            .overlay {
                Text("Select a Level")
                    .font(.title2)
                    .fontWeight(.semibold)
            }

            ScrollView([.vertical, .horizontal], showsIndicators: false) {
                ZStack(alignment: .topLeading) {
                    TRLevelPathView(
                        positions: positions,
                        tileStatesByLevelID: tileStatesByLevelID
                    )
                    .frame(width: contentWidth, height: contentHeight, alignment: .topLeading)

                    ForEach(Array(positions.enumerated()), id: \.element.levelID) { index, position in
                        TRLevelTile(
                            levelNumber: position.levelNumber,
                            state: tileStates[index],
                            stars: progressSnapshot.stars(for: position.levelID)
                        ) {
                            onLevelSelected(position.levelID)
                        }
                        .position(position.center)
                    }
                }
                .frame(width: contentWidth, height: contentHeight, alignment: .topLeading)
                .frame(maxWidth: .infinity)
                .padding(.vertical, 4)
            }
        }
        .padding(.horizontal, 8)
    }

    private func mapContentWidth(levelCount: Int) -> CGFloat {
        let columns = min(max(levelCount, 1), layout.columns)
        return CGFloat(columns) * layout.tileSize.width
            + CGFloat(max(columns - 1, 0)) * layout.horizontalSpacing
    }

    private func mapContentHeight(positions: [TRLevelTilePosition]) -> CGFloat {
        let rowCount = (positions.map(\.row).max() ?? -1) + 1
        guard rowCount > 0 else {
            return 0
        }

        return CGFloat(rowCount) * layout.tileSize.height
            + CGFloat(max(rowCount - 1, 0)) * layout.verticalSpacing
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
