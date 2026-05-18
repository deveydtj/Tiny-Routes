import Foundation
@testable import TinyRoutes

struct TestLevelCatalog {
    func loadAllProductionLevels() throws -> [LevelData] {
        let repository = LevelRepository(bundle: try bundledLevelsBundle())
        return try repository.loadAllLevels()
            .filter { $0.id.hasPrefix("level_") }
            .sorted { $0.id < $1.id }
    }

    private func bundledLevelsBundle() throws -> Bundle {
        let bundles = [Bundle(for: BundleMarker.self), Bundle.main]
        if let bundle = bundles.first(where: { bundle in
            bundle.url(forResource: "level_001", withExtension: "json", subdirectory: "Levels") != nil
                || bundle.url(forResource: "level_001", withExtension: "json") != nil
        }) {
            return bundle
        }

        throw LevelRepositoryError.fileNotFound(id: "level_001")
    }
}

private final class BundleMarker {}
