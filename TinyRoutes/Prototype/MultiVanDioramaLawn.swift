import SwiftUI
import UIKit

/// The diorama's lawn, painted once per level: mown grass, the scenery's pond, flower
/// beds and contact shadows, then the road network with its depot bays, switch
/// plazas, driveways and barrier hatching. Roads are
/// stroked from the flat board's own `RoadPath`s and `BoardLayout` projection, so
/// they sit exactly where the flat board draws them. Renderer-free: the scene lays
/// the image over the slab's top face, which spans it edge to edge.
enum MultiVanDioramaLawn {
    /// Texture pixels per grid unit, as in the HTML prototype.
    static let pixelsPerUnit: CGFloat = 180
    /// The prototype tuned its grass and grain in canvas pixels at 180 per unit.
    private static let px = pixelsPerUnit / 180

    static let imageSize = CGSize(
        width: (MultiVanDioramaGeometry.slabWidth * pixelsPerUnit).rounded(),
        height: (MultiVanDioramaGeometry.slabDepth * pixelsPerUnit).rounded()
    )

    enum Palette {
        static let lawn = UIColor(dioramaHex: 0x8FC766)
        static let curb = UIColor(dioramaHex: 0xEFE6D2)
        static let edgeLine = UIColor.white
        static let asphalt = UIColor(dioramaHex: 0x626779)
        static let driveway = UIColor(dioramaHex: 0xE4D4B4)
        static let bay = UIColor(dioramaHex: 0x6F7486)
    }

    /// Widths and radii in grid units. Each pass is stroked over the whole network,
    /// so where roads overlap they merge into one road.
    enum Measure {
        static let curbWidth = 0.47
        static let edgeLineWidth = 0.335
        static let asphaltWidth = 0.30
        static let plazaRadii = (curb: 0.34, edgeLine: 0.30, asphalt: 0.285)
        static let drivewayWidth = 0.4
        static let drivewayLength = 0.2
    }

    /// Grid to texture pixels: the flat board's layout for a board of `pixelsPerUnit`
    /// per unit, centred where `MultiVanDioramaGeometry.world` puts the grid's centre.
    static func layout(for level: MultiVanLevel) -> BoardLayout {
        let tuning = MultiVanTuning.default
        let centre = MultiVanDioramaGeometry.world(
            gridX: Double(tuning.gridColumns - 1) / 2, gridY: Double(tuning.gridRows - 1) / 2
        )
        let grid = CGSize(width: CGFloat(tuning.gridColumns) * pixelsPerUnit, height: CGFloat(tuning.gridRows) * pixelsPerUnit)
        let midX = (centre.x + MultiVanDioramaGeometry.slabWidth / 2) * pixelsPerUnit
        let midY = (centre.z + MultiVanDioramaGeometry.slabDepth / 2) * pixelsPerUnit
        return MultiVanBoardLayout.make(
            level: level,
            in: CGRect(x: midX - grid.width / 2, y: midY - grid.height / 2, width: grid.width, height: grid.height)
        )
    }

    /// What the lawn marks besides roads, in grid space. The board's pieces stand on
    /// these marks, and scenery keeps clear of them.
    struct Features {
        struct Depot {
            let nodeID: String
            let point: RoadPoint
            let heading: RoadVector
            /// Every van that waits here, in authored order.
            let colors: [VanColor]
        }

        struct Marking {
            let nodeID: String
            let point: RoadPoint
            let heading: RoadVector
        }

        struct House {
            let marking: Marking
            let color: VanColor

            /// Where the house stands, set back from its node along the arrival direction.
            var centre: RoadPoint {
                MultiVanDioramaGeometry.offset(marking.point, along: marking.heading, by: MultiVanDioramaGeometry.houseSetback)
            }
        }

        let plazas: [RoadPoint]
        let depots: [Depot]
        /// Each house's node and the road's arrival direction, towards its door.
        let houses: [House]
        let barriers: [Marking]

