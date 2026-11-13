import SwiftUI

extension Color {
    /// A colour from a 0xRRGGBB literal, as the village design names them.
    init(hex: UInt32, opacity: Double = 1) {
        self.init(
            .sRGB,
            red: Double((hex >> 16) & 0xFF) / 255,
            green: Double((hex >> 8) & 0xFF) / 255,
            blue: Double(hex & 0xFF) / 255,
            opacity: opacity
        )
    }
}

/// The village level map's colours.
enum TRVillagePalette {
    static let ink = Color(hex: 0x1A3329)
    static let teal = Color(hex: 0x215C61)
    static let tealDark = Color(hex: 0x174A4F)
    static let cream = Color(hex: 0xFEF9EE)
    static let creamDeep = Color(hex: 0xF6EEDD)
    static let creamLip = Color(hex: 0xD6C9AD)
    static let navy = Color(hex: 0x0D2E6E)
    static let slate = Color(hex: 0x576B8C)
    static let blue = Color(hex: 0x1480F5)
    static let blueDark = Color(hex: 0x0E5DB8)
    static let gold = Color(hex: 0xFFC22E)
    static let mint = Color(hex: 0xBFE0C9)
    static let roofs = [Color(hex: 0xEC5B4B), Color(hex: 0xF6C234), Color(hex: 0x4A86E8), Color(hex: 0x4CB862)]
    static let greens = [Color(hex: 0x6BB361), Color(hex: 0x8CCC6B), Color(hex: 0x30804F), Color(hex: 0x216642)]
}

/// The sky behind the village: blue at the top, fading to a pale mint.
struct TRVillageSky: View {
    var body: some View {
        LinearGradient(
            stops: [
                .init(color: Color(hex: 0x9ED1F2), location: 0),
                .init(color: Color(hex: 0xCCE8F7), location: 0.35),
                .init(color: Color(hex: 0xE6F5F2), location: 1),
            ],
            startPoint: .top,
            endPoint: .bottom
        )
        .ignoresSafeArea()
        .accessibilityHidden(true)
    }
}

/// The tilted board the village stands on, in page points. Across, the design's
/// 390 pt scale to the page's width; down, its top stays under the banner and its
/// lip above the controls, the face stretching between.
struct TRVillageBoard {
    /// Where the banner's straight sides end.
    static let bannerEdge = 50.0
    static let top = 104.0

    let scaleX: Double
    let lip: Double

    init(width: Double, height: Double) {
        scaleX = width / 390
        lip = max(height - 144, Self.top + 240)
    }

    var top: Double { Self.top }

    /// A design y on the board's face.
    func faceY(_ y: Double) -> Double { top + (y - 150) * (lip - top) / 490 }
    /// A design y above the board, kept its distance from the board's top.
    func aboveY(_ y: Double) -> Double { y - 150 + top }
    /// A design y below the lip, kept its distance from it.
    func belowY(_ y: Double) -> Double { y - 640 + lip }

    func point(_ x: Double, _ y: Double) -> CGPoint { CGPoint(x: x * scaleX, y: y) }

    /// The board's grassy top, narrowing towards the far edge.
    var face: Path {
        var path = Path()
        path.move(to: point(66, top))
        path.addLine(to: point(324, top))
        path.addQuadCurve(to: point(344, top + 18), control: point(342, top))
        path.addLine(to: point(370, lip - 22))
        path.addQuadCurve(to: point(350, lip), control: point(372, lip))
        path.addLine(to: point(40, lip))
        path.addQuadCurve(to: point(20, lip - 22), control: point(18, lip))
        path.addLine(to: point(46, top + 18))
        path.addQuadCurve(to: point(66, top), control: point(48, top))
        path.closeSubpath()
        return path
    }

    /// A layer of the board's side below the lip, from its sides' foot round its bottom.
    fileprivate func side(footLeft: Double, footY: Double, curveLeft: Double, bottom: Double, curveRight: Double, footRight: Double) -> Path {
        var path = Path()
        path.move(to: point(20, belowY(618)))
        path.addLine(to: point(footLeft, belowY(footY)))
        path.addQuadCurve(to: point(40, belowY(bottom)), control: point(curveLeft, belowY(bottom)))
        path.addLine(to: point(350, belowY(bottom)))
        path.addQuadCurve(to: point(footRight, belowY(footY)), control: point(curveRight, belowY(bottom)))
        path.addLine(to: point(370, belowY(618)))
        path.closeSubpath()
        return path
    }
}

/// The board's outline, to clip the world to.
struct TRVillageBoardShape: Shape {
    let board: TRVillageBoard

    func path(in rect: CGRect) -> Path { board.face }
}

