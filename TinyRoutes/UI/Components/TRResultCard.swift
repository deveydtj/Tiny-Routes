import SwiftUI

struct TRResultCard<Content: View>: View {
    let content: Content

    init(@ViewBuilder content: () -> Content) {
        self.content = content()
    }

    var body: some View {
        content
            .padding(.horizontal, 18)
            .padding(.top, 46)
            .padding(.bottom, 18)
            .frame(maxWidth: 380)
            .background {
                RoundedRectangle(cornerRadius: TRGameplayStyle.Metrics.resultCardCornerRadius, style: .continuous)
                    .fill(.white.opacity(0.90))
                    .overlay {
                        RoundedRectangle(cornerRadius: TRGameplayStyle.Metrics.resultCardCornerRadius, style: .continuous)
                            .stroke(TRGameplayStyle.Colors.resultCardStroke, lineWidth: 1.5)
                    }
                    .shadow(color: Color(red: 0.12, green: 0.25, blue: 0.36).opacity(0.14), radius: 24, x: 0, y: 14)
                    .shadow(color: .white.opacity(0.70), radius: 1, x: 0, y: -1)
            }
    }
}

#Preview("Result Card") {
    ZStack {
        TRResultScreenBackground()
        TRResultCard {
            Text("Level Complete!")
                .font(.system(size: 28, weight: .black, design: .rounded))
        }
        .padding()
    }
}