        init(level: MultiVanLevel, graph: RuntimeRouteGraph) {
            let point = { (node: RuntimeRouteNode) in RoadPoint(x: node.x, y: node.y) }
            plazas = MultiVanBoardRules.switchNodes(in: graph).map(point)
            var startIDs: [String] = []
            for van in level.vans where !startIDs.contains(van.startNodeID) { startIDs.append(van.startNodeID) }
            depots = startIDs.compactMap { nodeID in
                guard let node = graph.nodesByID[nodeID] else { return nil }
                return Depot(
                    nodeID: nodeID,
                    point: point(node),
                    heading: MultiVanBoardRules.departureTangent(from: nodeID, in: graph) ?? RoadVector(x: 0, y: 1),
                    colors: level.vans.filter { $0.startNodeID == nodeID }.map(\.color)
                )
            }
            houses = level.houses.compactMap { house in
                guard let node = graph.nodesByID[house.nodeID] else { return nil }
                let heading = MultiVanBoardRules.arrivalTangent(at: house.nodeID, in: graph) ?? RoadVector(x: 0, y: 1)
                return House(marking: Marking(nodeID: house.nodeID, point: point(node), heading: heading), color: house.color)
            }
            barriers = MultiVanBoardRules.barrierNodes(in: graph, houses: level.houses).map { node in
                Marking(
                    nodeID: node.id,
                    point: point(node),
                    heading: MultiVanBoardRules.arrivalTangent(at: node.id, in: graph) ?? RoadVector(x: 1, y: 0)
                )
            }
        }
    }

    static func image(for level: MultiVanLevel, graph: RuntimeRouteGraph) -> UIImage {
        image(for: level, graph: graph, scenery: MultiVanDioramaScenery(level: level, graph: graph))
    }

    /// The lawn under `scenery`: its pond and flower beds are painted on, with soft
    /// contact shadows under the trees, bushes and houses that stand on it.
    static func image(for level: MultiVanLevel, graph: RuntimeRouteGraph, scenery: MultiVanDioramaScenery) -> UIImage {
        let layout = layout(for: level)
        let features = Features(level: level, graph: graph)
        let roads = roadLayer(graph: graph, features: features, layout: layout)
        return UIGraphicsImageRenderer(size: imageSize, format: textureFormat(opaque: true)).image { context in
            let g = context.cgContext
            let pixel = { (point: RoadPoint) in layout.point(for: point) ?? .zero }
            var random = MultiVanDioramaRandom(seed: UInt32(Int(level.id.filter(\.isNumber)) ?? 0) &* 97)
            paintGrass(g, random: &random)
            paintScenery(g, scenery: scenery, houses: features.houses, pixel: pixel, random: &random)
            // The road layer goes down in one piece so the curb casts a single shadow.
            g.saveGState()
            g.setShadow(
                offset: CGSize(width: -0.012 * pixelsPerUnit, height: 0.02 * pixelsPerUnit),
                blur: 0.05 * pixelsPerUnit,
                color: UIColor(red: 25 / 255, green: 45 / 255, blue: 15 / 255, alpha: 0.38).cgColor
            )
            roads.draw(at: .zero)
            g.restoreGState()
            addGrain(g, alpha: 0.05)
        }
    }

    // MARK: - Grass