// MARK: - Drawing

/// The village's pieces, drawn in a `Canvas` in the design's own units.
enum TRVillageArt {
    // MARK: Shapes

    static func circle(_ x: Double, _ y: Double, _ r: Double) -> Path {
        Path(ellipseIn: CGRect(x: x - r, y: y - r, width: r * 2, height: r * 2))
    }

    static func ellipse(_ x: Double, _ y: Double, _ rx: Double, _ ry: Double) -> Path {
        Path(ellipseIn: CGRect(x: x - rx, y: y - ry, width: rx * 2, height: ry * 2))
    }

    static func rect(_ x: Double, _ y: Double, _ w: Double, _ h: Double, radius: Double = 0) -> Path {
        let rect = CGRect(x: x, y: y, width: w, height: h)
        return radius > 0 ? Path(roundedRect: rect, cornerRadius: radius) : Path(rect)
    }

    static func polygon(_ points: Double...) -> Path {
        var path = Path()
        for i in stride(from: 0, to: points.count - 1, by: 2) {
            let point = CGPoint(x: points[i], y: points[i + 1])
            if i == 0 { path.move(to: point) } else { path.addLine(to: point) }
        }
        path.closeSubpath()
        return path
    }

    // MARK: Placing

    /// Draws a piece with its foot `anchor` (in its own units) at `point`, scaled,
    /// tilted about its foot, and faded as one.
    static func place(_ context: GraphicsContext, at point: CGPoint, scale: Double, anchor: CGPoint, rotation: Angle = .zero, opacity: Double, draw: (GraphicsContext) -> Void) {
        guard opacity > 0.001 else { return }
        var context = context
        context.translateBy(x: point.x, y: point.y)
        context.scaleBy(x: scale, y: scale)
        context.rotate(by: rotation)
        context.translateBy(x: -anchor.x, y: -anchor.y)
        if opacity < 0.999 {
            context.opacity = opacity
            context.drawLayer { draw($0) }
        } else {
            draw(context)
        }
    }

    // MARK: Backdrop

    /// The sun, clouds and hills behind the board, then the board itself. `time`
    /// drifts the clouds and breathes the sun's glow.
    static func drawBackdrop(_ context: GraphicsContext, board: TRVillageBoard, time: Double) {
        let k = board.scaleX
        var blurred = context
        blurred.addFilter(.blur(radius: 8))

        let glow = 70 * (1 + 0.05 * sin(time * 0.9))
        blurred.fill(circle(70 * k, board.aboveY(180), glow * k), with: .color(Color(hex: 0xFFF0D6, opacity: 0.6)))
        context.fill(circle(70 * k, board.aboveY(178), 22 * k), with: .color(Color(hex: 0xFFF6DE)))
        drawCloud(context, at: board.point(250 + 7 * sin(time * 0.16), board.aboveY(122)), width: 110 * k, opacity: 0.9)
        drawCloud(context, at: board.point(132 + 5 * sin(time * 0.21 + 2), board.aboveY(128)), width: 64 * k, opacity: 0.8)

        // Two rows of hills, peeking out beside the board.
        var back = Path()
        back.move(to: board.point(-10, board.aboveY(200)))
        back.addCurve(to: board.point(140, board.aboveY(190)), control1: board.point(40, board.aboveY(170)), control2: board.point(90, board.aboveY(175)))
        back.addCurve(to: board.point(290, board.aboveY(172)), control1: board.point(190, board.aboveY(205)), control2: board.point(230, board.aboveY(160)))
        back.addCurve(to: board.point(400, board.aboveY(180)), control1: board.point(350, board.aboveY(184)), control2: board.point(370, board.aboveY(190)))
        back.addLine(to: board.point(400, board.aboveY(260)))
        back.addLine(to: board.point(-10, board.aboveY(260)))
        back.closeSubpath()
        context.fill(back, with: .color(Color(hex: 0xA9D49C)))
        var front = Path()
        front.move(to: board.point(-10, board.aboveY(222)))
        front.addCurve(to: board.point(170, board.aboveY(215)), control1: board.point(60, board.aboveY(200)), control2: board.point(120, board.aboveY(205)))
        front.addCurve(to: board.point(330, board.aboveY(200)), control1: board.point(220, board.aboveY(225)), control2: board.point(280, board.aboveY(192)))
        front.addCurve(to: board.point(400, board.aboveY(206)), control1: board.point(380, board.aboveY(208)), control2: board.point(380, board.aboveY(212)))
        front.addLine(to: board.point(400, board.aboveY(280)))
        front.addLine(to: board.point(-10, board.aboveY(280)))
        front.closeSubpath()
        context.fill(front, with: .color(Color(hex: 0x8CC47F)))

        // The board's shadow and its earthy sides, then the lawn on top.
        blurred.fill(ellipse(195 * k, board.belowY(694), 170 * k, 16), with: .color(TRVillagePalette.ink.opacity(0.22)))
        context.fill(board.side(footLeft: 18, footY: 658, curveLeft: 18, bottom: 680, curveRight: 372, footRight: 372), with: .color(Color(hex: 0x7B5339)))
        context.fill(board.side(footLeft: 19, footY: 646, curveLeft: 20, bottom: 664, curveRight: 370, footRight: 371), with: .color(Color(hex: 0xA26E48)))
        context.fill(board.side(footLeft: 19.6, footY: 630, curveLeft: 21, bottom: 648, curveRight: 369, footRight: 370.4), with: .color(Color(hex: 0x7DB457)))
        var pebbles = Path()
        for (x, y, r) in [(60.0, 660.0, 1.4), (96, 671, 1.8), (150, 657, 1.2), (204, 668, 1.6), (250, 659, 1.3), (300, 672, 1.7), (338, 658, 1.2)] {
            pebbles.addPath(circle(x * k, board.belowY(y), r))
        }
        context.fill(pebbles, with: .color(Color(hex: 0x5E3E2A, opacity: 0.35)))

        let face = board.face
        context.fill(face, with: .color(Color(hex: 0x8FC766)))

        // Soft light across the lawn: sunbeams, a warm glow by the sun, shade far right.
        var lit = context
        lit.clip(to: face)
        var beams = Path()
        for beam in [[40.0, 200, 60, 640, 100, 640, 82, 150], [160, 150, 150, 640, 200, 640, 200, 150], [280, 150, 300, 640, 340, 640, 312, 150]] {
            beams.addPath(polygon(
                beam[0] * k, board.faceY(beam[1]), beam[2] * k, board.faceY(beam[3]),
                beam[4] * k, board.faceY(beam[5]), beam[6] * k, board.faceY(beam[7])
            ))
        }
        lit.fill(beams, with: .color(.white.opacity(0.14)))
        let squash = (board.lip - board.top) / 490
        lit.addFilter(.blur(radius: 8))
        lit.fill(ellipse(70 * k, board.faceY(260), 200 * k, 170 * squash), with: .color(Color(hex: 0xFFF0D6, opacity: 0.28)))
        lit.fill(ellipse(340 * k, board.faceY(600), 190 * k, 130 * squash), with: .color(TRVillagePalette.ink.opacity(0.08)))
    }

