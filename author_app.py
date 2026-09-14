import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import os
import json
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# Khóa Master (32 bytes = 256 bits) cho thuật toán AES-GCM (KHỚP HOÀN TOÀN VỚI MÃ NGUỒN CryptoKit SWIFT BÊN KIA)
MASTER_KEY = b'12345678901234567890123456789012' 

class AdminAppSwiftBridge(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("PDFLock Admin Python (Đóng gói cho macOS Swift)")
        self.geometry("750x650")
        
        # UI
        self.btn_build = ctk.CTkButton(self, text="CHỌN & MÃ HÓA PDF (.khoa)", command=self.encrypt_files)
        self.btn_build.pack(pady=20)
        
        self.lbl = ctk.CTkLabel(self, text="Machine ID của Mac (VD: MAC-XXXX):")
        self.lbl.pack()
        self.entry_mid = ctk.CTkEntry(self, width=250)
        self.entry_mid.pack(pady=5)
        
        self.chk_print_var = tk.BooleanVar(value=False)
        self.chk_print = ctk.CTkCheckBox(self, text="Cho phép IN", variable=self.chk_print_var)
        self.chk_print.pack(pady=10)
        
        self.btn_key = ctk.CTkButton(self, text="TẠO LICENSE KEY", command=self.gen_key, fg_color="green")
        self.btn_key.pack(pady=20)
        
        self.txt_out = ctk.CTkTextbox(self, height=120, width=500)
        self.txt_out.pack(pady=20)
        
    def encrypt_files(self):
        files = filedialog.askopenfilenames(filetypes=[("PDF", "*.pdf")])
        if not files: return
        aesgcm = AESGCM(MASTER_KEY)
        for f in files:
            with open(f, "rb") as fd: data = fd.read()
            # CryptoKit AES.GCM.SealedBox(combined:) nhận 12 bytes nonce ở đầu + ciphertext + 16 bytes tag ở cuối
            nonce = os.urandom(12)
            ciphertext = aesgcm.encrypt(nonce, data, None)
            combined = nonce + ciphertext 
            
            out_file = f.replace(".pdf", ".khoa")
            with open(out_file, "wb") as fd: fd.write(combined)
        messagebox.showinfo("OK", f"Đã mã hóa {len(files)} file PDF sang đuôi .khoa")
            
    def gen_key(self):
        mid = self.entry_mid.get().strip()
        if not mid:
            messagebox.showerror("Lỗi", "Vui lòng nhập Machine ID!")
            return
            
        aesgcm = AESGCM(MASTER_KEY)
        license_data = {
            "machine_id": mid, 
            "expiry": "PERMANENT", 
            "can_print": self.chk_print_var.get()
        }
        data_json = json.dumps(license_data).encode('utf-8')
        
        nonce = os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, data_json, None)
        combined = nonce + ciphertext
        
        # Encode Base64 xuất dạng text cho khách
        b64 = base64.b64encode(combined).decode('utf-8')
        self.txt_out.delete("0.0", "end")
        self.txt_out.insert("0.0", b64)

if __name__ == "__main__":
    app = AdminAppSwiftBridge()
    app.mainloop()
