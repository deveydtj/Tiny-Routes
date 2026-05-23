import SwiftUI

struct ProfileScreen: View {
    let summary: TRProfileSummary
    let onSettingsTapped: () -> Void
    let onAddCurrencyTapped: () -> Void
    let onEditProfileTapped: () -> Void
    let onAchievementsTapped: () -> Void
    let onCustomizeTapped: () -> Void

    @State private var activePlaceholder: ProfilePlaceholderAlert?

    var body: some View {
        ScrollView(.vertical, showsIndicators: false) {
            VStack(spacing: 15) {
                TRProfileHeader(
                    coinTotal: summary.coinTotal,
                    onSettingsTapped: onSettingsTapped,
                    onAddCurrencyTapped: onAddCurrencyTapped
                )
                .padding(.bottom, 2)

                TRProfileHeroCard(summary: summary)

                TRProfileStatsCard(summary: summary)

                TRProfileAchievementPreviewCard(
                    achievements: summary.achievements,
                    onViewAllTapped: showAchievementsPlaceholder
                )

                TRProfileCollectionCard(
                    selections: summary.collectionSelections,
                    onCustomizeTapped: onCustomizeTapped
                )

                TRProfileRewardProgressCard(rewardProgress: summary.rewardProgress)

                TRProfileActionButtons(
                    onEditProfileTapped: showEditProfilePlaceholder,
                    onAchievementsTapped: showAchievementsPlaceholder
                )
                .padding(.top, 2)
                .padding(.bottom, 14)
            }
            .frame(maxWidth: 760)
            .frame(maxWidth: .infinity)
            .padding(.horizontal, 20)
            .padding(.top, 4)
            .padding(.bottom, 10)
        }
        .background {
            LinearGradient(
                colors: [
                    Color.white.opacity(0.24),
                    Color(red: 0.69, green: 0.89, blue: 0.80).opacity(0.12)
                ],
                startPoint: .top,
                endPoint: .bottom
            )
            .ignoresSafeArea()
        }
        .alert(item: $activePlaceholder) { placeholder in
            Alert(
                title: Text(placeholder.title),
                message: Text(placeholder.message),
                dismissButton: .default(Text("OK"))
            )
        }
    }

    private func showEditProfilePlaceholder() {
        onEditProfileTapped()
        activePlaceholder = .editProfile
    }

    private func showAchievementsPlaceholder() {
        onAchievementsTapped()
        activePlaceholder = .achievements
    }
}

private enum ProfilePlaceholderAlert: Identifiable {
    case editProfile
    case achievements

    var id: String {
        title
    }

    var title: String {
        switch self {
        case .editProfile:
            "Edit Profile"
        case .achievements:
            "Achievements"
        }
    }

    var message: String {
        switch self {
        case .editProfile:
            "Profile editing coming soon."
        case .achievements:
            "Full achievements coming soon."
        }
    }
}

#Preview("Profile Screen") {
    ZStack {
        SpriteImage(name: "background")
            .scaledToFill()
            .ignoresSafeArea()

        ProfileScreen(
            summary: .conceptPreview,
            onSettingsTapped: {},
            onAddCurrencyTapped: {},
            onEditProfileTapped: {},
            onAchievementsTapped: {},
            onCustomizeTapped: {}
        )
    }
}

#Preview("Profile Screen Empty") {
    ZStack {
        SpriteImage(name: "background")
            .scaledToFill()
            .ignoresSafeArea()

        ProfileScreen(
            summary: .emptyPreview,
            onSettingsTapped: {},
            onAddCurrencyTapped: {},
            onEditProfileTapped: {},
            onAchievementsTapped: {},
            onCustomizeTapped: {}
        )
    }
}