    /// The clouds that drift under the board's front corners.
    static func drawLowClouds(_ context: GraphicsContext, board: TRVillageBoard, time: Double) {
        drawCloud(context, at: board.point(4 * sin(time * 0.19 + 1), board.belowY(672)), width: 120 * board.scaleX, opacity: 0.95)
        drawCloud(context, at: board.point(272 + 4 * sin(time * 0.17 + 4), board.belowY(676)), width: 124 * board.scaleX, opacity: 0.95)
    }

    /// How far through its loop something repeating every `period` seconds is.
    static func phase(_ time: Double, every period: Double) -> Double {
        let cycles = time / period
        return cycles - cycles.rounded(.down)
    }

    /// A puffy cloud `width` wide with its top left at `point`.
    static func drawCloud(_ context: GraphicsContext, at point: CGPoint, width: Double, opacity: Double) {
        var context = context
        context.opacity = opacity
        context.translateBy(x: point.x, y: point.y)
        context.scaleBy(x: width / 100, y: width / 100)
        var cloud = Path()
        cloud.addPath(circle(26, 26, 16))
        cloud.addPath(circle(52, 18, 22))
        cloud.addPath(circle(76, 27, 15))
        cloud.addPath(rect(8, 24, 84, 18, radius: 9))
        context.fill(cloud, with: .color(.white))
    }

    // MARK: Pieces

    static let houseAnchor = CGPoint(x: 24, y: 54)
    static let treeAnchor = CGPoint(x: 15, y: 43)
    static let flowersAnchor = CGPoint(x: 10, y: 6)
    static let pondAnchor = CGPoint(x: 36, y: 13)
    static let bushAnchor = CGPoint(x: 15, y: 16)
    static let rockAnchor = CGPoint(x: 8, y: 9)
    static let signAnchor = CGPoint(x: 15, y: 39)
    /// The van turns and flips about a point just above its wheels' foot.
    static let vanPivot = CGPoint(x: 20, y: 23.2)