    private static func paintGrass(_ g: CGContext, random: inout MultiVanDioramaRandom) {
        let size = imageSize
        g.setFillColor(Palette.lawn.cgColor)
        g.fill(CGRect(origin: .zero, size: size))
        // Mowing stripes across the board.
        let stripe = pixelsPerUnit / 2
        for (index, y) in stride(from: 0, to: size.height, by: stripe).enumerated() {
            g.setFillColor(index.isMultiple(of: 2)
                ? UIColor(red: 40 / 255, green: 80 / 255, blue: 20 / 255, alpha: 0.035).cgColor
                : UIColor(white: 1, alpha: 0.05).cgColor)
            g.fill(CGRect(x: 0, y: y, width: size.width, height: stripe))
        }
        let speckles = [0x7FB85A, 0x9FD474, 0x86C060, 0xA9DA7F].map { UIColor(dioramaHex: $0) }
        for index in 0..<16_000 {
            let alpha = 0.35 + random.next() * 0.4
            let x = random.next() * size.width, y = random.next() * size.height
            let radius = (0.8 + random.next() * 2.2) * px
            g.setFillColor(speckles[index % 4].withAlphaComponent(alpha).cgColor)
            g.fillEllipse(in: CGRect(x: x - radius, y: y - radius, width: radius * 2, height: radius * 2))
        }
        // Blades of grass, as small ticks.
        let blades = CGMutablePath()
        for _ in 0..<900 {
            let x = random.next() * size.width, y = random.next() * size.height
            blades.move(to: CGPoint(x: x - 3 * px, y: y - 5 * px))
            blades.addLine(to: CGPoint(x: x, y: y))
            blades.addLine(to: CGPoint(x: x + 3 * px, y: y - 6 * px))
        }
        g.addPath(blades)
        g.setStrokeColor(UIColor(red: 60 / 255, green: 110 / 255, blue: 40 / 255, alpha: 0.35).cgColor)
        g.setLineWidth(1.6 * px)
        g.strokePath()
    }

    // MARK: - Scenery

    private static func paintScenery(
        _ g: CGContext, scenery: MultiVanDioramaScenery, houses: [Features.House],
        pixel: (RoadPoint) -> CGPoint, random: inout MultiVanDioramaRandom
    ) {
        let unit = pixelsPerUnit
        // Contact shadows, so the cutouts stand on the lawn rather than float over it.
        func shade(_ point: RoadPoint, radius: Double, alpha: CGFloat) {
            let centre = pixel(point)
            let colors = [alpha, 0].map { UIColor(red: 30 / 255, green: 60 / 255, blue: 20 / 255, alpha: $0).cgColor } as CFArray
            let gradient = CGGradient(colorsSpace: nil, colors: colors, locations: [0, 1])!
            g.drawRadialGradient(gradient, startCenter: centre, startRadius: 0, endCenter: centre, endRadius: radius * unit, options: [])
        }
        for item in scenery.items {
            switch item.kind {
            case .tree: shade(item.point, radius: 0.26, alpha: 0.35)
            case .bush: shade(item.point, radius: 0.18, alpha: 0.28)
            case .flowers, .resident: break
            }
        }
        houses.forEach { shade($0.centre, radius: 0.55, alpha: 0.4) }

        if let pond = scenery.pond {
            let centre = pixel(pond.centre), radiusX = pond.radiusX * unit, radiusY = pond.radiusY * unit
            g.saveGState()
            g.translateBy(x: centre.x, y: centre.y)
            // The texture's y runs down the board, so an anticlockwise turn is negative here.
            g.rotate(by: -pond.angle)
            let ellipse = { (x: CGFloat, y: CGFloat, width: CGFloat, height: CGFloat, hex: Int) in
                g.setFillColor(UIColor(dioramaHex: hex).cgColor)
                g.fillEllipse(in: CGRect(x: x - width, y: y - height, width: width * 2, height: height * 2))
            }
            ellipse(0, 0, radiusX + 12 * px, radiusY + 12 * px, 0xE8D9B5)
            ellipse(0, 0, radiusX, radiusY, 0x5FB2DA)
            ellipse(-radiusX * 0.15, -radiusY * 0.2, radiusX * 0.7, radiusY * 0.55, 0x86CBE8)
            // Lily pads.
            for _ in 0..<3 {
                let x = (random.next() - 0.5) * radiusX, y = (random.next() - 0.5) * radiusY
                ellipse(x, y, 9 * px, 9 * px, 0x5EA44D)
            }
            g.restoreGState()
        }

        for item in scenery.items {
            guard case let .flowers(color) = item.kind else { continue }
            let centre = pixel(item.point)
            for _ in 0..<9 {
                let x = centre.x + (random.next() - 0.5) * 34 * px, y = centre.y + (random.next() - 0.5) * 26 * px
                let dot = { (dy: CGFloat, radius: CGFloat, color: UIColor) in
                    g.setFillColor(color.cgColor)
                    g.fillEllipse(in: CGRect(x: x - radius, y: y + dy - radius, width: radius * 2, height: radius * 2))
                }
                dot(2 * px, 4.5 * px, UIColor(red: 40 / 255, green: 80 / 255, blue: 20 / 255, alpha: 0.25))
                dot(0, 4.5 * px, UIColor(dioramaHex: MultiVanDioramaScenery.flowerColors[color]))
                dot(0, 1.6 * px, UIColor(dioramaHex: 0xF3B437))
            }
        }
    }

