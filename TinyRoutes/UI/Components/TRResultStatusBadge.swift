import SwiftUI

struct TRResultStatusBadge: View {
    enum Status {
        case success
        case failure
    }

    let status: Status

    var body: some View {
        ZStack {
            Circle()
                .fill(glowColor.opacity(0.22))
                .frame(width: TRGameplayStyle.Metrics.resultStatusBadgeSize + 18, height: TRGameplayStyle.Metrics.resultStatusBadgeSize + 18)
                .blur(radius: 6)

            Circle()
                .fill(.white)
                .frame(width: TRGameplayStyle.Metrics.resultStatusBadgeSize, height: TRGameplayStyle.Metrics.resultStatusBadgeSize)
                .shadow(color: glowColor.opacity(0.26), radius: 14, x: 0, y: 8)

            Circle()
                .fill(gradient)
                .frame(width: TRGameplayStyle.Metrics.resultStatusBadgeSize - 12, height: TRGameplayStyle.Metrics.resultStatusBadgeSize - 12)
                .overlay {
                    Circle()
                        .stroke(.white.opacity(0.42), lineWidth: 1.5)
                }

            Image(systemName: systemImage)
                .font(.system(size: 29, weight: .black, design: .rounded))
                .foregroundStyle(.white)
                .shadow(color: .black.opacity(0.16), radius: 4, x: 0, y: 2)
        }
        .accessibilityHidden(true)
    }

    private var systemImage: String {
        switch status {
        case .success:
            return "checkmark"
        case .failure:
            return "xmark"
        }
    }

    private var glowColor: Color {
        switch status {
        case .success:
            return TRGameplayStyle.Colors.successGreen
        case .failure:
            return TRGameplayStyle.Colors.resultWarningOrange
        }
    }

    private var gradient: LinearGradient {
        switch status {
        case .success:
            return LinearGradient(
                colors: [
                    Color(red: 0.28, green: 0.86, blue: 0.56),
                    TRGameplayStyle.Colors.successGreen
                ],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
        case .failure:
            return LinearGradient(
                colors: [
                    TRGameplayStyle.Colors.resultWarningOrange,
                    TRGameplayStyle.Colors.resultFailureRed
                ],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
        }
    }
}

#Preview("Result Badges") {
    HStack(spacing: 24) {
        TRResultStatusBadge(status: .success)
        TRResultStatusBadge(status: .failure)
    }
    .padding()
    .background(Color(red: 0.88, green: 0.95, blue: 1.0))
}