    /// A cottage: chimney smoking once its delivery's done, a parcel on the step
    /// while it waits, and a flag on the depot. `time` sends the smoke up, hops
    /// the parcel now and then, and flaps the flag; `wind` bends the smoke over.
    static func drawHouse(_ context: GraphicsContext, roof: Color, smoke: Bool, parcel: Bool, flag: Bool, wind: Double = 0, time: Double) {
        let ink = TRVillagePalette.ink
        context.fill(ellipse(25, 54, 24, 4.5), with: .color(ink.opacity(0.18)))
        context.fill(polygon(36, 54, 46, 48, 46, 27, 36, 33), with: .color(Color(hex: 0xDCCFB6)))
        context.fill(rect(2, 33, 34, 21), with: .color(Color(hex: 0xF3E8D3)))
        context.fill(polygon(2, 33, 36, 33, 19, 16), with: .color(Color(hex: 0xF6ECD8)))
        let slope = polygon(19, 16, 36, 33, 46, 27, 29, 10)
        context.fill(slope, with: .color(roof))
        context.fill(slope, with: .color(ink.opacity(0.16)))
        context.stroke(eave, with: .color(roof), style: StrokeStyle(lineWidth: 3.2, lineCap: .round, lineJoin: .round))
        context.fill(rect(33, 11, 5, 10), with: .color(Color(hex: 0xB9A58A)))
        context.fill(rect(15, 42, 8, 12, radius: 1.5), with: .color(Color(hex: 0x5D5A6E)))
        let glass = Color(hex: 0x8CC3E0)
        context.fill(rect(5, 38, 6, 6, radius: 1), with: .color(glass))
        context.fill(rect(26, 38, 6, 6, radius: 1), with: .color(glass))
        context.fill(polygon(39, 41, 43, 38.6, 43, 43, 39, 45.4), with: .color(glass))
        var glints = rect(5.8, 38.8, 2, 2)
        glints.addPath(rect(26.8, 38.8, 2, 2))
        context.fill(glints, with: .color(.white.opacity(0.8)))
        if smoke { drawSmoke(context, wind: wind, time: time) }
        if parcel {
            // A hop every couple of seconds, waiting to be delivered.
            let beat = phase(time, every: 2.4)
            let hop = beat < 0.18 ? sin(beat / 0.18 * .pi) * 2.2 : 0
            context.fill(rect(25, 48 - hop, 7, 6, radius: 1), with: .color(Color(hex: 0xC99A63)))
            context.fill(rect(28, 48 - hop, 1.4, 6), with: .color(Color(hex: 0xE9D9B5)))
        }
        if flag {
            context.fill(rect(-3, 20, 1.6, 34), with: .color(Color(hex: 0x8A6244)))
            // A ripple runs out along the flag from the pole.
            func wave(_ x: Double) -> Double { sin(time * 4 - x * 0.45) * 0.9 * (x + 1.4) / 11.4 }
            var cloth = Path()
            cloth.move(to: CGPoint(x: -1.4, y: 20))
            for x in [3.0, 7, 10] { cloth.addLine(to: CGPoint(x: x, y: 20 + wave(x))) }
            cloth.addLine(to: CGPoint(x: 7, y: 24 + wave(7)))
            for x in [10.0, 7, 3] { cloth.addLine(to: CGPoint(x: x, y: 28 + wave(x))) }
            cloth.addLine(to: CGPoint(x: -1.4, y: 28))
            cloth.closeSubpath()
            context.fill(cloth, with: .color(Color(hex: 0xEC5B4B)))
        }
    }

    /// A cottage's chimney smoke on its own, in the cottage's units: three puffs
    /// in turn, each swelling and thinning as it drifts up.
    static func drawSmoke(_ context: GraphicsContext, wind: Double = 0, time: Double) {
        for puff in 0..<3 {
            let p = phase(time + Double(puff) * 0.9, every: 2.7)
            let opacity = 0.75 * min(1, p / 0.15) * (1 - p)
            let x = 35.5 + (4 + 16 * wind) * p + sin(p * .pi * 2) * 1.2
            context.fill(circle(x, 7 - 17 * p, 2.2 + 2.4 * p), with: .color(.white.opacity(opacity)))
        }
    }

