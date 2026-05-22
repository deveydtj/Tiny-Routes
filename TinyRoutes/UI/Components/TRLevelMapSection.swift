import SwiftUI

struct TRLevelMapSection: View {
    let levels: [LevelData]
    let progressService: ProgressService
    let onLevelSelected: (String) -> Void

    private let layout = TRSerpentineLayout(
        tileSize: TRLevelTile.size,
        horizontalSpacing: 16,
        verticalSpacing: 34
    )
    private let sideRoadInset: CGFloat = 36
    private let topInset: CGFloat = 32
    private let bottomInset: CGFloat = 22

    var body: some View {
        let positions = layout.positions(for: levels)
        let displayPositions = positions.map { shiftedPosition($0) }
        let contentWidth = mapContentWidth(levelCount: levels.count)
        let contentHeight = mapContentHeight(positions: positions)
        let progressSnapshot = TRLevelProgressSnapshot(levels: levels, progressService: progressService)
        let tileStates = positions.enumerated().map { index, position in
            progressSnapshot.tileState(at: index, levelID: position.levelID)
        }
        let tileStatesByLevelID = Dictionary(uniqueKeysWithValues: zip(positions.map(\.levelID), tileStates))

        ZStack(alignment: .topLeading) {
            TRLevelPathView(
                positions: displayPositions,
                tileStatesByLevelID: tileStatesByLevelID
            )
            .frame(width: contentWidth, height: contentHeight, alignment: .topLeading)

            ForEach(Array(positions.enumerated()), id: \.element.levelID) { index, position in
                let shifted = shiftedPosition(position)

                TRLevelTile(
                    levelNumber: position.levelNumber,
                    state: tileStates[index],
                    stars: progressSnapshot.stars(for: position.levelID)
                ) {
                    onLevelSelected(position.levelID)
                }
                .position(shifted.center)
            }
        }
        .frame(width: contentWidth, height: contentHeight, alignment: .topLeading)
        .frame(maxWidth: .infinity)
        .padding(.vertical, 2)
    }

    private func shiftedPosition(_ position: TRLevelTilePosition) -> TRLevelTilePosition {
        TRLevelTilePosition(
            levelID: position.levelID,
            levelNumber: position.levelNumber,
            row: position.row,
            column: position.column,
            center: CGPoint(
                x: position.center.x + sideRoadInset,
                y: position.center.y + topInset
            )
        )
    }

    private func mapContentWidth(levelCount: Int) -> CGFloat {
        let columns = min(max(levelCount, 1), layout.columns)
        return CGFloat(columns) * layout.tileSize.width
            + CGFloat(max(columns - 1, 0)) * layout.horizontalSpacing
            + sideRoadInset * 2
    }

    private func mapContentHeight(positions: [TRLevelTilePosition]) -> CGFloat {
        let rowCount = (positions.map(\.row).max() ?? -1) + 1
        guard rowCount > 0 else {
            return topInset + bottomInset
        }

        return topInset
            + CGFloat(rowCount) * layout.tileSize.height
            + CGFloat(max(rowCount - 1, 0)) * layout.verticalSpacing
            + bottomInset
    }
}

#Preview("Level Map Section") {
    let levels = (1...11).map { number in
        LevelData(
            id: "level_\(String(format: "%03d", number))",
            name: "Level \(number)",
            graph: RouteGraph(),
            startNodeID: "start",
            packageNodeID: "package",
            destinationNodeID: "destination",
            timeLimitSeconds: 60,
            parTaps: 6
        )
    }

    ZStack {
        Color(red: 0.78, green: 0.90, blue: 0.96)
            .ignoresSafeArea()

        TRLevelMapSection(
            levels: levels,
            progressService: ProgressService(),
            onLevelSelected: { _ in }
        )
        .padding(20)
    }
}
