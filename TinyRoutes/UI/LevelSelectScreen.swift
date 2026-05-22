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
    let onLevelSelected: (String) -> Void
    let onSettingsTapped: (() -> Void)?
    private let progressService: ProgressService

    init(
        levels: [LevelData],
        onLevelSelected: @escaping (String) -> Void,
        onSettingsTapped: (() -> Void)? = nil,
        progressService: ProgressService = ProgressService()
    ) {
        self.levels = levels
        self.onLevelSelected = onLevelSelected
        self.onSettingsTapped = onSettingsTapped
        self.progressService = progressService
    }

    var body: some View {
        ScrollView(.vertical, showsIndicators: false) {
            VStack(spacing: 16) {
                TRLevelPageHeader(
                    onSettingsTapped: {
                        onSettingsTapped?()
                    },
                    onAddCurrencyTapped: {}
                )
                .padding(.top, 10)

                TRDailyRoutePlaceholderCard()

                TRMilestoneRewardsPlaceholderCard()

                TRLevelMapSection(
                    levels: levels,
                    progressService: progressService,
                    onLevelSelected: onLevelSelected
                )

                TRStarCollectorPlaceholderCard()
                    .padding(.bottom, 12)
            }
            .padding(.horizontal, 20)
            .padding(.top, 4)
            .padding(.bottom, 8)
        }
        .background {
            LinearGradient(
                colors: [
                    Color.white.opacity(0.18),
                    Color(red: 0.72, green: 0.90, blue: 0.78).opacity(0.10)
                ],
                startPoint: .top,
                endPoint: .bottom
            )
            .ignoresSafeArea()
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
            onLevelSelected: { _ in }
        )
    }
}