    /// A house still to be reached, pale and unpainted.
    static func drawEmptyHouse(_ context: GraphicsContext) {
        context.fill(ellipse(25, 54, 24, 4.5), with: .color(TRVillagePalette.ink.opacity(0.12)))
        context.fill(polygon(36, 54, 46, 48, 46, 27, 36, 33), with: .color(Color(hex: 0xE2D8C4)))
        context.fill(rect(2, 33, 34, 21), with: .color(Color(hex: 0xF4ECDC)))
        context.fill(polygon(2, 33, 36, 33, 19, 16), with: .color(Color(hex: 0xF7F0E2)))
        context.fill(polygon(19, 16, 36, 33, 46, 27, 29, 10), with: .color(TRVillagePalette.creamLip))
        let trim = Color(hex: 0xCDBF9F)
        context.stroke(eave, with: .color(trim), style: StrokeStyle(lineWidth: 3, lineCap: .round, lineJoin: .round))
        context.fill(rect(15, 42, 8, 12, radius: 1.5), with: .color(trim))
        context.fill(rect(5, 38, 6, 6, radius: 1), with: .color(TRVillagePalette.creamLip))
        context.fill(rect(26, 38, 6, 6, radius: 1), with: .color(TRVillagePalette.creamLip))
    }

    private static var eave: Path {
        var path = Path()
        path.move(to: CGPoint(x: 0, y: 34.5))
        path.addLine(to: CGPoint(x: 19, y: 15))
        path.addLine(to: CGPoint(x: 38, y: 34.5))
        return path
    }

    static func drawTree(_ context: GraphicsContext, color: Color) {
        let ink = TRVillagePalette.ink
        context.fill(ellipse(16, 43, 14, 3.5), with: .color(ink.opacity(0.18)))
        context.fill(rect(13.5, 26, 3, 17, radius: 1), with: .color(Color(hex: 0x8A6244)))
        context.fill(circle(15, 16, 14), with: .color(color))
        var shade = Path()
        shade.addArc(center: CGPoint(x: 15, y: 16), radius: 14, startAngle: .degrees(-90), endAngle: .degrees(90), clockwise: false)
        shade.closeSubpath()
        context.fill(shade, with: .color(ink.opacity(0.16)))
        context.fill(circle(10, 11, 4), with: .color(.white.opacity(0.18)))
    }

    static func drawPine(_ context: GraphicsContext, color: Color) {
        let ink = TRVillagePalette.ink
        context.fill(ellipse(16, 43, 12, 3), with: .color(ink.opacity(0.18)))
        context.fill(rect(13.5, 34, 3, 9, radius: 1), with: .color(Color(hex: 0x8A6244)))
        context.fill(polygon(15, 1, 28, 35, 2, 35), with: .color(color))
        context.fill(polygon(15, 1, 28, 35, 15, 35), with: .color(ink.opacity(0.2)))
    }

    /// A low round bush of three clumps.
    static func drawBush(_ context: GraphicsContext, color: Color) {
        let ink = TRVillagePalette.ink
        context.fill(ellipse(15, 16, 14, 3), with: .color(ink.opacity(0.18)))
        var clumps = circle(8, 10.5, 6.5)
        clumps.addPath(circle(15, 7.5, 7.5))
        clumps.addPath(circle(22, 11, 6))
        clumps.addPath(rect(3, 10, 24, 6, radius: 3))
        context.fill(clumps, with: .color(color))
        var shade = circle(22, 11, 6)
        shade.addPath(rect(15, 12, 12, 4, radius: 2))
        context.fill(shade, with: .color(ink.opacity(0.14)))
        context.fill(circle(12, 5, 2.6), with: .color(.white.opacity(0.2)))
    }

    /// A grey boulder.
    static func drawRock(_ context: GraphicsContext) {
        context.fill(ellipse(8.5, 9, 8.5, 2.2), with: .color(TRVillagePalette.ink.opacity(0.18)))
        context.fill(ellipse(8, 5.6, 7.5, 5), with: .color(Color(hex: 0xA3ACB0)))
        context.fill(ellipse(10, 7.6, 5.5, 2.6), with: .color(TRVillagePalette.ink.opacity(0.12)))
        context.fill(ellipse(5.6, 3.6, 2.8, 1.5), with: .color(.white.opacity(0.4)))
    }

    static func drawFlowers(_ context: GraphicsContext) {
        let yellow = Color(hex: 0xF6C234)
        context.fill(circle(4, 5, 2), with: .color(.white))
        context.fill(circle(10, 7, 2), with: .color(.white))
        context.fill(circle(7, 3, 2), with: .color(yellow))
        context.fill(circle(15, 4, 1.8), with: .color(Color(hex: 0xEC5B4B, opacity: 0.85)))
        context.fill(circle(16, 8, 1.8), with: .color(yellow))
    }

