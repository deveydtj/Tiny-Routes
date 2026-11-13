import UIKit

/// The level map's lawn, painted once: the gameplay table's mown grass and paper
/// grain, the scenery's contact shadows, flower beds and pond banks, and the road
/// winding up it with a dashed middle line. The slab lays it over its top face,
/// far edge at the top of the image.
enum TRLevelMapLawn {
    /// A wider road than the gameplay table's, to carry the van between tiles.
    enum Measure {
        static let curbWidth = 0.72
        static let edgeLineWidth = 0.56
        static let asphaltWidth = 0.5
        static let dashWidth = 0.035
        static let dash = (on: 0.16, off: 0.14)
    }

    /// Texture pixels per unit, fewer on long maps so the image stays in bounds.
    static func pixelsPerUnit(for layout: TRLevelMapLayout) -> CGFloat {
        min(150, 4096 / CGFloat(max(layout.depth, TRLevelMapLayout.width)))
    }

    static func image(layout: TRLevelMapLayout, scenery: TRLevelMapScenery, pixelsPerUnit: CGFloat? = nil) -> UIImage {
        let unit = pixelsPerUnit ?? Self.pixelsPerUnit(for: layout)
        let size = CGSize(
            width: (TRLevelMapLayout.width * unit).rounded(),
            height: (layout.depth * unit).rounded()
        )
        let texture = { (point: RoadPoint) in
            CGPoint(x: (point.x + TRLevelMapLayout.width / 2) * unit, y: (layout.depth - point.y) * unit)
        }
        var random = MultiVanDioramaRandom(seed: 43)
        return UIGraphicsImageRenderer(size: size, format: MultiVanDioramaLawn.textureFormat(opaque: true)).image { context in
            let g = context.cgContext
            paintGrass(g, size: size, unit: unit, random: &random)
            paintScenery(g, scenery: scenery, unit: unit, texture: texture)
            paintRoad(g, layout: layout, unit: unit, texture: texture)
            MultiVanDioramaLawn.addGrain(g, alpha: 0.5, blendMode: .multiply)
        }
    }

    // MARK: - Grass

    private static func paintGrass(_ g: CGContext, size: CGSize, unit: CGFloat, random: inout MultiVanDioramaRandom) {
        g.setFillColor(MultiVanDioramaLawn.Palette.lawn.cgColor)
        g.fill(CGRect(origin: .zero, size: size))
        // Mowing stripes across the island.
        let stripe = unit / 2
        for (index, y) in stride(from: 0, to: size.height, by: stripe).enumerated() {
            g.setFillColor(index.isMultiple(of: 2)
                ? UIColor(red: 40 / 255, green: 80 / 255, blue: 20 / 255, alpha: 0.035).cgColor
                : UIColor(white: 1, alpha: 0.05).cgColor)
            g.fill(CGRect(x: 0, y: y, width: size.width, height: stripe))
        }
        let px = unit / 180
        let speckles = [0x7FB85A, 0x9FD474, 0x86C060, 0xA9DA7F].map { UIColor(dioramaHex: $0) }
        let count = Int(size.width * size.height / 70)
        for index in 0..<count {
            let alpha = 0.35 + random.next() * 0.4
            let x = random.next() * size.width, y = random.next() * size.height
            let radius = (0.8 + random.next() * 2.2) * px
            g.setFillColor(speckles[index % 4].withAlphaComponent(alpha).cgColor)
            g.fillEllipse(in: CGRect(x: x - radius, y: y - radius, width: radius * 2, height: radius * 2))
        }
    }

    // MARK: - Scenery

