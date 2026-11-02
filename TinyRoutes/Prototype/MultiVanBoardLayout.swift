import CoreGraphics

enum MultiVanBoardLayout {
    static func make(level: MultiVanLevel, in rect: CGRect) -> BoardLayout {
        let columns = CGFloat(MultiVanTuning.default.gridColumns)
        let rows = CGFloat(MultiVanTuning.default.gridRows)
        // The point spans are one unit smaller, leaving half a unit on each edge.
        let scale = min(rect.width / columns, rect.height / rows)
        let originX = rect.midX - (columns - 1) * scale / 2
        let originY = rect.midY - (rows - 1) * scale / 2
        let projection = BoardLayout(
            pointsByNodeID: [:],
            coordinateScale: scale,
            minX: 0,
            maxY: Double(rows - 1),
            originX: originX,
            originY: originY
        )
        let points = Dictionary(uniqueKeysWithValues: level.graph.nodes.map { node in
            (node.id, projection.point(for: RoadPoint(x: node.x, y: node.y))!)
        })
        return BoardLayout(
            pointsByNodeID: points,
            coordinateScale: scale,
            minX: 0,
            maxY: Double(rows - 1),
            originX: originX,
            originY: originY
        )
    }
}