    /// A pond, its ripples shifting and glinting with `time`.
    static func drawPond(_ context: GraphicsContext, time: Double) {
        context.fill(ellipse(36, 13, 36, 13), with: .color(Color(hex: 0x5A9CC4)))
        context.fill(ellipse(36, 11, 33, 10.5), with: .color(Color(hex: 0x8CC3E0)))
        let drift = sin(time * 0.9) * 3
        var ripple = Path()
        ripple.move(to: CGPoint(x: 16 + drift, y: 10))
        ripple.addQuadCurve(to: CGPoint(x: 48 + drift, y: 9), control: CGPoint(x: 30 + drift, y: 5))
        context.stroke(ripple, with: .color(.white.opacity(0.6 + 0.25 * sin(time * 1.8))), style: StrokeStyle(lineWidth: 2, lineCap: .round))
        var small = Path()
        small.move(to: CGPoint(x: 30 - drift, y: 15.5))
        small.addQuadCurve(to: CGPoint(x: 46 - drift, y: 15), control: CGPoint(x: 38 - drift, y: 12.5))
        context.stroke(small, with: .color(.white.opacity(0.4 + 0.3 * sin(time * 1.8 + 2))), style: StrokeStyle(lineWidth: 1.5, lineCap: .round))
    }

    /// A signpost by the road, naming the chapter that starts there.
    static func drawSign(_ context: GraphicsContext, label: String) {
        context.fill(ellipse(15, 39, 9, 2.5), with: .color(TRVillagePalette.ink.opacity(0.2)))
        context.fill(rect(13.5, 14, 3, 25, radius: 1), with: .color(Color(hex: 0x8A6244)))
        let board = rect(1, 2, 28, 15, radius: 3.5)
        context.fill(board, with: .color(TRVillagePalette.teal))
        context.stroke(board, with: .color(TRVillagePalette.tealDark), lineWidth: 1.2)
        let text = Text(label)
            .font(.system(size: 9.5, weight: .bold, design: .rounded))
            .foregroundStyle(TRVillagePalette.cream)
        context.draw(text, at: CGPoint(x: 15, y: 9.5), anchor: .center)
    }

    /// The delivery van, facing right, wheels turned `spin` degrees, puffing
    /// exhaust when `puffs` is above 0. As `idle` nears 1 it sits ticking over:
    /// its body rocking on its wheels and a wisp coming from the exhaust, in time
    /// with `time`.
    static func drawVan(_ context: GraphicsContext, spin: Double, puffs: Double, idle: Double, time: Double) {
        context.fill(ellipse(20, 26, 17, 2.6), with: .color(TRVillagePalette.ink.opacity(0.25)))
        if puffs > 0.001 {
            context.fill(circle(-2, 19, 2.4), with: .color(.white.opacity(0.8 * puffs)))
            context.fill(circle(-7, 16.5, 3.2), with: .color(.white.opacity(0.55 * puffs)))
            context.fill(circle(-13, 14, 3.8), with: .color(.white.opacity(0.3 * puffs)))
        }
        if idle > 0.001 {
            let p = phase(time, every: 1.8)
            let opacity = 0.45 * idle * min(1, p / 0.2) * (1 - p)
            context.fill(circle(-1 - 7 * p, 19 - 5 * p, 1.6 + 2 * p), with: .color(.white.opacity(opacity)))
        }
        var body = context
        body.translateBy(x: 0, y: sin(time * 9) * 0.3 * idle)
        body.fill(rect(2, 5, 34, 17, radius: 5), with: .color(Color(hex: 0xEC5B4B)))
        var cab = Path()
        cab.move(to: CGPoint(x: 24, y: 5))
        cab.addLine(to: CGPoint(x: 30, y: 5))
        cab.addArc(center: CGPoint(x: 30, y: 11), radius: 6, startAngle: .degrees(-90), endAngle: .degrees(0), clockwise: false)
        cab.addLine(to: CGPoint(x: 36, y: 22))
        cab.addLine(to: CGPoint(x: 24, y: 22))
        cab.closeSubpath()
        body.fill(cab, with: .color(Color(hex: 0xB8392C, opacity: 0.55)))
        let window = Color(hex: 0x2C3A55)
        body.fill(rect(26, 8, 7, 6, radius: 2), with: .color(window))
        body.fill(rect(6, 8, 15, 6, radius: 2), with: .color(window))
        body.fill(rect(5, 3, 26, 2.5, radius: 1.2), with: .color(Color(hex: 0xFBF7EE)))
        for x in [10.0, 28] {
            context.fill(circle(x, 22, 4.2), with: .color(Color(hex: 0x2A2933)))
            var hub = context
            hub.translateBy(x: x, y: 22)
            hub.rotate(by: .degrees(spin))
            hub.translateBy(x: -x, y: -22)
            let metal = Color(hex: 0xE9E4DA)
            hub.fill(circle(x, 22, 1.7), with: .color(metal))
            hub.fill(rect(x - 0.6, 18.3, 1.2, 2.4, radius: 0.6), with: .color(metal))
        }
    }
}

