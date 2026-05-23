import SwiftUI

struct TRResultStarRatingView: View {
    let stars: Int
    var size: CGFloat = TRGameplayStyle.Metrics.resultLargeStarSize

    var body: some View {
        HStack(spacing: max(size * 0.08, 4)) {
            ForEach(0..<3, id: \.self) { index in
                Image(systemName: index < clampedStars ? "star.fill" : "star.fill")
                    .font(.system(size: size, weight: .black, design: .rounded))
                    .foregroundStyle(index < clampedStars ? TRGameplayStyle.Colors.resultGold : TRGameplayStyle.Colors.resultEmptyStar)
                    .overlay {
                        if index >= clampedStars {
                            Image(systemName: "star")
                                .font(.system(size: size, weight: .black, design: .rounded))
                                .foregroundStyle(Color(red: 0.63, green: 0.70, blue: 0.80).opacity(0.62))
                        }
                    }
                    .shadow(
                        color: index < clampedStars ? TRGameplayStyle.Colors.resultGold.opacity(0.34) : .clear,
                        radius: 7,
                        x: 0,
                        y: 4
                    )
            }
        }
        .accessibilityHidden(true)
    }

    private var clampedStars: Int {
        min(max(stars, 0), 3)
    }
}

#Preview("Result Stars") {
    VStack(spacing: 16) {
        TRResultStarRatingView(stars: 3)
        TRResultStarRatingView(stars: 1)
        TRResultStarRatingView(stars: 0, size: 42)
    }
    .padding()
    .background(Color(red: 0.88, green: 0.95, blue: 1.0))
}
