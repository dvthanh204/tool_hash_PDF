import Foundation

class PackageReader {
    static func readKhoaFile(url: URL) -> Data? {
        do {
            let encryptedData = try Data(contentsOf: url)
            let decryptedData = try AESManager.shared.decrypt(data: encryptedData)
            return decryptedData
        } catch {
            return nil
        }
    }
}
