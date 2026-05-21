import SwiftUI

struct TRBottomNavigationBar: View {
    let selectedTab: TRBottomTab
    let onTabSelected: (TRBottomTab) -> Void

    private let selectedColor = Color(red: 0.10, green: 0.56, blue: 0.97)
    private let unselectedColor = Color(red: 0.43, green: 0.51, blue: 0.64)

    var body: some View {
        HStack(spacing: 0) {
            ForEach(TRBottomTab.allCases, id: \.title) { tab in
                let isSelected = selectedTab == tab
                Button {
                    onTabSelected(tab)
                } label: {
                    VStack(spacing: 6) {
                        Capsule()
                            .fill(selectedColor)
                            .frame(width: 22, height: 4)
                            .opacity(isSelected ? 1 : 0)

                        Image(systemName: tab.systemImage)
                            .font(.system(size: 18, weight: isSelected ? .semibold : .medium))

                        Text(tab.title)
                            .font(.system(size: 12, weight: isSelected ? .semibold : .medium))
                    }
                    .frame(maxWidth: .infinity, minHeight: 56)
                    .foregroundStyle(isSelected ? selectedColor : unselectedColor)
                    .contentShape(Rectangle())
                }
                .buttonStyle(.plain)
                .accessibilityElement(children: .ignore)
                .accessibilityLabel("\(tab.title) tab")
                .accessibilityAddTraits(isSelected ? .isSelected : [])
            }
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 10)
        .background(
            RoundedRectangle(cornerRadius: 28, style: .continuous)
                .fill(.white.opacity(0.96))
                .overlay(
                    RoundedRectangle(cornerRadius: 28, style: .continuous)
                        .stroke(.white.opacity(0.8), lineWidth: 1)
                )
        )
        .shadow(color: .black.opacity(0.10), radius: 12, x: 0, y: 6)
        .padding(.horizontal, 16)
        .padding(.bottom, 8)
    }
}
