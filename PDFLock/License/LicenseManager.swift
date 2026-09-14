import Foundation
import SwiftUI

class LicenseManager: ObservableObject {
    @Published var isActivated: Bool = false
    @Published var currentLicense: License?
    
    init() {
        checkSavedLicense()
    }
    
    func checkSavedLicense() {
        if let keyStr = KeychainManager.load(key: "PDFLockLicense"),
           let license = parseKey(keyStr) {
            if license.isValid {
                self.currentLicense = license
                self.isActivated = true
            }
        }
    }
    
    func activate(with keyStr: String) -> Bool {
        if let license = parseKey(keyStr), license.isValid {
            KeychainManager.save(key: "PDFLockLicense", data: keyStr)
            self.currentLicense = license
            self.isActivated = true
            return true
        }
        return false
    }
    
    private func parseKey(_ keyStr: String) -> License? {
        guard let data = Data(base64Encoded: keyStr) else { return nil }
        do {
            let decrypted = try AESManager.shared.decrypt(data: data)
            let license = try JSONDecoder().decode(License.self, from: decrypted)
            return license
        } catch {
            return nil
        }
    }
}
