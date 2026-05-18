import Foundation
@testable import TinyRoutes

struct TestLevelCatalog {
    private let decoder: JSONDecoder

    init(decoder: JSONDecoder = JSONDecoder()) {
        self.decoder = decoder
    }

    func loadAllProductionLevels() throws -> [LevelData] {
        let urls = productionLevelFileURLs()
        return try urls.map { fileURL in
            let data = try Data(contentsOf: fileURL)
            return try decoder.decode(LevelData.self, from: data)
        }
    }

    private func productionLevelFileURLs() -> [URL] {
        let urls = bundleCandidates
            .flatMap { bundle in
                (bundle.urls(forResourcesWithExtension: "json", subdirectory: "Levels") ?? [])
                    + (bundle.urls(forResourcesWithExtension: "json", subdirectory: nil) ?? [])
            }
            .filter { $0.deletingPathExtension().lastPathComponent.hasPrefix("level_") }

        var seen = Set<URL>()
        return urls
            .filter { seen.insert($0).inserted }
            .sorted { $0.lastPathComponent < $1.lastPathComponent }
    }

    private var bundleCandidates: [Bundle] {
        [Bundle(for: BundleMarker.self), Bundle.main]
    }
}

private final class BundleMarker {}
