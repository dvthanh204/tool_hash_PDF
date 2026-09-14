import Foundation
import CryptoKit

class AESManager {
    // Shared Master Key (Chuẩn 32 ký tự = 256 bits). Phải khớp với author_app.py!
    static let shared = AESManager()
    let keyString = "12345678901234567890123456789012"
    
    func decrypt(data: Data) throws -> Data {
        let key = SymmetricKey(data: keyString.data(using: .utf8)!)
        let sealedBox = try AES.GCM.SealedBox(combined: data)
        let decryptedData = try AES.GCM.open(sealedBox, using: key)
        return decryptedData
    }
}