    // MARK: - Roads

    private static func roadLayer(graph: RuntimeRouteGraph, features: Features, layout: BoardLayout) -> UIImage {
        UIGraphicsImageRenderer(size: imageSize, format: textureFormat(opaque: false)).image { context in
            let g = context.cgContext
            let unit = pixelsPerUnit
            let network = CGMutablePath()
            for edge in graph.edgesByID.values.sorted(by: { $0.id < $1.id }) {
                network.addPath(RoadPathRenderer.path(for: edge, layout: layout).cgPath)
            }
            let pixel = { (point: RoadPoint) in layout.point(for: point) ?? .zero }
            func strokeNetwork(width: Double, color: UIColor, plazaRadius: Double) {
                g.addPath(network)
                g.setLineCap(.round)
                g.setLineJoin(.round)
                g.setLineWidth(width * unit)
                g.setStrokeColor(color.cgColor)
                g.strokePath()
                g.setFillColor(color.cgColor)
                for plaza in features.plazas {
                    let centre = pixel(plaza), radius = plazaRadius * unit
                    g.fillEllipse(in: CGRect(x: centre.x - radius, y: centre.y - radius, width: radius * 2, height: radius * 2))
                }
            }

            strokeNetwork(width: Measure.curbWidth, color: Palette.curb, plazaRadius: Measure.plazaRadii.curb)
            // Driveways run on from the curb to each front door, under the road's end.
            let driveways = CGMutablePath()
            for driveway in features.houses.map(\.marking) {
                let start = pixel(driveway.point), heading = textureDirection(driveway.heading)
                driveways.move(to: start)
                driveways.addLine(to: CGPoint(
                    x: start.x + heading.dx * Measure.drivewayLength * unit,
                    y: start.y + heading.dy * Measure.drivewayLength * unit
                ))
            }
            g.addPath(driveways)
            g.setLineWidth(Measure.drivewayWidth * unit)
            g.setStrokeColor(Palette.driveway.cgColor)
            g.strokePath()
            strokeNetwork(width: Measure.edgeLineWidth, color: Palette.edgeLine, plazaRadius: Measure.plazaRadii.edgeLine)
            strokeNetwork(width: Measure.asphaltWidth, color: Palette.asphalt, plazaRadius: Measure.plazaRadii.asphalt)

            for depot in features.depots {
                drawRotated(g, at: pixel(depot.point), heading: depot.heading) { drawDepot(g, colors: depot.colors) }
            }
            for barrier in features.barriers {
                drawRotated(g, at: pixel(barrier.point), heading: barrier.heading) { drawHatching(g) }
            }
            // Grain only where there is paint.
            addGrain(g, alpha: 0.16, blendMode: .sourceAtop)
        }
    }