    private static func paintScenery(
        _ g: CGContext, scenery: TRLevelMapScenery, unit: CGFloat, texture: (RoadPoint) -> CGPoint
    ) {
        func shade(_ point: RoadPoint, radius: Double, alpha: CGFloat) {
            let centre = texture(point)
            let r = CGFloat(radius) * unit
            let colors = [UIColor(white: 0, alpha: alpha).cgColor, UIColor(white: 0, alpha: 0).cgColor] as CFArray
            let gradient = CGGradient(colorsSpace: nil, colors: colors, locations: [0, 1])!
            g.saveGState()
            // Squashed along the lens's line of sight, like a shadow lying on grass.
            g.translateBy(x: centre.x, y: centre.y)
            g.scaleBy(x: 1, y: 0.7)
            g.drawRadialGradient(gradient, startCenter: .zero, startRadius: 0, endCenter: .zero, endRadius: r, options: [])
            g.restoreGState()
        }

        for item in scenery.items {
            switch item.kind {
            case .tree: shade(item.point, radius: item.height * 0.42, alpha: 0.28)
            case .bush: shade(item.point, radius: item.height * 0.9, alpha: 0.22)
            case let .flowers(color):
                let centre = texture(item.point)
                var random = MultiVanDioramaRandom(seed: UInt32(abs(Int(item.point.x * 997 + item.point.y * 131))) % 10_000 + 1)
                for _ in 0..<6 {
                    let x = centre.x + (random.next() - 0.5) * 0.19 * unit
                    let y = centre.y + (random.next() - 0.5) * 0.15 * unit
                    let r = (0.018 + random.next() * 0.012) * unit
                    g.setFillColor(UIColor(dioramaHex: MultiVanDioramaScenery.flowerColors[color]).cgColor)
                    g.fillEllipse(in: CGRect(x: x - r, y: y - r, width: r * 2, height: r * 2))
                }
            case .resident:
                break
            }
        }
        for house in scenery.houses {
            shade(house.point, radius: 0.55, alpha: 0.3)
        }
        for pond in scenery.ponds {
            let centre = texture(pond.centre)
            g.saveGState()
            g.translateBy(x: centre.x, y: centre.y)
            // Texture y runs down the island, so an anticlockwise turn is negative here.
            g.rotate(by: -CGFloat(pond.angle))
            let bank = CGRect(x: -pond.radiusX - 0.09, y: -pond.radiusY - 0.08, width: (pond.radiusX + 0.09) * 2, height: (pond.radiusY + 0.08) * 2)
            let water = CGRect(x: -pond.radiusX, y: -pond.radiusY, width: pond.radiusX * 2, height: pond.radiusY * 2)
            g.scaleBy(x: unit, y: unit)
            g.setFillColor(UIColor(dioramaHex: 0xE9DDBF).cgColor)
            g.fillEllipse(in: bank)
            g.setFillColor(UIColor(dioramaHex: 0x5FB8DD).cgColor)
            g.fillEllipse(in: water)
            g.setFillColor(UIColor(dioramaHex: 0x8BD0EC).cgColor)
            g.fillEllipse(in: water.insetBy(dx: pond.radiusX * 0.18, dy: pond.radiusY * 0.22))
            g.restoreGState()
        }
    }

    // MARK: - Road

    private static func paintRoad(
        _ g: CGContext, layout: TRLevelMapLayout, unit: CGFloat, texture: (RoadPoint) -> CGPoint
    ) {
        // Off both ends of the island, so the road runs on past its edges.
        let samples = layout.roadSamples(fromY: -0.5, toY: layout.depth + 0.5, spacing: 0.04)
        let path = CGMutablePath()
        path.addLines(between: samples.map(texture))
        g.setLineCap(.round)
        g.setLineJoin(.round)

        // The curb casts a soft shadow onto the lawn.
        g.saveGState()
        g.setShadow(offset: CGSize(width: 0, height: 0.03 * unit), blur: 0.08 * unit, color: UIColor(white: 0, alpha: 0.28).cgColor)
        stroke(g, path, width: Measure.curbWidth * unit, color: MultiVanDioramaLawn.Palette.curb)
        g.restoreGState()
        stroke(g, path, width: Measure.edgeLineWidth * unit, color: MultiVanDioramaLawn.Palette.edgeLine)
        stroke(g, path, width: Measure.asphaltWidth * unit, color: MultiVanDioramaLawn.Palette.asphalt)

        g.saveGState()
        g.setLineCap(.butt)
        g.setLineDash(phase: 0, lengths: [Measure.dash.on * unit, Measure.dash.off * unit])
        stroke(g, path, width: Measure.dashWidth * unit, color: UIColor.white.withAlphaComponent(0.85))
        g.restoreGState()
    }

    private static func stroke(_ g: CGContext, _ path: CGPath, width: CGFloat, color: UIColor) {
        g.addPath(path)
        g.setLineWidth(width)
        g.setStrokeColor(color.cgColor)
        g.strokePath()
    }
}
