import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import os
import shutil
import zipfile
import json
import base64
from datetime import datetime
from cryptography.fernet import Fernet

# Khóa Master để mã hóa tài liệu và mã hóa Key. (Trong thực tế nên bảo mật khóa này, giống giữa Client và Admin)
MASTER_KEY = b'-hZzUf1Mkx1t0wM_hX2b6F4kS_J5LqZcQk9d-4S5X88='
fernet = Fernet(MASTER_KEY)

class AdminApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("PDFLock Admin (macOS Target)")
        self.geometry("750x650")
        ctk.set_appearance_mode("dark")
        
        # Tạo Tabs
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(padx=20, pady=20, fill="both", expand=True)
        
        self.tab_package = self.tabview.add("Đóng Gói PDF")
        self.tab_license = self.tabview.add("Cấp Key & Quản Lý")
        
        self.setup_package_tab()
        self.setup_license_tab()
        
    def setup_package_tab(self):
        # 1. Chọn PDF
        self.pdf_paths = []
        
        btn_frame = ctk.CTkFrame(self.tab_package)
        btn_frame.pack(fill="x", pady=10)
        
        self.btn_sel_pdf = ctk.CTkButton(btn_frame, text="Chọn file PDF", command=self.select_pdf)
        self.btn_sel_pdf.pack(side="left", padx=10)
        
        self.lbl_pdf_count = ctk.CTkLabel(btn_frame, text="Chưa chọn file nào.")
        self.lbl_pdf_count.pack(side="left", padx=10)
        
        # 2. Chọn App macOS gốc (.app)
        app_frame = ctk.CTkFrame(self.tab_package)
        app_frame.pack(fill="x", pady=10)
        
        self.viewer_app_path = ""
        self.btn_sel_app = ctk.CTkButton(app_frame, text="Chọn PDFLock_Viewer.app", command=self.select_app)
        self.btn_sel_app.pack(side="left", padx=10)
        
        self.lbl_app_path = ctk.CTkLabel(app_frame, text="Chưa chọn Viewer App.")
        self.lbl_app_path.pack(side="left", padx=10)
        
        # 3. Chọn Output Folder
        out_frame = ctk.CTkFrame(self.tab_package)
        out_frame.pack(fill="x", pady=10)
        
        self.output_dir = ""
        self.btn_sel_out = ctk.CTkButton(out_frame, text="Thư mục Output", command=self.select_output)
        self.btn_sel_out.pack(side="left", padx=10)
        
        self.lbl_out_dir = ctk.CTkLabel(out_frame, text="Chưa chọn thư mục Output.")
        self.lbl_out_dir.pack(side="left", padx=10)
        
        # Nút Build
        self.btn_build = ctk.CTkButton(self.tab_package, text="MÃ HÓA & ĐÓNG GÓI ZIP CHO MACOS", 
                                       command=self.build_package, fg_color="green")
        self.btn_build.pack(pady=30)
        
    def select_pdf(self):
        paths = filedialog.askopenfilenames(filetypes=[("PDF Files", "*.pdf")])
        if paths:
            self.pdf_paths = list(paths)
            self.lbl_pdf_count.configure(text=f"Đã chọn {len(self.pdf_paths)} file PDF.")
            
    def select_app(self):
        path = filedialog.askdirectory(title="Chọn bundle PDFLock_Viewer.app")
        # Trên Windows, folder macOS app bundle sẽ là thư mục .app
        if path and str(path).endswith(".app"):
            self.viewer_app_path = path
            self.lbl_app_path.configure(text=os.path.basename(path))
        else:
            messagebox.showerror("Lỗi", "Vui lòng chọn thư mục bundle đuôi .app của ứng dụng macOS")
            
    def select_output(self):
        path = filedialog.askdirectory()
        if path:
            self.output_dir = path
            self.lbl_out_dir.configure(text=path)
            
    def build_package(self):
        if not self.pdf_paths or not self.viewer_app_path or not self.output_dir:
            messagebox.showerror("Lỗi", "Vui lòng chọn đầy đủ PDF đầu vào, Viewer App (.app) và thư mục Output!")
            return
            
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            package_name = f"PDFLock_Mac_Release_{timestamp}"
            package_path = os.path.join(self.output_dir, package_name)
            os.makedirs(package_path, exist_ok=True)
            
            # Mã hóa các file PDF và lưu thành đuôi .khoa
            encrypted_files = []
            for pdf in self.pdf_paths:
                with open(pdf, "rb") as f:
                    pdf_data = f.read()
                encrypted_data = fernet.encrypt(pdf_data)
                
                base_name = os.path.basename(pdf).replace(".pdf", ".khoa")
                out_khoa_path = os.path.join(package_path, base_name)
                with open(out_khoa_path, "wb") as f:
                    f.write(encrypted_data)
                encrypted_files.append(out_khoa_path)
            
            # Copy Viewer App (folder .app)
            dest_app = os.path.join(package_path, os.path.basename(self.viewer_app_path))
            if os.path.exists(dest_app):
                shutil.rmtree(dest_app)
            shutil.copytree(self.viewer_app_path, dest_app)
            
            # Nén tất cả tài nguyên thành 1 file ZIP để phân phối dễ dàng cho macOS
            zip_filename = os.path.join(self.output_dir, f"{package_name}.zip")
            with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Zip .khoa files
                for khoa in encrypted_files:
                    zipf.write(khoa, arcname=os.path.basename(khoa))
                # Zip app bundle
                for root, dirs, files in os.walk(dest_app):
                    for file in files:
                        file_path = os.path.join(root, file)
                        # Giữ nguyên cấu trúc thư mục của .app bên trong ZIP
                        arcname = os.path.join(os.path.basename(dest_app), os.path.relpath(file_path, dest_app))
                        zipf.write(file_path, arcname)
                        
            messagebox.showinfo("Thành công", f"Đã đóng gói thành công file {zip_filename}\nBạn có thể gửi file ZIP này cho khách hàng macOS.")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Xuất hiện lỗi khi đóng gói: {str(e)}")

    def setup_license_tab(self):
        # Thông tin Machine ID
        self.lbl_mid = ctk.CTkLabel(self.tab_license, text="Machine ID của khách hàng (VD: MAC-XXXXX):")
        self.lbl_mid.pack(pady=(10, 0))
        self.entry_mid = ctk.CTkEntry(self.tab_license, width=300)
        self.entry_mid.pack(pady=5)
        
        # Ngày hết hạn
        self.lbl_exp = ctk.CTkLabel(self.tab_license, text="Ngày hết hạn (Định dạng YYYY-MM-DD): \n(Để trống nếu muốn cấp vĩnh viễn)")
        self.lbl_exp.pack(pady=(10, 0))
        self.entry_exp = ctk.CTkEntry(self.tab_license, width=150)
        self.entry_exp.pack(pady=5)
        
        # Quyền In ấn
        self.var_print = tk.BooleanVar(value=False)
        self.chk_print = ctk.CTkCheckBox(self.tab_license, text="Cho phép IN tài liệu (Gửi ngầm trong macOS)", variable=self.var_print)
        self.chk_print.pack(pady=10)
        
        # Nút tạo Key
        self.btn_gen = ctk.CTkButton(self.tab_license, text="TẠO LICENSE KEY", command=self.generate_key)
        self.btn_gen.pack(pady=10)
        
        # Kết quả Key
        self.lbl_key = ctk.CTkLabel(self.tab_license, text="License Key Cấp Cho Khách Hàng:")
        self.lbl_key.pack()
        self.txt_key = ctk.CTkTextbox(self.tab_license, height=100, width=540)
        self.txt_key.pack(pady=5)
        
        # Tính năng Blacklist
        self.btn_black = ctk.CTkButton(self.tab_license, text="Thêm Machine ID vào Blacklist (Tạo blacklist.json)", 
                                       command=self.add_blacklist, fg_color="red")
        self.btn_black.pack(pady=20)

    def generate_key(self):
        mid = self.entry_mid.get().strip()
        if not mid:
            messagebox.showerror("Lỗi", "Vui lòng nhập Machine ID của khách hàng trước khi tạo key.")
            return
            
        expiry = self.entry_exp.get().strip() or "PERMANENT"
        can_print = self.var_print.get()
        
        # Lưu vào dict JSON
        license_data = {
            "machine_id": mid,
            "expiry": expiry,
            "can_print": can_print
        }
        
        # Mã hóa Key (Dùng AES qua Fernet)
        data_json = json.dumps(license_data).encode('utf-8')
        encrypted_key = fernet.encrypt(data_json)
        encoded_key = base64.urlsafe_b64encode(encrypted_key).decode('utf-8')
        
        # Hiển thị lên UI
        self.txt_key.delete("0.0", "end")
        self.txt_key.insert("0.0", encoded_key)
        
    def add_blacklist(self):
        mid = self.entry_mid.get().strip()
        if not mid:
            messagebox.showerror("Lỗi", "Vui lòng nhập Machine ID cần cho vào Blacklist.")
            return
        
        bl_file = "blacklist.json" # Có thể đổi đường dẫn mong muốn
        blacklist = []
        if os.path.exists(bl_file):
            with open(bl_file, "r") as f:
                blacklist = json.load(f)
                
        if mid not in blacklist:
            blacklist.append(mid)
            with open(bl_file, "w") as f:
                json.dump(blacklist, f)
            messagebox.showinfo("Thành công", f"Đã thêm {mid} vào {bl_file}.\n(Hãy đính kèm blacklist.json chung với bộ cài hoặc ZIP của khách để chặn).")
        else:
            messagebox.showwarning("Cảnh báo", f"{mid} đã tồn tại trong blacklist!")

if __name__ == "__main__":
    app = AdminApp()
    app.mainloop()
