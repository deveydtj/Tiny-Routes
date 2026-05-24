import SwiftUI

struct TRCurrencyPill: View {
    enum Size {
        case standard
        case menuHeader
    }

    let coinTotal: Int
    let onAddTapped: () -> Void
    let size: Size

    init(coinTotal: Int, onAddTapped: @escaping () -> Void, size: Size = .standard) {
        self.coinTotal = coinTotal
        self.onAddTapped = onAddTapped
        self.size = size
    }

    private var formattedCoinTotal: String {
        coinTotal.formatted(.number.grouping(.automatic))
    }

    var body: some View {
        Button(action: onAddTapped) {
            HStack(spacing: metrics.spacing) {
                ZStack {
                    Image(systemName: "star.circle.fill")
                        .font(.system(size: metrics.coinImageSize - 3, weight: .bold))
                        .foregroundStyle(TRGameplayStyle.Colors.resultGold)

                    SpriteImage(name: "gold_coin")
                        .scaledToFit()
                        .frame(width: metrics.coinImageSize, height: metrics.coinImageSize)
                }
                .frame(width: metrics.coinImageSize, height: metrics.coinImageSize)
                .accessibilityHidden(true)

                Text(formattedCoinTotal)
                    .font(.system(size: metrics.textFontSize, weight: .bold, design: .rounded))
                    .foregroundStyle(TRGameplayStyle.Colors.titleNavy)
                    .lineLimit(1)
                    .minimumScaleFactor(0.76)
                    .monospacedDigit()

                Image(systemName: "plus.circle.fill")
                    .font(.system(size: metrics.plusIconSize, weight: .bold))
                    .foregroundStyle(TRGameplayStyle.Colors.primaryBlue)
                    .accessibilityHidden(true)
            }
            .padding(.leading, metrics.leadingPadding)
            .padding(.trailing, metrics.trailingPadding)
            .frame(height: metrics.height)
            .background {
                Capsule()
                    .fill(.white.opacity(0.92))
                    .overlay {
                        Capsule()
                            .stroke(.white.opacity(0.70), lineWidth: 1)
                    }
                    .shadow(color: .black.opacity(0.08), radius: 8, x: 0, y: 4)
            }
            .contentShape(Capsule())
        }
        .buttonStyle(.plain)
        .accessibilityLabel(Text("Add currency"))
        .accessibilityValue(Text(formattedCoinTotal))
    }

    private var metrics: CurrencyPillMetrics {
        switch size {
        case .standard:
            return CurrencyPillMetrics(
                height: 42,
                leadingPadding: 11,
                trailingPadding: 9,
                coinImageSize: 23,
                textFontSize: 15,
                plusIconSize: 18,
                spacing: 7
            )
        case .menuHeader:
            return CurrencyPillMetrics(
                height: 54,
                leadingPadding: 15,
                trailingPadding: 12,
                coinImageSize: 29,
                textFontSize: 18,
                plusIconSize: 23,
                spacing: 9
            )
        }
    }
}

private struct CurrencyPillMetrics {
    let height: CGFloat
    let leadingPadding: CGFloat
    let trailingPadding: CGFloat
    let coinImageSize: CGFloat
    let textFontSize: CGFloat
    let plusIconSize: CGFloat
    let spacing: CGFloat
}

#Preview("Currency Pill") {
    ZStack {
        Color(red: 0.78, green: 0.90, blue: 0.96)
            .ignoresSafeArea()

        VStack(spacing: 20) {
            TRCurrencyPill(coinTotal: 1_250, onAddTapped: {})
            TRCurrencyPill(coinTotal: 12_500, onAddTapped: {}, size: .menuHeader)
        }
    }
}
