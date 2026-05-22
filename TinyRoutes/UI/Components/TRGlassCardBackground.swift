import SwiftUI

struct TRGlassCardBackground: View {
    var cornerRadius: CGFloat = 24

    var body: some View {
        RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
            .fill(.white.opacity(0.88))
            .overlay {
                RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
                    .stroke(.white.opacity(0.65), lineWidth: 1)
            }
            .shadow(color: .black.opacity(0.10), radius: 16, x: 0, y: 8)
    }
}

#Preview("Glass Card Background") {
    Text("Placeholder Card")
        .font(.headline)
        .padding(18)
        .background {
            TRGlassCardBackground()
        }
        .padding()
        .background(Color(red: 0.78, green: 0.90, blue: 0.96))
}
