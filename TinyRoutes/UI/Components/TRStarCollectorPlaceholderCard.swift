import SwiftUI

struct TRStarCollectorPlaceholderCard: View {
    private let primaryBlue = Color(red: 0.05, green: 0.48, blue: 0.95)
    private let titleColor = Color(red: 0.05, green: 0.18, blue: 0.43)
    private let mutedTextColor = Color(red: 0.40, green: 0.49, blue: 0.62)
    private let progress: CGFloat = 102 / 150

    var body: some View {
        HStack(spacing: 14) {
            ZStack {
                Circle()
                    .fill(Color(red: 1.0, green: 0.82, blue: 0.28))
                Image(systemName: "trophy.fill")
                    .font(.system(size: 26, weight: .bold))
                    .foregroundStyle(.white)
            }
            .frame(width: 58, height: 58)
            .shadow(color: Color(red: 1.0, green: 0.65, blue: 0.14).opacity(0.25), radius: 8, x: 0, y: 5)

            VStack(alignment: .leading, spacing: 7) {
                Text("Star Collector")
                    .font(.system(size: 20, weight: .black, design: .rounded))
                    .foregroundStyle(titleColor)
                    .lineLimit(1)
                    .minimumScaleFactor(0.76)

                Text("Collect 150 stars")
                    .font(.system(size: 13, weight: .semibold, design: .rounded))
                    .foregroundStyle(mutedTextColor)

                progressBar

                Text("102 / 150")
                    .font(.system(size: 12, weight: .bold, design: .rounded))
                    .foregroundStyle(mutedTextColor)
            }

            Spacer(minLength: 4)

            rewardPill
        }
        .padding(18)
        .background {
            TRGlassCardBackground()
        }
        // TODO: Replace the placeholder total with stars from ProgressService when rewards are implemented.
    }

    private var progressBar: some View {
        GeometryReader { geometry in
            ZStack(alignment: .leading) {
                Capsule()
                    .fill(Color(red: 0.82, green: 0.87, blue: 0.93))

                Capsule()
                    .fill(primaryBlue)
                    .frame(width: geometry.size.width * progress)
            }
        }
        .frame(height: 8)
    }

    private var rewardPill: some View {
        VStack(spacing: 4) {
            Image(systemName: "star.circle.fill")
                .font(.system(size: 20, weight: .bold))
                .foregroundStyle(Color(red: 1.0, green: 0.74, blue: 0.18))

            Text("250")
                .font(.system(size: 14, weight: .black, design: .rounded))
                .foregroundStyle(titleColor)
        }
        .frame(width: 54, height: 58)
        .background {
            RoundedRectangle(cornerRadius: 18, style: .continuous)
                .fill(Color(red: 0.94, green: 0.97, blue: 1.0))
        }
    }
}

#Preview("Star Collector Placeholder") {
    ZStack {
        Color(red: 0.78, green: 0.90, blue: 0.96)
            .ignoresSafeArea()

        TRStarCollectorPlaceholderCard()
            .padding(20)
    }
}
