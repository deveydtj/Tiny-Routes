import SwiftUI

struct TRLevelPathSegment: Equatable {
    let start: CGPoint
    let end: CGPoint
    let isUnlocked: Bool
}

let connectorEndpointInset: CGFloat = 6

func makeHorizontalSegments(
    positions: [TRLevelTilePosition],
    tileStatesByLevelID: [String: TRLevelTileState],
    tileSize: CGSize = TRLevelTile.size,
    endpointInset: CGFloat = connectorEndpointInset
) -> [TRLevelPathSegment] {
    let groupedByRow = Dictionary(grouping: positions, by: \.row)
    let sortedRows = groupedByRow.keys.sorted()

    return sortedRows.flatMap { row in
        let rowPositions = (groupedByRow[row] ?? []).sorted { $0.column < $1.column }
        guard rowPositions.count > 1 else { return [] }

        return zip(rowPositions, rowPositions.dropFirst()).map { left, right in
            let leftCenter = left.center
            let rightCenter = right.center
            let startX = min(leftCenter.x, rightCenter.x) + tileSize.width / 2 - endpointInset
            let endX = max(leftCenter.x, rightCenter.x) - tileSize.width / 2 + endpointInset
            let leftState = tileStatesByLevelID[left.levelID] ?? .locked
            let rightState = tileStatesByLevelID[right.levelID] ?? .locked

            return TRLevelPathSegment(
                start: CGPoint(x: startX, y: leftCenter.y),
                end: CGPoint(x: endX, y: leftCenter.y),
                isUnlocked: leftState != .locked && rightState != .locked
            )
        }
    }
}

struct TRLevelPathView: View {
    let positions: [TRLevelTilePosition]
    let tileStatesByLevelID: [String: TRLevelTileState]

    private let unlockedColor = Color(red: 0.20, green: 0.74, blue: 0.50)
    private let lockedColor = Color(red: 0.72, green: 0.77, blue: 0.84)
    private let dashHighlightColor = Color.white.opacity(0.45)

    var body: some View {
        let segments = makeHorizontalSegments(
            positions: positions,
            tileStatesByLevelID: tileStatesByLevelID
        )

        Canvas { context, _ in
            for segment in segments {
                var path = Path()
                path.move(to: segment.start)
                path.addLine(to: segment.end)

                let baseColor = segment.isUnlocked ? unlockedColor : lockedColor
                context.stroke(
                    path,
                    with: .color(baseColor),
                    style: StrokeStyle(lineWidth: 16, lineCap: .round, lineJoin: .round)
                )
                context.stroke(
                    path,
                    with: .color(dashHighlightColor),
                    style: StrokeStyle(lineWidth: 3, lineCap: .round, dash: [8, 12])
                )
            }
        }
        .allowsHitTesting(false)
        .accessibilityHidden(true)
    }
}
