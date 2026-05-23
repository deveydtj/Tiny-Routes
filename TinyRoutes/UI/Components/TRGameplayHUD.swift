import SwiftUI

enum GameplayLevelNumberFormatter {
    static func title(for levelID: String) -> String {
        if let levelNumber = numericSuffix(in: levelID) {
            return "Level \(levelNumber)"
        }

        return levelID.isEmpty ? "Level" : "Level \(levelID)"
    }

    private static func numericSuffix(in levelID: String) -> Int? {
        let components = levelID.split(separator: "_")
        guard let suffix = components.last,
              !suffix.isEmpty,
              suffix.allSatisfy(\.isNumber),
              let number = Int(suffix) else {
            return nil
        }

        return number
    }
}

struct TRGameplayTopHUD: View {
    let levelID: String
    let isPaused: Bool
    let timeRemaining: TimeInterval?
    let tapCount: Int

    var body: some View {
        ViewThatFits(in: .horizontal) {
            HStack(spacing: 8) {
                TRGameplayLevelCard(levelID: levelID, isPaused: isPaused, tapCount: tapCount)
                    .frame(minWidth: 104)

                TRGameplayObjectiveCard()
                    .layoutPriority(1)

                TRGameplayTimerCard(timeRemaining: timeRemaining)
                    .frame(minWidth: 102)
            }

            VStack(spacing: 8) {
                HStack(spacing: 8) {
                    TRGameplayLevelCard(levelID: levelID, isPaused: isPaused, tapCount: tapCount)
                    TRGameplayTimerCard(timeRemaining: timeRemaining)
                }

                TRGameplayObjectiveCard()
            }
        }
    }
}

private struct TRGameplayLevelCard: View {
    let levelID: String
    let isPaused: Bool
    let tapCount: Int

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(GameplayLevelNumberFormatter.title(for: levelID))
                .font(.system(size: 16, weight: .heavy, design: .rounded))
                .foregroundStyle(.white)
                .lineLimit(1)
                .minimumScaleFactor(0.74)

            HStack(spacing: 3) {
                ForEach(0..<3, id: \.self) { _ in
                    Image(systemName: "star.fill")
                        .font(.system(size: 8, weight: .bold))
                        .foregroundStyle(Color.white.opacity(0.42))
                }
            }
            .accessibilityHidden(true)

            Text("\(isPaused ? "Paused" : "Running") | \(tapCount) taps")
                .font(.system(size: 10, weight: .bold, design: .rounded))
                .foregroundStyle(Color.white.opacity(0.78))
                .lineLimit(1)
                .minimumScaleFactor(0.70)
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 10)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background {
            RoundedRectangle(cornerRadius: 18, style: .continuous)
                .fill(
                    LinearGradient(
                        colors: [
                            Color(red: 0.22, green: 0.56, blue: 1.0),
                            TRGameplayStyle.Colors.primaryBlue
                        ],
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    )
                )
                .overlay {
                    RoundedRectangle(cornerRadius: 18, style: .continuous)
                        .stroke(Color.white.opacity(0.48), lineWidth: 1.5)
                }
                .shadow(color: TRGameplayStyle.Colors.primaryBlue.opacity(0.25), radius: 12, x: 0, y: 7)
        }
    }
}

struct TRGameplayObjectiveCard: View {
    var body: some View {
        HStack(spacing: 8) {
            SpriteImage(name: "shipping_box")
                .scaledToFit()
                .frame(width: 24, height: 24)
                .accessibilityHidden(true)

            Image(systemName: "arrow.right")
                .font(.system(size: 11, weight: .heavy, design: .rounded))
                .foregroundStyle(TRGameplayStyle.Colors.secondaryText)
                .accessibilityHidden(true)

            SpriteImage(name: "finish_flag_pin")
                .scaledToFit()
                .frame(width: 24, height: 24)
                .accessibilityHidden(true)

            Text("Deliver the package")
                .font(.system(size: 13, weight: .heavy, design: .rounded))
                .foregroundStyle(TRGameplayStyle.Colors.titleNavy)
                .lineLimit(1)
                .minimumScaleFactor(0.68)
                .layoutPriority(1)
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 10)
        .frame(maxWidth: .infinity)
        .background {
            TRGlassCardBackground(cornerRadius: 18)
        }
    }
}

