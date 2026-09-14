import SwiftUI

struct ActivationView: View {
    @Binding var isActivated: Bool
    @State private var licenseKey: String = ""
    @State private var showError = false
    
    var body: some View {
        VStack(spacing: 20) {
            Image(systemName: "lock.laptopcomputer")
                .resizable()
                .scaledToFit()
                .frame(width: 80, height: 80)
                .foregroundColor(.blue)
            
            Text("Kích Hoạt Tài Liệu")
                .font(.title)
                .bold()
            
            Text("Máy của bạn là: \(MachineID.get())")
                .font(.headline)
                .foregroundColor(.red)
                .textSelection(.enabled) // Cho phép copy mã thiết bị gửi Admin
            
            Text("Hãy nhập Key vào đây:")
            TextField("License Key...", text: $licenseKey)
                .textFieldStyle(RoundedBorderTextFieldStyle())
                .frame(width: 400)
            
            Button("KÍCH HOẠT") {
                let trimmedKey = licenseKey.trimmingCharacters(in: .whitespacesAndNewlines)
                if CryptoManager.verifyLicense(key: trimmedKey) {
                    UserDefaults.standard.set(trimmedKey, forKey: "LicenseKey")
                    isActivated = true
                } else {
                    showError = true
                }
            }
            .buttonStyle(.borderedProminent)
            .alert("Lỗi Kích Hoạt", isPresented: $showError) {
                Button("OK", role: .cancel) { }
            } message: {
                Text("License Key không đúng với máy này!")
            }
        }
        .frame(width: 600, height: 400)
    }
}
