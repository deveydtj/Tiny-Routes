import SwiftUI

/// A progress bar sunk into a cream card, filling with a glossy colour.
struct TRProgressBar: View {
    let progress: CGFloat
    var height: CGFloat = 10
    var fillColor: Color = TRVillagePalette.blue
    var trackColor: Color = Color(hex: 0xE9DDC5)

    private var clampedProgress: CGFloat {
        min(max(progress, 0), 1)
    }

    var body: some View {
        GeometryReader { geometry in
            ZStack(alignment: .leading) {
                Capsule()
                    .fill(trackColor)
                    .overlay { Capsule().strokeBorder(TRVillagePalette.creamLip.opacity(0.6), lineWidth: 1) }

                Capsule()
                    .fill(fillColor)
                    .overlay { Capsule().fill(LinearGradient(colors: [.white.opacity(0.3), .clear], startPoint: .top, endPoint: .center)) }
                    .frame(width: max(clampedProgress > 0 ? height : 0, geometry.size.width * clampedProgress))
            }
        }
        .frame(height: height)
        .accessibilityHidden(true)
    }
}

#Preview("Progress Bar") {
    VStack(spacing: 16) {
        TRProgressBar(progress: 0)
        TRProgressBar(progress: 0.55)
        TRProgressBar(progress: 1, fillColor: MultiVanHUDStyle.pine)
    }
    .padding(24)
    .background(MultiVanHUDCardBackground())
    .padding(24)
}
