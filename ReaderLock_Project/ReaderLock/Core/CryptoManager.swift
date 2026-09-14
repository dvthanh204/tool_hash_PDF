import Foundation
import CryptoKit

struct CryptoManager {
    static let secretSalt = "MY_SUPER_SECRET_2026"
    
    static func getAESKey() -> SymmetricKey {
        let digest = SHA256.hash(data: Data(secretSalt.utf8))
        return SymmetricKey(data: Data(digest))
    }
    
    static func verifyLicense(key: String, machineID: String) -> (isValid: Bool, message: String, version: Int) {
        let parts = key.split(separator: "-").map { String($0) }
        
        // V1-PERM-HASH
        guard parts.count == 3, parts[0].hasPrefix("V") else {
            return (false, "Mật khẩu không đúng định dạng!", 0)
        }
        
        let versionStr = parts[0].dropFirst()
        guard let version = Int(versionStr) else {
            return (false, "Phiên bản không hợp lệ!", 0)
        }
        
        let expiryStr = parts[1]
        let codeHash = parts[2]
        
        let raw = "\(machineID)_\(version)_\(expiryStr)_\(secretSalt)"
        let expectedHash = SHA256.hash(data: Data(raw.utf8))
            .map { String(format: "%02x", $0) }.joined().prefix(8).uppercased()
            
        if codeHash != expectedHash {
            return (false, "Mật khẩu không hợp lệ cho PC này!", 0)
        }
        
        if expiryStr != "PERM" {
            let formatter = DateFormatter()
            formatter.dateFormat = "yyMMdd"
            formatter.timeZone = TimeZone.current
            
            if let expDate = formatter.date(from: expiryStr) {
                let calendar = Calendar.current
                if let endOfDay = calendar.date(bySettingHour: 23, minute: 59, second: 59, of: expDate) {
                    if Date() > endOfDay {
                        return (false, "Mật khẩu này ĐÃ HẾT HẠN SỬ DỤNG!", 0)
                    }
                }
            } else {
                return (false, "Lỗi đọc thời hạn.", 0)
            }
        }
        
        // Kiểm tra version local cache nếu có
        let savedVersion = UserDefaults.standard.integer(forKey: "LicenseVersion")
        if version < savedVersion {
            return (false, "Mật khẩu (V\(version)) ĐÃ BỊ THU HỒI. Hãy dùng mã tối thiểu V\(savedVersion).", 0)
        }
        
        return (true, "Hợp lệ", version)
    }
    
    static func decryptPayload(data: Data) -> Data? {
        do {
            let key = getAESKey()
            let sealedBox = try AES.GCM.SealedBox(combined: data)
            let decryptedData = try AES.GCM.open(sealedBox, using: key)
            return decryptedData
        } catch {
            print("Lỗi giải mã: \(error)")
            return nil
        }
    }
}
