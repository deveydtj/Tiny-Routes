import SwiftUI

/// The profile's two chunky buttons: editing it, and all its achievements.
struct TRProfileActionButtons: View {
    let onEditProfileTapped: () -> Void
    let onAchievementsTapped: () -> Void

    var body: some View {
        ViewThatFits(in: .horizontal) {
            HStack(spacing: 12) {
                editButton
                achievementsButton
            }

            VStack(spacing: 10) {
                editButton
                achievementsButton
            }
        }
    }

    private var editButton: some View {
        Button(action: onEditProfileTapped) {
            label("Edit Profile", systemImage: "pencil")
        }
        .buttonStyle(MultiVanHUDButtonStyle(isProminent: true, tint: TRVillagePalette.blue, shape: AnyShape(Capsule())))
        .accessibilityLabel(Text("Edit Profile"))
    }

    private var achievementsButton: some View {
        Button(action: onAchievementsTapped) {
            label("Achievements", systemImage: "rosette")
        }
        .buttonStyle(MultiVanHUDButtonStyle(shape: AnyShape(Capsule())))
        .accessibilityLabel(Text("Achievements"))
    }

    private func label(_ title: String, systemImage: String) -> some View {
        HStack(spacing: 8) {
            Image(systemName: systemImage)
                .font(.system(size: 17, weight: .semibold))
            Text(title)
                .font(.system(size: 18, weight: .semibold, design: .rounded))
                .lineLimit(1)
                .minimumScaleFactor(0.8)
        }
        .frame(maxWidth: .infinity, minHeight: 52)
    }
}

#Preview("Profile Actions") {
    TRProfileActionButtons(
        onEditProfileTapped: {},
        onAchievementsTapped: {}
    )
    .padding(20)
    .background(TRVillageSky())
}
