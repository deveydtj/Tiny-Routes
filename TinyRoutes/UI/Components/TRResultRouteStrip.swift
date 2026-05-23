import SwiftUI

struct TRResultRouteStrip: View {
    enum State {
        case success
        case failure
    }

    let state: State

    var body: some View {
        HStack(spacing: 10) {
            endpointIcon(spriteName: "shipping_box", badgeSystemImage: nil)

            routeLine
                .frame(height: 42)
                .layoutPriority(1)

            endpointIcon(
                spriteName: "finish_flag_pin",
                badgeSystemImage: state == .success ? "checkmark" : "exclamationmark"
            )
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 11)
        .background {
            RoundedRectangle(cornerRadius: 22, style: .continuous)
                .fill(.white.opacity(0.78))
                .overlay {
                    RoundedRectangle(cornerRadius: 22, style: .continuous)
                        .stroke(.white.opacity(0.72), lineWidth: 1)
                }
                .shadow(color: .black.opacity(0.06), radius: 10, x: 0, y: 5)
        }
        .accessibilityHidden(true)
    }

    private var routeLine: some View {
        GeometryReader { geometry in
            ZStack {
                HStack(spacing: dotSpacing(width: geometry.size.width)) {
                    ForEach(0..<dotCount(width: geometry.size.width), id: \.self) { index in
                        Circle()
                            .fill(dotColor.opacity(dotOpacity(for: index, total: dotCount(width: geometry.size.width))))
                            .frame(width: 6, height: 6)
                    }
                }
                .frame(maxWidth: .infinity)

                if state == .success {
                    Image(systemName: "arrow.right")
                        .font(.system(size: 17, weight: .black, design: .rounded))
                        .foregroundStyle(dotColor)
                        .padding(6)
                        .background(Circle().fill(.white.opacity(0.78)))
                } else {
                    ZStack {
                        Circle()
                            .fill(.white)
                        Circle()
                            .fill(TRGameplayStyle.Colors.resultFailureRed)
                            .padding(3)
                        Image(systemName: "xmark")
                            .font(.system(size: 10, weight: .black, design: .rounded))
                            .foregroundStyle(.white)
                    }
                    .frame(width: 28, height: 28)
                    .shadow(color: TRGameplayStyle.Colors.resultFailureRed.opacity(0.18), radius: 6, x: 0, y: 3)
                }
            }
            .frame(width: geometry.size.width, height: geometry.size.height)
        }
    }

    private var dotColor: Color {
        switch state {
        case .success:
            return TRGameplayStyle.Colors.successGreen
        case .failure:
            return Color(red: 0.54, green: 0.62, blue: 0.72)
        }
    }

    private func dotCount(width: CGFloat) -> Int {
        max(Int(width / 14), 5)
    }

    private func dotSpacing(width: CGFloat) -> CGFloat {
        let count = dotCount(width: width)
        guard count > 1 else { return 0 }
        return max((width - CGFloat(count * 6)) / CGFloat(count - 1), 4)
    }

    private func dotOpacity(for index: Int, total: Int) -> Double {
        guard state == .failure else { return 1.0 }
        let middle = total / 2
        return index >= middle ? 0.32 : 0.78
    }

    private func endpointIcon(spriteName: String, badgeSystemImage: String?) -> some View {
        ZStack(alignment: .bottomTrailing) {
            Circle()
                .fill(.white)
                .frame(width: 54, height: 54)
                .overlay {
                    Circle()
                        .stroke(Color(red: 0.72, green: 0.80, blue: 0.89).opacity(0.50), lineWidth: 1)
                }
                .shadow(color: .black.opacity(0.08), radius: 7, x: 0, y: 4)

            SpriteImage(name: spriteName)
                .scaledToFit()
                .frame(width: 38, height: 38)
                .padding(8)
                .frame(width: 54, height: 54)

            if let badgeSystemImage {
                Circle()
                    .fill(badgeFill)
                    .frame(width: 21, height: 21)
                    .overlay {
                        Image(systemName: badgeSystemImage)
                            .font(.system(size: 9, weight: .black))
                            .foregroundStyle(.white)
                    }
                    .overlay {
                        Circle()
                            .stroke(.white, lineWidth: 2)
                    }
                    .offset(x: 3, y: 3)
            }
        }
        .frame(width: 58, height: 58)
    }

    private var badgeFill: Color {
        switch state {
        case .success:
            return TRGameplayStyle.Colors.successGreen
        case .failure:
            return TRGameplayStyle.Colors.resultWarningOrange
        }
    }
}

#Preview("Result Route Strips") {
    VStack(spacing: 18) {
        TRResultRouteStrip(state: .success)
        TRResultRouteStrip(state: .failure)
    }
    .padding()
    .background(Color(red: 0.88, green: 0.95, blue: 1.0))
}
