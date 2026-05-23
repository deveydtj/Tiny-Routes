import SwiftUI

struct TRProfileHeader: View {
    let coinTotal: Int
    let onSettingsTapped: () -> Void
    let onAddCurrencyTapped: () -> Void

    var body: some View {
        VStack(spacing: 2) {
            ZStack {
                HStack {
                    Button(action: onSettingsTapped) {
                        Image(systemName: "gearshape.fill")
                            .font(.system(size: 20, weight: .bold))
                            .foregroundStyle(TRGameplayStyle.Colors.primaryBlue)
                            .frame(width: 44, height: 44)
                            .background {
                                RoundedRectangle(cornerRadius: 16, style: .continuous)
                                    .fill(.white.opacity(0.92))
                                    .overlay {
                                        RoundedRectangle(cornerRadius: 16, style: .continuous)
                                            .stroke(.white.opacity(0.72), lineWidth: 1)
                                    }
                                    .shadow(color: .black.opacity(0.08), radius: 8, x: 0, y: 4)
                            }
                    }
                    .buttonStyle(.plain)
                    .accessibilityLabel(Text("Settings"))

                    Spacer(minLength: 12)

                    TRCurrencyPill(coinTotal: coinTotal, onAddTapped: onAddCurrencyTapped)
                }

                TRTinyRoutesLogo(subtitle: nil, size: .compact)
                    .frame(maxWidth: 170)
            }
            .frame(minHeight: 48)

            ZStack {
                confettiDiamond(color: TRGameplayStyle.Colors.resultGold)
                    .offset(x: -72, y: -2)

                confettiDiamond(color: TRGameplayStyle.Colors.primaryBlue, size: 7)
                    .offset(x: 74, y: 5)

                Text("Profile")
                    .font(.system(size: 31, weight: .black, design: .rounded))
                    .foregroundStyle(TRGameplayStyle.Colors.titleNavy)
                    .lineLimit(1)
                    .minimumScaleFactor(0.82)
                    .accessibilityAddTraits(.isHeader)
            }
            .frame(maxWidth: .infinity)
        }
        .padding(.top, 6)
    }

    private func confettiDiamond(color: Color, size: CGFloat = 9) -> some View {
        RoundedRectangle(cornerRadius: 2, style: .continuous)
            .fill(color)
            .frame(width: size, height: size)
            .rotationEffect(.degrees(45))
            .accessibilityHidden(true)
    }
}

#Preview("Profile Header") {
    TRProfileHeader(
        coinTotal: 1_250,
        onSettingsTapped: {},
        onAddCurrencyTapped: {}
    )
    .padding(20)
    .background(Color(red: 0.86, green: 0.94, blue: 0.98))
}
