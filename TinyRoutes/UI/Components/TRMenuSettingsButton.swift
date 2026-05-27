import SwiftUI

struct TRMenuSettingsButton: View {
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Image(systemName: "gearshape.fill")
                .font(.system(size: 28, weight: .bold))
                .foregroundStyle(TRGameplayStyle.Colors.primaryBlue)
                .frame(width: 64, height: 64)
                .background {
                    Circle()
                        .fill(.white.opacity(0.92))
                        .overlay {
                            Circle()
                                .stroke(.white.opacity(0.75), lineWidth: 1)
                        }
                        .shadow(color: .black.opacity(0.08), radius: 10, x: 0, y: 5)
                }
        }
        .buttonStyle(.plain)
        .accessibilityLabel(Text("Settings"))
    }
}

#Preview("Menu Settings Button") {
    TRMenuSettingsButton(action: {})
        .padding(20)
        .background(Color(red: 0.86, green: 0.94, blue: 0.98))
}
