import SwiftUI

/// A real board, small and untouchable, wearing the cosmetics on trial: the same
/// flat board a level draws, on the table and under the sky the player would get.
struct TRShopBoardPreview: View {
    let cosmetics: MultiVanCosmetics
    /// Scatters the win's paper over the board, for a confetti on trial.
    var showsConfetti = false

    @State private var engine = Self.previewLevel.flatMap { try? MultiVanEngine(level: $0) }

    /// Two vans and two houses: enough board to judge a table by.
    private static let previewLevel = (try? MultiVanLevelRepository().loadAllLevels())?
        .first { $0.id == "level_005" }

    var body: some View {
        ZStack {
            TRShopTableSky(table: cosmetics.table)
            if let engine {
                MultiVanBoardView(engine: engine)
                    .environment(\.multiVanCosmetics, cosmetics)
                    // A board's own shape, so the sky shows either side of the table.
                    .aspectRatio(5.0 / 7.0, contentMode: .fit)
                    .padding(.top, 10)
                    .padding(.bottom, 16)
                    .allowsHitTesting(false)
            } else {
                TRShopTableSwatch(table: cosmetics.table)
            }
            if showsConfetti {
                TRShopConfettiScatter(style: cosmetics.confetti, count: 46)
            }
        }
        .clipShape(RoundedRectangle(cornerRadius: 18, style: .continuous))
        .accessibilityHidden(true)
    }
}

/// The studio sky a table theme paints behind the 3D board.
struct TRShopTableSky: View {
    let table: MultiVanTableTheme

    var body: some View {
        LinearGradient(colors: table.skyHexes.map { Color(hex: $0) }, startPoint: .top, endPoint: .bottom)
    }
}

/// A table theme at thumbnail size: its sky, and a slice of lawn on its two soil bands.
struct TRShopTableSwatch: View {
    let table: MultiVanTableTheme

    var body: some View {
        GeometryReader { geometry in
            let width = geometry.size.width * 0.62
            let height = geometry.size.height * 0.46
            let slab = RoundedRectangle(cornerRadius: 9, style: .continuous)
            ZStack {
                TRShopTableSky(table: table)
                ZStack {
                    slab.fill(Color(hex: table.deepSoilHex)).offset(y: 9)
                    slab.fill(Color(hex: table.soilHex)).offset(y: 5)
                    slab.fill(Color(hex: 0x8FC766))
                    // A scrap of road, so it reads as a board and not a swatch of green.
                    Capsule().fill(Color(hex: 0x6E7480)).frame(width: width * 0.62, height: 7)
                    Capsule().fill(.white.opacity(0.85)).frame(width: width * 0.5, height: 1.5)
                }
                .frame(width: width, height: height)
                .offset(y: -3)
            }
        }
        .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
    }
}

/// Paper in a confetti's colours, scattered the same way every time.
struct TRShopConfettiScatter: View {
    let style: MultiVanConfettiStyle
    var count = 22

    var body: some View {
        Canvas { context, size in
            let colors = TRConfettiScene.colors(forConfettiID: style.rawValue).map { Color(uiColor: $0) }
            var random = MultiVanDioramaRandom(seed: 97)
            for index in 0..<count {
                let centre = CGPoint(x: random.next() * size.width, y: random.next() * size.height)
                let side = 5 + random.next() * 4
                var piece = context
                piece.translateBy(x: centre.x, y: centre.y)
                piece.rotate(by: .radians(random.next() * .pi))
                piece.fill(
                    Path(CGRect(x: -side / 2, y: -side * 0.3, width: side, height: side * 0.6)),
                    with: .color(colors[index % colors.count])
                )
            }
        }
        .allowsHitTesting(false)
    }
}
