import SwiftUI

struct TRBottomNavigationBar: View {
    let selectedTab: TRBottomTab
    let onTabSelected: (TRBottomTab) -> Void

    private let selectedColor = Color(red: 0.05, green: 0.48, blue: 0.95)
    private let unselectedColor = Color(red: 0.38, green: 0.48, blue: 0.62)

    var body: some View {
        HStack(spacing: 0) {
            ForEach(TRBottomTab.allCases, id: \.title) { tab in
                button(for: tab)
            }
        }
        .padding(.horizontal, 10)
        .padding(.top, 10)
        .padding(.bottom, 12)
        .background {
            RoundedRectangle(cornerRadius: 28, style: .continuous)
                .fill(.white.opacity(0.94))
                .overlay {
                    RoundedRectangle(cornerRadius: 28, style: .continuous)
                        .stroke(.white.opacity(0.70), lineWidth: 1)
                }
                .shadow(color: .black.opacity(0.10), radius: 12, x: 0, y: 6)
        }
        .padding(.horizontal, 16)
        .padding(.bottom, 8)
    }

    private func button(for tab: TRBottomTab) -> some View {
        let isSelected = tab == selectedTab
        let foregroundColor = isSelected ? selectedColor : unselectedColor

        return Button {
            onTabSelected(tab)
        } label: {
            VStack(spacing: 5) {
                Capsule()
                    .fill(isSelected ? selectedColor : .clear)
                    .frame(width: 26, height: 4)
                    .padding(.bottom, 2)

                Image(systemName: tab.systemImage)
                    .font(.system(size: 22, weight: isSelected ? .semibold : .medium))

                Text(tab.title)
                    .font(.system(size: 12, weight: isSelected ? .semibold : .medium))
            }
            .foregroundStyle(foregroundColor)
            .frame(maxWidth: .infinity, minHeight: 58)
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(Text("\(tab.title) tab"))
        .accessibilityValue(Text(isSelected ? "Selected" : "Not selected"))
        .accessibilityAddTraits(isSelected ? [.isSelected] : [])
    }
}

struct TRBottomNavigationBar_Previews: PreviewProvider {
    static var previews: some View {
        ZStack {
            Color(red: 0.84, green: 0.93, blue: 0.98)
                .ignoresSafeArea()

            VStack {
                Spacer()
                TRBottomNavigationBar(selectedTab: .home, onTabSelected: { _ in })
            }
        }
    }
}
