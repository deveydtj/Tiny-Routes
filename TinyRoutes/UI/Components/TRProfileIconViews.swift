import SwiftUI

/// A green tick on a cream ring, for what's earned or in use.
struct TRProfileCheckBadge: View {
    var size: CGFloat = 22

    var body: some View {
        Image(systemName: "checkmark")
            .font(.system(size: size * 0.46, weight: .bold))
            .foregroundStyle(.white)
            .frame(width: size, height: size)
            .background {
                Circle()
                    .fill(MultiVanHUDStyle.pine)
                    .overlay { Circle().strokeBorder(TRVillagePalette.cream, lineWidth: 2) }
                    .background { Circle().fill(MultiVanHUDStyle.pineDark).offset(y: 2) }
            }
            .accessibilityHidden(true)
    }
}

/// A stat's symbol on a round coloured badge.
struct TRProfileStatIcon: View {
    let systemImage: String
    let color: Color
    var size: CGFloat = 44

    var body: some View {
        TRCozyIconBadge(systemName: systemImage, tint: color, size: size)
    }
}

/// An achievement's symbol on a rounded tile: coloured once earned, sunken and
/// faded until then.
struct TRProfileAchievementIcon: View {
    let achievement: ProfileAchievement
    var size: CGFloat = 56

    var body: some View {
        let shape = RoundedRectangle(cornerRadius: size * 0.3, style: .continuous)
        Image(systemName: achievement.systemImage)
            .font(.system(size: size * 0.42, weight: .semibold))
            .foregroundStyle(achievement.isUnlocked ? TRVillagePalette.cream : TRVillagePalette.slate.opacity(0.7))
            .frame(width: size, height: size)
            .background {
                if achievement.isUnlocked {
                    shape
                        .fill(achievement.accent.color)
                        .overlay { shape.fill(LinearGradient(colors: [.white.opacity(0.22), .clear], startPoint: .top, endPoint: .center)) }
                        .background { shape.fill(achievement.accent.color).overlay { shape.fill(.black.opacity(0.25)) }.offset(y: 3) }
                } else {
                    shape
                        .fill(TRVillagePalette.creamDeep)
                        .overlay { shape.strokeBorder(TRVillagePalette.creamLip, style: StrokeStyle(lineWidth: 1.5, dash: [4, 3])) }
                }
            }
            .padding(.bottom, 3)
            .accessibilityHidden(true)
    }
}

/// A collection's symbol on a rounded coloured tile.
struct TRProfileCollectionIcon: View {
    let selection: ProfileCollectionSelection
    var size: CGFloat = 54

    var body: some View {
        let shape = RoundedRectangle(cornerRadius: size * 0.3, style: .continuous)
        Image(systemName: selection.systemImage)
            .font(.system(size: size * 0.42, weight: .semibold))
            .foregroundStyle(TRVillagePalette.cream)
            .frame(width: size, height: size)
            .background {
                shape
                    .fill(selection.accent.color)
                    .overlay { shape.fill(LinearGradient(colors: [.white.opacity(0.22), .clear], startPoint: .top, endPoint: .center)) }
                    .background { shape.fill(selection.accent.color).overlay { shape.fill(.black.opacity(0.25)) }.offset(y: 3) }
            }
            .padding(.bottom, 3)
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
                            Color(hex: 0x2E7C82),
                            TRVillagePalette.teal
                        ],
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    )
                )
                .overlay {
                    Circle()
                        .strokeBorder(TRVillagePalette.cream, lineWidth: size * 0.06)
                }
                .background { Circle().fill(TRVillagePalette.tealDark).offset(y: size * 0.05) }

            Image(systemName: "mappin")
                .font(.system(size: size * 0.58, weight: .bold))
                .foregroundStyle(TRVillagePalette.mint.opacity(0.3))
                .offset(y: -size * 0.03)

            HStack(spacing: size * 0.16) {
                Circle()
                Circle()
            }
            .foregroundStyle(TRVillagePalette.cream)
            .frame(width: size * 0.36, height: size * 0.08)
            .offset(y: -size * 0.08)

            Capsule()
                .stroke(TRVillagePalette.cream, lineWidth: size * 0.035)
                .frame(width: size * 0.30, height: size * 0.16)
                .offset(y: size * 0.12)

            SpriteImage(name: "shipping_box")
                .scaledToFit()
                .frame(width: size * 0.34, height: size * 0.34)
                .background {
                    Circle()
                        .fill(TRVillagePalette.cream)
                        .frame(width: size * 0.40, height: size * 0.40)
                }
                .offset(x: size * 0.32, y: size * 0.30)
        }
        .frame(width: size, height: size)
        .shadow(color: TRVillagePalette.ink.opacity(0.22), radius: 8, x: 0, y: 6)
        .accessibilityHidden(true)
    }
}

struct TRProfileRewardChestIcon: View {
    var size: CGFloat = 54

    var body: some View {
        ZStack {
            RoundedRectangle(cornerRadius: size * 0.22, style: .continuous)
                .fill(TRVillagePalette.roofs[1])

            RoundedRectangle(cornerRadius: size * 0.10, style: .continuous)
                .fill(Color(hex: 0xC8862F))
                .frame(width: size * 0.72, height: size * 0.34)
                .offset(y: size * 0.10)

            Rectangle()
                .fill(.white.opacity(0.78))
                .frame(width: size * 0.12, height: size * 0.64)

            Image(systemName: "star.fill")
                .font(.system(size: size * 0.24, weight: .bold))
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
            Color(hex: 0xE3A51C)
        case .blue:
            TRVillagePalette.blue
        case .purple:
            Color(hex: 0x8A6FD1)
        case .orange:
            TRVillagePalette.roofs[0]
        }
    }
}

extension ProfileCollectionAccent {
    var color: Color {
        switch self {
        case .theme:
            TRVillagePalette.teal
        case .trail:
            Color(hex: 0x8A6FD1)
        case .destination:
            MultiVanHUDStyle.pine
        }
    }
}

#Preview("Profile Icons") {
    VStack(spacing: 18) {
        TRProfileAvatarIcon()
        HStack {
            TRProfileStatIcon(systemImage: "star.fill", color: TRVillagePalette.gold)
            TRProfileAchievementIcon(achievement: TRProfileSummary.conceptPreview.achievements[0])
            TRProfileCollectionIcon(selection: ProfileCollectionSelection.conceptDefaults[0])
            TRProfileRewardChestIcon()
            TRProfileCheckBadge()
        }
    }
    .padding(24)
    .background(TRVillageSky())
}
