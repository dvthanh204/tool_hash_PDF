import Foundation
import CryptoKit

struct CryptoManager {
    static let staticKey = "12345678901234567890123456789012"
    
    static func verifyLicense(key: String) -> Bool {
        let mid = MachineID.get()
        let symmetricKey = SymmetricKey(data: Data(staticKey.utf8))
        
        // HMAC-SHA256 băm Machine ID
        let signature = HMAC<SHA256>.authenticationCode(for: Data(mid.utf8), using: symmetricKey)
        let signatureBase64 = Data(signature).base64EncodedString()
        
        return signatureBase64 == key
    }
    
    static func decryptPayload(data: Data) -> Data? {
        do {
            let key = SymmetricKey(data: Data(staticKey.utf8))
            // CryptoKit tự động phân tách phần Nonce 12-byte khởi đầu từ Combined Data
            let sealedBox = try AES.GCM.SealedBox(combined: data)
            let decryptedData = try AES.GCM.open(sealedBox, using: key)
            return decryptedData
        } catch {
            print("Lỗi giải mã AES-GCM: \(error)")
            return nil
        }
    }
}
