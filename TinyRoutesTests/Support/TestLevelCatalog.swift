import Foundation
@testable import TinyRoutes

struct TestLevelCatalog {
    private let decoder = JSONDecoder()

    func loadAllProductionLevels() throws -> [LevelData] {
        let repository = LevelRepository(bundle: try bundledLevelsBundle())
        return try repository.loadAllLevels()
            .sorted { $0.id < $1.id }
    }

    func loadLevel(levelID: String, from directory: URL) throws -> LevelData {
        let url = directory.appendingPathComponent("\(levelID).json")
        let data = try Data(contentsOf: url)
        return try decoder.decode(LevelData.self, from: data)
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