// MARK: Weather

extension TRVillageArt {
    /// How hard the breeze blows at `time` where it reaches `x` across the board:
    /// about 0.2 in a lull, up to 1 at a gust's height. A gust comes along every
    /// 11 s, each one a different strength, and sweeps left to right.
    static func breeze(at time: Double, x: Double = 195) -> Double {
        let t = time - x / 160
        let cycle = Int((t / 11).rounded(.down))
        let swell = pow(sin(phase(t, every: 11) * .pi), 4)
        let strength = 0.35 + 0.65 * TRVillageRoad.noise(cycle, 21)
        return 0.18 + 0.8 * strength * swell + 0.05 * sin(t * 1.9)
    }

    /// What floats over the board: wind streaks while it gusts, leaves and
    /// petals carried on it, motes rising in the sunbeams, and now and then a
    /// little flock crossing. `camera` slides the near ones a little as the
    /// ground moves under them, so they seem to hang between it and the eye.
    static func drawAir(_ context: GraphicsContext, board: TRVillageBoard, camera: Double, time: Double) {
        drawMotes(context, board: board, camera: camera, time: time)
        drawWindStreaks(context, board: board, time: time)
        drawDrift(context, board: board, camera: camera, time: time)
        drawBirds(context, board: board, time: time)
    }

    /// Wraps `y` into the stretch from `top` to `bottom`, and says how far it is
    /// from either end, to fade it in and out there.
    private static func wrap(_ y: Double, _ top: Double, _ bottom: Double) -> (y: Double, edge: Double) {
        let span = bottom - top
        let wrapped = top + (y - top - ((y - top) / span).rounded(.down) * span)
        return (wrapped, min(wrapped - top, bottom - wrapped))
    }

    /// Specks of light drifting up through the sunbeams on the left.
    private static func drawMotes(_ context: GraphicsContext, board: TRVillageBoard, camera: Double, time: Double) {
        let k = board.scaleX
        var motes = Path()
        for i in 0..<12 {
            let rise = phase(time + 9 * TRVillageRoad.noise(i, 31), every: 9 + 5 * TRVillageRoad.noise(i, 32))
            let x = (30 + 300 * TRVillageRoad.noise(i, 33) + 6 * sin(time * 0.7 + Double(i))) * k
            let (y, edge) = wrap(board.faceY(240 + 360 * TRVillageRoad.noise(i, 34)) - 70 * rise + camera * 0.2 * k, board.top, board.lip)
            let twinkle = 0.5 + 0.5 * sin(time * 2.3 + Double(i) * 1.7)
            let r = (1 + 0.8 * twinkle) * k * min(1, edge / 30) * min(1, rise / 0.2) * min(1, (1 - rise) / 0.2)
            motes.addPath(circle(x, y, r))
        }
        context.fill(motes, with: .color(Color(hex: 0xFFF6DE, opacity: 0.8)))
    }

    /// Curls of air sweeping across while a gust blows, gone in a lull.
    private static func drawWindStreaks(_ context: GraphicsContext, board: TRVillageBoard, time: Double) {
        let k = board.scaleX
        var curl = Path()
        curl.move(to: .zero)
        curl.addCurve(to: CGPoint(x: 40, y: -3), control1: CGPoint(x: 13, y: 5), control2: CGPoint(x: 26, y: -8))
        curl.addCurve(to: CGPoint(x: 52, y: -12), control1: CGPoint(x: 52, y: 1), control2: CGPoint(x: 60, y: -8))
        curl.addCurve(to: CGPoint(x: 46, y: -8), control1: CGPoint(x: 48, y: -15), control2: CGPoint(x: 43, y: -12))
        for i in 0..<4 {
            let period = 2.4 + 0.4 * Double(i)
            let shifted = time + Double(i) * 0.83
            let p = phase(shifted, every: period)
            let cycle = Int((shifted / period).rounded(.down))
            let x = (-30 + 300 * TRVillageRoad.noise(cycle, i) + 120 * p) * k
            let strength = min(1, max(0, breeze(at: time, x: x / k) - 0.35) / 0.4)
            guard strength > 0.01 else { continue }
            let y = board.faceY(170 + 420 * TRVillageRoad.noise(cycle, i + 40))
            // The streak draws itself on, then lets go of its tail.
            let streak = curl.trimmedPath(from: max(0, p * 1.5 - 0.5), to: min(1, p * 1.5))
            var placed = context
            placed.translateBy(x: x, y: y)
            placed.scaleBy(x: k, y: k)
            placed.stroke(streak, with: .color(.white.opacity(0.75 * strength)), style: StrokeStyle(lineWidth: 2, lineCap: .round))
        }
    }

