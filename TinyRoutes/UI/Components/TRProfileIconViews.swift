import SwiftUI

struct TRProfileCheckBadge: View {
    var size: CGFloat = 22

    var body: some View {
        ZStack {
            Circle()
                .fill(TRGameplayStyle.Colors.successGreen)
                .overlay {
                    Circle()
                        .stroke(.white, lineWidth: 2)
                }

            Image(systemName: "checkmark")
                .font(.system(size: size * 0.46, weight: .black))
                .foregroundStyle(.white)
        }
        .frame(width: size, height: size)
        .shadow(color: TRGameplayStyle.Colors.successGreen.opacity(0.24), radius: 4, x: 0, y: 2)
        .accessibilityHidden(true)
    }
}

struct TRProfileStatIcon: View {
    let systemImage: String
    let color: Color
    var size: CGFloat = 44

    var body: some View {
        ZStack {
            Circle()
                .fill(color.opacity(0.15))

            Image(systemName: systemImage)
                .font(.system(size: size * 0.46, weight: .black))
                .foregroundStyle(color)
        }
        .frame(width: size, height: size)
        .accessibilityHidden(true)
    }
}

struct TRProfileAchievementIcon: View {
    let achievement: ProfileAchievement
    var size: CGFloat = 56

    var body: some View {
        ZStack {
            RoundedRectangle(cornerRadius: size * 0.32, style: .continuous)
                .fill(achievement.accent.color.opacity(0.16))

            Image(systemName: achievement.systemImage)
                .font(.system(size: size * 0.44, weight: .black))
                .foregroundStyle(achievement.accent.color)
        }
        .frame(width: size, height: size)
        .accessibilityHidden(true)
    }
}

struct TRProfileCollectionIcon: View {
    let selection: ProfileCollectionSelection
    var size: CGFloat = 54

    var body: some View {
        ZStack {
            RoundedRectangle(cornerRadius: size * 0.30, style: .continuous)
                .fill(selection.accent.color.opacity(0.16))

            Image(systemName: selection.systemImage)
                .font(.system(size: size * 0.42, weight: .black))
                .foregroundStyle(selection.accent.color)
        }
        .frame(width: size, height: size)
        .accessibilityHidden(true)
    }
}

struct TRProfileAvatarIcon: View {
    var size: CGFloat = 86

    var body: some View {
        ZStack {
            Circle()
                .fill(
                    LinearGradient(
                        colors: [
                            Color(red: 0.13, green: 0.61, blue: 0.99),
                            Color(red: 0.05, green: 0.42, blue: 0.88)
                        ],
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    )
                )
                .overlay {
                    Circle()
                        .stroke(.white.opacity(0.86), lineWidth: size * 0.06)
                }

            Image(systemName: "mappin")
                .font(.system(size: size * 0.58, weight: .black))
                .foregroundStyle(.white.opacity(0.28))
                .offset(y: -size * 0.03)

            HStack(spacing: size * 0.16) {
                Circle()
                Circle()
            }
            .foregroundStyle(.white)
            .frame(width: size * 0.36, height: size * 0.08)
            .offset(y: -size * 0.08)

            Capsule()
                .stroke(.white, lineWidth: size * 0.035)
                .frame(width: size * 0.30, height: size * 0.16)
                .offset(y: size * 0.12)

            SpriteImage(name: "shipping_box")
                .scaledToFit()
                .frame(width: size * 0.34, height: size * 0.34)
                .background {
                    Circle()
                        .fill(.white.opacity(0.94))
                        .frame(width: size * 0.40, height: size * 0.40)
                }
                .offset(x: size * 0.32, y: size * 0.30)
        }
        .frame(width: size, height: size)
        .shadow(color: Color(red: 0.04, green: 0.30, blue: 0.70).opacity(0.22), radius: 10, x: 0, y: 6)
        .accessibilityHidden(true)
    }
}

struct TRProfileRewardChestIcon: View {
    var size: CGFloat = 54

    var body: some View {
        ZStack {
            RoundedRectangle(cornerRadius: size * 0.22, style: .continuous)
                .fill(Color(red: 1.00, green: 0.81, blue: 0.27))

            RoundedRectangle(cornerRadius: size * 0.10, style: .continuous)
                .fill(Color(red: 0.98, green: 0.55, blue: 0.16))
                .frame(width: size * 0.72, height: size * 0.34)
                .offset(y: size * 0.10)

            Rectangle()
                .fill(.white.opacity(0.78))
                .frame(width: size * 0.12, height: size * 0.64)

            Image(systemName: "star.fill")
                .font(.system(size: size * 0.24, weight: .black))
                .foregroundStyle(.white)
                .offset(y: size * 0.10)
        }
        .frame(width: size, height: size)
        .accessibilityHidden(true)
    }
}

extension ProfileAchievementAccent {
    var color: Color {
        switch self {
        case .gold:
            TRGameplayStyle.Colors.resultGold
        case .blue:
            TRGameplayStyle.Colors.primaryBlue
        case .purple:
            Color(red: 0.55, green: 0.33, blue: 0.95)
        case .orange:
            TRGameplayStyle.Colors.orangeAccent
        }
    }
}

extension ProfileCollectionAccent {
    var color: Color {
        switch self {
        case .theme:
            Color(red: 0.08, green: 0.62, blue: 0.82)
        case .trail:
            Color(red: 0.48, green: 0.43, blue: 0.90)
        case .destination:
            TRGameplayStyle.Colors.successGreen
        }
    }
}

#Preview("Profile Icons") {
    VStack(spacing: 18) {
        TRProfileAvatarIcon()
        HStack {
            TRProfileStatIcon(systemImage: "star.fill", color: TRGameplayStyle.Colors.resultGold)
            TRProfileAchievementIcon(achievement: TRProfileSummary.conceptPreview.achievements[0])
            TRProfileCollectionIcon(selection: ProfileCollectionSelection.conceptDefaults[0])
            TRProfileRewardChestIcon()
            TRProfileCheckBadge()
        }
    }
    .padding(24)
    .background(Color(red: 0.86, green: 0.94, blue: 0.98))
}