struct TRGameplayTimerCard: View {
    let timeRemaining: TimeInterval?

    var body: some View {
        HStack(spacing: 6) {
            Image(systemName: "stopwatch.fill")
                .font(.system(size: 15, weight: .bold))
                .foregroundStyle(TRGameplayStyle.Colors.primaryBlue)
                .accessibilityHidden(true)

            Text(GameTimeFormatter.countdown(timeRemaining))
                .font(.system(size: 16, weight: .heavy, design: .rounded))
                .monospacedDigit()
                .foregroundStyle(TRGameplayStyle.Colors.titleNavy)
                .lineLimit(1)
                .minimumScaleFactor(0.72)
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 11)
        .frame(maxWidth: .infinity)
        .background {
            TRGlassCardBackground(cornerRadius: 18)
        }
    }
}

struct TRGameplayBottomControls: View {
    let isPaused: Bool
    let onRestartTapped: () -> Void
    let onPauseResumeTapped: () -> Void
    let onExitTapped: () -> Void

    var body: some View {
        HStack(spacing: 30) {
            TRGameplayControlButton(
                systemImage: "arrow.counterclockwise",
                label: "Restart",
                action: onRestartTapped
            )

            TRGameplayControlButton(
                systemImage: isPaused ? "play.fill" : "pause.fill",
                label: isPaused ? "Resume" : "Pause",
                action: onPauseResumeTapped
            )

            TRGameplayControlButton(
                systemImage: "house.fill",
                label: "Menu",
                action: onExitTapped
            )
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 8)
        .background {
            TRGlassCardBackground(cornerRadius: 24)
        }
    }
}

struct TRGameplayControlButton: View {
    let systemImage: String
    let label: String
    var isEnabled: Bool = true
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            VStack(spacing: 6) {
                ZStack {
                    Circle()
                        .fill(Color.white.opacity(isEnabled ? 0.97 : 0.68))
                        .overlay {
                            Circle()
                                .stroke(Color.white, lineWidth: 3)
                        }
                        .overlay {
                            Circle()
                                .stroke(TRGameplayStyle.Colors.markerStroke, lineWidth: 1.5)
                                .padding(2)
                        }
                        .shadow(color: Color.black.opacity(isEnabled ? 0.14 : 0.05), radius: 8, x: 0, y: 4)

                    Image(systemName: systemImage)
                        .font(.system(size: 20, weight: .heavy, design: .rounded))
                        .foregroundStyle(isEnabled ? TRGameplayStyle.Colors.titleNavy : TRGameplayStyle.Colors.secondaryText.opacity(0.65))
                }
                .frame(width: 50, height: 50)

                Text(label)
                    .font(.system(size: 11, weight: .heavy, design: .rounded))
                    .foregroundStyle(isEnabled ? TRGameplayStyle.Colors.titleNavy : TRGameplayStyle.Colors.secondaryText)
                    .lineLimit(1)
                    .minimumScaleFactor(0.70)
                    .frame(width: 68)
            }
        }
        .buttonStyle(.plain)
        .disabled(!isEnabled)
        .opacity(isEnabled ? 1 : 0.55)
        .accessibilityLabel(Text(label))
    }
}

#Preview("Gameplay HUD") {
    VStack(spacing: 20) {
        TRGameplayTopHUD(levelID: "level_012", isPaused: false, timeRemaining: 48.2, tapCount: 3)
        TRGameplayBottomControls(isPaused: false, onRestartTapped: {}, onPauseResumeTapped: {}, onExitTapped: {})
    }
    .padding()
    .background(Color(red: 0.86, green: 0.93, blue: 0.98))
}