    /// A parking bay under a waiting van, nose along `heading`, with a stripe at its
    /// back in each waiting van's colour.
    private static func drawDepot(_ g: CGContext, colors: [VanColor]) {
        let unit = pixelsPerUnit
        g.setFillColor(Palette.bay.cgColor)
        g.addPath(CGPath(
            roundedRect: CGRect(x: -0.36 * unit, y: -0.2 * unit, width: 0.62 * unit, height: 0.4 * unit),
            cornerWidth: 0.055 * unit, cornerHeight: 0.055 * unit, transform: nil
        ))
        g.fillPath()
        let inner = CGRect(x: -0.34 * unit, y: -0.18 * unit, width: 0.58 * unit, height: 0.36 * unit)
        g.addPath(CGPath(roundedRect: inner, cornerWidth: 0.044 * unit, cornerHeight: 0.044 * unit, transform: nil))
        g.setStrokeColor(Palette.edgeLine.cgColor)
        g.setLineWidth(3 * px)
        g.setLineDash(phase: 0, lengths: [9 * px, 7 * px])
        g.strokePath()
        g.setLineDash(phase: 0, lengths: [])
        let share = inner.height / CGFloat(max(colors.count, 1))
        for (index, color) in colors.enumerated() {
            g.setFillColor(color.dioramaBody.cgColor)
            g.fill(CGRect(x: inner.minX, y: inner.minY + share * CGFloat(index), width: 0.07 * unit, height: share))
        }
    }

    /// Stop hatching on the road where a barrier closes it.
    private static func drawHatching(_ g: CGContext) {
        let unit = pixelsPerUnit
        g.setFillColor(Palette.edgeLine.cgColor)
        for index in -2...2 {
            g.fill(CGRect(x: -0.06 * unit, y: CGFloat(index) * 0.055 * unit - 3 * px, width: 0.12 * unit, height: 6 * px))
        }
    }

    // MARK: - Helpers

    /// A grid direction as a unit vector in texture space, where y runs down the board.
    private static func textureDirection(_ heading: RoadVector) -> CGVector {
        let length = hypot(heading.x, heading.y)
        guard length.isFinite, length > 1e-9 else { return CGVector(dx: 0, dy: -1) }
        return CGVector(dx: heading.x / length, dy: -heading.y / length)
    }

    /// Runs `draw` with x along `heading` and the origin at `point`.
    private static func drawRotated(_ g: CGContext, at point: CGPoint, heading: RoadVector, draw: () -> Void) {
        let direction = textureDirection(heading)
        g.saveGState()
        g.translateBy(x: point.x, y: point.y)
        g.rotate(by: atan2(direction.dy, direction.dx))
        draw()
        g.restoreGState()
    }

    /// One texel per pixel, 8-bit sRGB: a wide-colour format would double the texture.
    static func textureFormat(opaque: Bool) -> UIGraphicsImageRendererFormat {
        let format = UIGraphicsImageRendererFormat()
        format.scale = 1
        format.opaque = opaque
        format.preferredRange = .standard
        return format
    }

    static func addGrain(_ g: CGContext, alpha: CGFloat, blendMode: CGBlendMode = .normal) {
        g.saveGState()
        g.setBlendMode(blendMode)
        g.setAlpha(alpha)
        g.draw(grainTile, in: CGRect(x: 0, y: 0, width: grainTile.width, height: grainTile.height), byTiling: true)
        g.restoreGState()
    }

    /// Mid-grey paper noise with a few fibres, shared by every printed surface.
    private static let grainTile: CGImage = {
        let side = 160
        var random = MultiVanDioramaRandom(seed: 7)
        let image = UIGraphicsImageRenderer(size: CGSize(width: side, height: side), format: textureFormat(opaque: true)).image { context in
            let g = context.cgContext
            for y in 0..<side {
                for x in 0..<side {
                    g.setFillColor(gray: (128 + (random.next() - 0.5) * 120) / 255, alpha: 1)
                    g.fill(CGRect(x: x, y: y, width: 1, height: 1))
                }
            }
            g.setStrokeColor(UIColor(white: 1, alpha: 0.35).cgColor)
            g.setLineWidth(0.7)
            for _ in 0..<40 {
                let x = random.next() * Double(side), y = random.next() * Double(side)
                // The prototype's draw order: control point, then end.
                let control = CGPoint(x: x + random.next() * 14 - 7, y: y + random.next() * 14 - 7)
                let end = CGPoint(x: x + random.next() * 20 - 10, y: y + random.next() * 20 - 10)
                g.move(to: CGPoint(x: x, y: y))
                g.addQuadCurve(to: end, control: control)
                g.strokePath()
            }
        }
        return image.cgImage!
    }()
}