    /// Leaves and petals tumbling across on the breeze: one or two in a lull,
    /// a flurry in a gust.
    private static func drawDrift(_ context: GraphicsContext, board: TRVillageBoard, camera: Double, time: Double) {
        let k = board.scaleX
        let colors = [TRVillagePalette.greens[0], TRVillagePalette.greens[1], Color(hex: 0xF6C234), Color(hex: 0xF4A3B4), .white]
        for i in 0..<10 {
            let period = 7 + 5 * TRVillageRoad.noise(i, 51)
            let shifted = time + period * TRVillageRoad.noise(i, 52)
            let p = phase(shifted, every: period)
            let cycle = Int((shifted / period).rounded(.down))
            let x = -20 + p * 430
            // Each waits for a stronger gust than the last before it shows.
            let showing = min(1, max(0, breeze(at: time, x: x) - 0.15 - 0.06 * Double(i)) * 4)
            guard showing > 0.01 else { continue }
            let flutter = sin(time * (1.6 + TRVillageRoad.noise(i, 53)) + Double(i)) * 16
            let (y, edge) = wrap(board.faceY(150 + 440 * TRVillageRoad.noise(cycle, i + 60)) + flutter + 50 * p + camera * 0.3 * k, board.top - 20, board.lip + 10)
            let opacity = showing * min(1, p / 0.08) * min(1, (1 - p) / 0.08) * min(1, edge / 20)
            var leaf = context
            leaf.opacity = opacity
            leaf.translateBy(x: x * k, y: y)
            leaf.rotate(by: .radians(time * (1.5 + 2 * TRVillageRoad.noise(i, 54)) + Double(i)))
            // Tumbling end over end, so it narrows and widens as it turns.
            leaf.scaleBy(x: k * (0.25 + 0.75 * abs(cos(time * 2.6 + Double(i) * 2))), y: k)
            leaf.fill(ellipse(0, 0, 5, 2.4), with: .color(colors[i % colors.count]))
        }
    }

    /// A few birds in a loose V, crossing over the top of the board every
    /// 24 s or so, a different way and height each time.
    private static func drawBirds(_ context: GraphicsContext, board: TRVillageBoard, time: Double) {
        let k = board.scaleX
        let period = 24.0
        let cycle = Int((time / period).rounded(.down))
        let crossing = phase(time, every: period) / 0.6
        guard crossing < 1 else { return }
        let heading: Double = TRVillageRoad.noise(cycle, 71) < 0.5 ? 1 : -1
        let height = 64 + 90 * TRVillageRoad.noise(cycle, 72)
        let climb = -30 + 60 * TRVillageRoad.noise(cycle, 73)
        let count = 3 + Int(3 * TRVillageRoad.noise(cycle, 74))
        let along = -40 + crossing * 520
        var flock = Path()
        for j in 0..<count {
            // The leader in front, the rest falling back on alternate sides.
            let rank = Double((j + 1) / 2)
            let side: Double = j.isMultiple(of: 2) ? 1 : -1
            let behind = along - rank * 16 - 4 * TRVillageRoad.noise(cycle, 80 + j)
            let x = heading > 0 ? behind : 390 - behind
            let y = height + climb * (behind / 430) + side * rank * 7 + 2 * sin(time * 1.3 + Double(j))
            // Flapping, with now and then a glide.
            let glide = 0.35 + 0.65 * max(0, sin(time * 0.9 + Double(j) * 1.1))
            let wing = sin(time * 10 + Double(j) * 1.3) * glide
            flock.addPath(bird(span: 7 - 0.5 * rank, wing: wing).applying(CGAffineTransform(translationX: x, y: y)))
        }
        var sky = context
        sky.scaleBy(x: k, y: k)
        sky.stroke(flock, with: .color(TRVillagePalette.ink.opacity(0.65)), style: StrokeStyle(lineWidth: 1.7, lineCap: .round, lineJoin: .round))
    }

    /// A bird as two arched wings meeting at its body, `span` to each tip;
    /// `wing` from 1, raised, to -1, lowered.
    private static func bird(span s: Double, wing: Double) -> Path {
        let tip = -0.55 * s * wing
        var path = Path()
        path.move(to: CGPoint(x: -s, y: tip))
        path.addQuadCurve(to: .zero, control: CGPoint(x: -0.5 * s, y: tip * 0.6 - 0.3 * s))
        path.addQuadCurve(to: CGPoint(x: s, y: tip), control: CGPoint(x: 0.5 * s, y: tip * 0.6 - 0.3 * s))
        return path
    }
}
