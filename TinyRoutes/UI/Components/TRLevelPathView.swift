import SwiftUI

struct TRLevelPathSegment: Equatable {
    let start: CGPoint
    let end: CGPoint
    let isUnlocked: Bool
}

struct TRLevelPathCurveSegment: Equatable {
    let start: CGPoint
    let control1: CGPoint
    let control2: CGPoint
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

func makeRowTransitionSegments(
    positions: [TRLevelTilePosition],
    tileStatesByLevelID: [String: TRLevelTileState],
    tileSize: CGSize = TRLevelTile.size,
    endpointInset: CGFloat = connectorEndpointInset,
    curveOutset: CGFloat = 28
) -> [TRLevelPathCurveSegment] {
    let groupedByRow = Dictionary(grouping: positions, by: \.row)
    let sortedRows = groupedByRow.keys.sorted()

    guard sortedRows.count > 1 else { return [] }

    return zip(sortedRows, sortedRows.dropFirst()).compactMap { fromRow, toRow in
        guard toRow == fromRow + 1 else { return nil }

        let fromPositions = groupedByRow[fromRow] ?? []
        let toPositions = groupedByRow[toRow] ?? []
        guard !fromPositions.isEmpty, !toPositions.isEmpty else { return nil }

        let from = fromRow.isMultiple(of: 2)
            ? fromPositions.max { $0.column < $1.column }
            : fromPositions.min { $0.column < $1.column }
        let to = toRow.isMultiple(of: 2)
            ? toPositions.min { $0.column < $1.column }
            : toPositions.max { $0.column < $1.column }
        guard let from, let to else { return nil }

        let fromState = tileStatesByLevelID[from.levelID] ?? .locked
        let toState = tileStatesByLevelID[to.levelID] ?? .locked
        let isRightTurn = from.row.isMultiple(of: 2)
        let horizontalDirection: CGFloat = isRightTurn ? 1 : -1
        let startY = from.center.y + tileSize.height / 2 - endpointInset
        let endY = to.center.y - tileSize.height / 2 + endpointInset
        let startX = from.center.x + horizontalDirection * (tileSize.width / 2 - endpointInset)
        let endX = to.center.x + horizontalDirection * (tileSize.width / 2 - endpointInset)
        let controlX = startX + horizontalDirection * curveOutset
        let verticalDelta = endY - startY

        return TRLevelPathCurveSegment(
            start: CGPoint(x: startX, y: startY),
            control1: CGPoint(x: controlX, y: startY + verticalDelta * 0.35),
            control2: CGPoint(x: controlX, y: startY + verticalDelta * 0.65),
            end: CGPoint(x: endX, y: endY),
            isUnlocked: fromState != .locked && toState != .locked
        )
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
        let transitions = makeRowTransitionSegments(
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

            for transition in transitions {
                var path = Path()
                path.move(to: transition.start)
                path.addCurve(to: transition.end, control1: transition.control1, control2: transition.control2)

                let baseColor = transition.isUnlocked ? unlockedColor : lockedColor
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
