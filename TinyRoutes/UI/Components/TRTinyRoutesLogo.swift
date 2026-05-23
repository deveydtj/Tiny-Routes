import SwiftUI

struct TRTinyRoutesLogo: View {
    enum Size {
        case large
        case medium
        case compact
    }

    let subtitle: String?
    let size: Size

    init(subtitle: String? = "One-tap delivery puzzles", size: Size = .large) {
        self.subtitle = subtitle
        self.size = size
    }

    var body: some View {
        VStack(spacing: metrics.subtitleSpacing) {
            ZStack(alignment: .topLeading) {
                HStack(alignment: .firstTextBaseline, spacing: metrics.wordSpacing) {
                    Text("Tiny")
                        .foregroundStyle(TRGameplayStyle.Colors.titleNavy)

                    Text("Routes")
                        .foregroundStyle(
                            LinearGradient(
                                colors: [
                                    Color(red: 0.10, green: 0.56, blue: 0.97),
                                    Color(red: 0.05, green: 0.42, blue: 0.90)
                                ],
                                startPoint: .top,
                                endPoint: .bottom
                            )
                        )
                }
                .font(.system(size: metrics.titleSize, weight: .black, design: .rounded))
                .lineLimit(1)
                .minimumScaleFactor(0.72)
                .shadow(color: .white.opacity(0.60), radius: 1, x: 0, y: 1)
                .shadow(color: Color(red: 0.12, green: 0.45, blue: 0.82).opacity(0.18), radius: metrics.titleShadowRadius, x: 0, y: metrics.titleShadowY)

                Image(systemName: "mappin.circle.fill")
                    .font(.system(size: metrics.pinSize, weight: .heavy))
                    .symbolRenderingMode(.palette)
                    .foregroundStyle(.white, Color(red: 0.13, green: 0.57, blue: 0.97))
                    .shadow(color: Color(red: 0.04, green: 0.31, blue: 0.72).opacity(0.22), radius: 4, x: 0, y: 3)
                    .offset(metrics.pinOffset)
                    .accessibilityHidden(true)
            }

            if let subtitle {
                Text(subtitle)
                    .font(.system(size: metrics.subtitleSize, weight: .semibold, design: .rounded))
                    .foregroundStyle(TRGameplayStyle.Colors.secondaryText)
                    .lineLimit(1)
                    .minimumScaleFactor(0.82)
            }
        }
        .padding(.top, metrics.topPadding)
        .padding(.bottom, metrics.bottomPadding)
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(Text(accessibilityLabel))
    }

    private var accessibilityLabel: String {
        if let subtitle {
            return "Tiny Routes. \(subtitle)."
        }

        return "Tiny Routes."
    }

    private var metrics: LogoMetrics {
        switch size {
        case .large:
            return LogoMetrics(
                titleSize: 54,
                subtitleSize: 23,
                pinSize: 34,
                wordSpacing: 8,
                subtitleSpacing: 5,
                pinOffset: CGSize(width: 90, height: -26),
                titleShadowRadius: 7,
                titleShadowY: 5,
                topPadding: 14,
                bottomPadding: 4
            )
        case .medium:
            return LogoMetrics(
                titleSize: 40,
                subtitleSize: 17,
                pinSize: 26,
                wordSpacing: 6,
                subtitleSpacing: 1,
                pinOffset: CGSize(width: 66, height: -19),
                titleShadowRadius: 5,
                titleShadowY: 4,
                topPadding: 6,
                bottomPadding: 2
            )
        case .compact:
            return LogoMetrics(
                titleSize: 27,
                subtitleSize: 13,
                pinSize: 18,
                wordSpacing: 4,
                subtitleSpacing: 0,
                pinOffset: CGSize(width: 45, height: -12),
                titleShadowRadius: 4,
                titleShadowY: 3,
                topPadding: 0,
                bottomPadding: 0
            )
        }
    }
}

private struct LogoMetrics {
    let titleSize: CGFloat
    let subtitleSize: CGFloat
    let pinSize: CGFloat
    let wordSpacing: CGFloat
    let subtitleSpacing: CGFloat
    let pinOffset: CGSize
    let titleShadowRadius: CGFloat
    let titleShadowY: CGFloat
    let topPadding: CGFloat
    let bottomPadding: CGFloat
}

#Preview("Tiny Routes Logo") {
    VStack(spacing: 24) {
        TRTinyRoutesLogo()
        TRTinyRoutesLogo(subtitle: "Levels", size: .medium)
        TRTinyRoutesLogo(subtitle: nil, size: .compact)
    }
    .padding(24)
    .background(Color(red: 0.86, green: 0.94, blue: 0.98))
}
