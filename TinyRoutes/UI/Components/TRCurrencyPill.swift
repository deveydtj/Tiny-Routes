import SwiftUI

struct TRCurrencyPill: View {
    let coinTotal: Int
    let onAddTapped: () -> Void

    private var formattedCoinTotal: String {
        coinTotal.formatted(.number.grouping(.automatic))
    }

    var body: some View {
        Button(action: onAddTapped) {
            HStack(spacing: 7) {
                ZStack {
                    Image(systemName: "star.circle.fill")
                        .font(.system(size: 20, weight: .bold))
                        .foregroundStyle(TRGameplayStyle.Colors.resultGold)

                    SpriteImage(name: "gold_coin")
                        .scaledToFit()
                        .frame(width: 23, height: 23)
                }
                .frame(width: 23, height: 23)
                .accessibilityHidden(true)

                Text(formattedCoinTotal)
                    .font(.system(size: 15, weight: .bold, design: .rounded))
                    .foregroundStyle(TRGameplayStyle.Colors.titleNavy)
                    .lineLimit(1)
                    .minimumScaleFactor(0.76)
                    .monospacedDigit()

                Image(systemName: "plus.circle.fill")
                    .font(.system(size: 18, weight: .bold))
                    .foregroundStyle(TRGameplayStyle.Colors.primaryBlue)
                    .accessibilityHidden(true)
            }
            .padding(.leading, 11)
            .padding(.trailing, 9)
            .frame(height: 42)
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
}

#Preview("Currency Pill") {
    ZStack {
        Color(red: 0.78, green: 0.90, blue: 0.96)
            .ignoresSafeArea()

        TRCurrencyPill(coinTotal: 1_250, onAddTapped: {})
    }
}
