import SwiftUI

struct TRLevelPageHeader: View {
    let onSettingsTapped: () -> Void
    let onAddCurrencyTapped: () -> Void

    private let primaryBlue = Color(red: 0.05, green: 0.48, blue: 0.95)
    private let titleColor = Color(red: 0.05, green: 0.18, blue: 0.43)
    private let secondaryTextColor = Color(red: 0.35, green: 0.43, blue: 0.56)

    var body: some View {
        VStack(spacing: 8) {
            HStack {
                Button(action: onSettingsTapped) {
                    Image(systemName: "gearshape.fill")
                        .font(.system(size: 18, weight: .bold))
                        .foregroundStyle(primaryBlue)
                        .frame(width: 44, height: 44)
                        .background {
                            Circle()
                                .fill(.white.opacity(0.90))
                                .overlay {
                                    Circle()
                                        .stroke(.white.opacity(0.70), lineWidth: 1)
                                }
                                .shadow(color: .black.opacity(0.08), radius: 8, x: 0, y: 4)
                        }
                }
                .buttonStyle(.plain)
                .accessibilityLabel(Text("Settings"))

                Spacer()

                Button(action: onAddCurrencyTapped) {
                    HStack(spacing: 7) {
                        Image(systemName: "star.circle.fill")
                            .font(.system(size: 20, weight: .bold))
                            .foregroundStyle(Color(red: 1.0, green: 0.74, blue: 0.18))

                        Text("1,250")
                            .font(.system(size: 15, weight: .bold, design: .rounded))
                            .foregroundStyle(titleColor)

                        Image(systemName: "plus.circle.fill")
                            .font(.system(size: 18, weight: .bold))
                            .foregroundStyle(primaryBlue)
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
                }
                .buttonStyle(.plain)
                .accessibilityLabel(Text("Add currency"))
                .accessibilityValue(Text("1,250"))
            }

            VStack(spacing: 0) {
                Text("Tiny Routes")
                    .font(.system(size: 40, weight: .black, design: .rounded))
                    .foregroundStyle(titleColor)
                    .lineLimit(1)
                    .minimumScaleFactor(0.72)
                    .shadow(color: .white.opacity(0.70), radius: 1, x: 0, y: 1)

                Text("Levels")
                    .font(.system(size: 17, weight: .semibold, design: .rounded))
                    .foregroundStyle(secondaryTextColor)
            }
            .padding(.top, -4)
        }
    }
}

#Preview("Level Page Header") {
    ZStack {
        Color(red: 0.78, green: 0.90, blue: 0.96)
            .ignoresSafeArea()

        TRLevelPageHeader(
            onSettingsTapped: {},
            onAddCurrencyTapped: {}
        )
        .padding(20)
    }
}
