import SwiftUI

/// A striped roadworks plank on two posts. Zero rotation closes a road travelling screen-up.
struct MultiVanBarrierView: View {
    var width: CGFloat = 30

    var body: some View {
        let height = width * 0.34
        let plank = RoundedRectangle(cornerRadius: height * 0.3)
        ZStack {
            // Two wooden posts stand just inside the plank's ends.
            ForEach([-1.0, 1.0], id: \.self) { side in
                RoundedRectangle(cornerRadius: width * 0.03)
                    .fill(Color(hex: 0x8A6244))
                    .frame(width: width * 0.1, height: height * 1.5)
                    .offset(x: width * 0.36 * side, y: height * 0.12)
            }
            plank
                .fill(TRVillagePalette.cream)
                .overlay {
                    Path { path in
                        for index in -1...4 {
                            let x = CGFloat(index) * width * 0.3
                            path.move(to: CGPoint(x: x, y: height))
                            path.addLine(to: CGPoint(x: x + width * 0.14, y: height))
                            path.addLine(to: CGPoint(x: x + width * 0.14 + height, y: 0))
                            path.addLine(to: CGPoint(x: x + height, y: 0))
                            path.closeSubpath()
                        }
                    }
                    .fill(Color(hex: 0xEC5B4B))
                }
                .clipShape(plank)
                .overlay { plank.strokeBorder(Color(hex: 0xB8392C).opacity(0.55), lineWidth: width * 0.03) }
                .frame(width: width, height: height)
        }
        .frame(width: width, height: height)
        .shadow(color: TRVillagePalette.ink.opacity(0.28), radius: width * 0.02, y: width * 0.04)
        .accessibilityLabel(Self.accessibilityLabel)
    }

    static let accessibilityLabel = "Dead end barrier"
}

#if DEBUG
#Preview("Barriers — gameplay and enlarged") {
    HStack(spacing: 32) {
        MultiVanBarrierView()
        MultiVanBarrierView().rotationEffect(.degrees(90))
        MultiVanBarrierView(width: 60)
    }
    .padding(32)
    .background(Color(hex: 0x8FC766))
}
#endif
