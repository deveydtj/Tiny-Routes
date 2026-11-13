import SwiftUI

struct TRProfileCollectionCard: View {
    let selections: [ProfileCollectionSelection]
    let onCustomizeTapped: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack {
                TRCozyCardTitle(title: "Collections")

                Spacer()

                Button(action: onCustomizeTapped) {
                    HStack(spacing: 5) {
                        Image(systemName: "pencil")
                        Text("Customize")
                    }
                    .font(.system(size: 13, weight: .semibold, design: .rounded))
                    .foregroundStyle(TRVillagePalette.teal)
                    .padding(.horizontal, 12)
                    .frame(height: 32)
                }
                .buttonStyle(MultiVanHUDButtonStyle(shape: AnyShape(Capsule())))
                .accessibilityLabel(Text("Customize collections"))
            }

            ViewThatFits(in: .horizontal) {
                HStack(spacing: 0) {
                    ForEach(Array(selections.enumerated()), id: \.element.id) { index, selection in
                        collectionItem(selection)
                        if index < selections.count - 1 {
                            TRCozyDivider()
                                .frame(height: 82)
                        }
                    }
                }

                VStack(spacing: 10) {
                    ForEach(selections) { selection in
                        collectionRow(selection)
                    }
                }
            }
        }
        .padding(18)
        .background {
            MultiVanHUDCardBackground(cornerRadius: 26)
        }
    }

    private func collectionItem(_ selection: ProfileCollectionSelection) -> some View {
        VStack(spacing: 8) {
            ZStack(alignment: .topTrailing) {
                TRProfileCollectionIcon(selection: selection)
                if selection.isSelected {
                    TRProfileCheckBadge(size: 18)
                        .offset(x: 4, y: -4)
                }
            }

            Text(selection.label)
                .font(.system(size: 12, weight: .semibold, design: .rounded))
                .foregroundStyle(TRVillagePalette.slate)
                .lineLimit(1)
                .minimumScaleFactor(0.68)

            Text(selection.value)
                .font(.system(size: 15, weight: .bold, design: .rounded))
                .foregroundStyle(TRVillagePalette.navy)
                .lineLimit(1)
                .minimumScaleFactor(0.72)
        }
        .frame(maxWidth: .infinity, minHeight: 110)
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(Text("\(selection.label), \(selection.value), selected"))
    }

    private func collectionRow(_ selection: ProfileCollectionSelection) -> some View {
        HStack(spacing: 12) {
            ZStack(alignment: .topTrailing) {
                TRProfileCollectionIcon(selection: selection, size: 48)
                if selection.isSelected {
                    TRProfileCheckBadge(size: 17)
                        .offset(x: 3, y: -3)
                }
            }

            VStack(alignment: .leading, spacing: 2) {
                Text(selection.label)
                    .font(.system(size: 12, weight: .semibold, design: .rounded))
                    .foregroundStyle(TRVillagePalette.slate)
                Text(selection.value)
                    .font(.system(size: 16, weight: .bold, design: .rounded))
                    .foregroundStyle(TRVillagePalette.navy)
            }

            Spacer()
        }
        .padding(12)
        .background {
            TRCozyWellBackground(cornerRadius: 18)
        }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(Text("\(selection.label), \(selection.value), selected"))
    }
}

#Preview("Collection Card") {
    TRProfileCollectionCard(
        selections: ProfileCollectionSelection.conceptDefaults,
        onCustomizeTapped: {}
    )
    .padding(20)
    .background(TRVillageSky())
}
