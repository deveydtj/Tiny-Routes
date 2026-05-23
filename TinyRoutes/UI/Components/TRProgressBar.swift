import SwiftUI

struct TRProgressBar: View {
    let progress: CGFloat
    var height: CGFloat = 10
    var fillColor: Color = TRGameplayStyle.Colors.primaryBlue
    var trackColor: Color = Color(red: 0.82, green: 0.87, blue: 0.93)

    private var clampedProgress: CGFloat {
        min(max(progress, 0), 1)
    }

    var body: some View {
        GeometryReader { geometry in
            ZStack(alignment: .leading) {
                Capsule()
                    .fill(trackColor)

                Capsule()
                    .fill(fillColor)
                    .frame(width: geometry.size.width * clampedProgress)
            }
        }
        .frame(height: height)
        .accessibilityHidden(true)
    }
}

#Preview("Progress Bar") {
    VStack(spacing: 16) {
        TRProgressBar(progress: 0)
        TRProgressBar(progress: 0.55)
        TRProgressBar(progress: 1)
    }
    .padding(24)
    .background(Color(red: 0.86, green: 0.94, blue: 0.98))
}
