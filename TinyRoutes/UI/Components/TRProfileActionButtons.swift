import SwiftUI

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
            HStack(spacing: 8) {
                Image(systemName: "pencil")
                Text("Edit Profile")
            }
            .font(.system(size: 17, weight: .black, design: .rounded))
            .foregroundStyle(.white)
            .frame(maxWidth: .infinity, minHeight: 60)
            .background {
                RoundedRectangle(cornerRadius: 22, style: .continuous)
                    .fill(TRGameplayStyle.Colors.primaryBlue)
                    .shadow(color: TRGameplayStyle.Colors.primaryBlue.opacity(0.22), radius: 9, x: 0, y: 5)
            }
        }
        .buttonStyle(.plain)
        .accessibilityLabel(Text("Edit Profile"))
    }

    private var achievementsButton: some View {
        Button(action: onAchievementsTapped) {
            HStack(spacing: 8) {
                Image(systemName: "rosette")
                Text("Achievements")
            }
            .font(.system(size: 17, weight: .black, design: .rounded))
            .foregroundStyle(TRGameplayStyle.Colors.titleNavy)
            .frame(maxWidth: .infinity, minHeight: 60)
            .background {
                RoundedRectangle(cornerRadius: 22, style: .continuous)
                    .fill(.white.opacity(0.93))
                    .overlay {
                        RoundedRectangle(cornerRadius: 22, style: .continuous)
                            .stroke(.white.opacity(0.72), lineWidth: 1)
                    }
                    .shadow(color: .black.opacity(0.08), radius: 9, x: 0, y: 5)
            }
        }
        .buttonStyle(.plain)
        .accessibilityLabel(Text("Achievements"))
    }
}

#Preview("Profile Actions") {
    TRProfileActionButtons(
        onEditProfileTapped: {},
        onAchievementsTapped: {}
    )
    .padding(20)
    .background(Color(red: 0.86, green: 0.94, blue: 0.98))
}
