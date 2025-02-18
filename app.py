import streamlit as st
import pandas as pd
import pdfplumber
import io
import re

def login_page():
    if st.session_state.get("logged_in"):
        return True
    
    st.title("Login Convert PDF FP To Excel")
    username = st.text_input("Username", key="username")
    password = st.text_input("Password", type="password", key="password")
    login_btn = st.button("Login")
    
    if (username and password) and (login_btn or st.session_state.get("attempt_login")):
        if (username == "admin" and password == "admin") or (username == "demo" and password == "123456"):
            st.session_state["logged_in"] = True
            st.session_state["user"] = username
            st.rerun()
        else:
            st.error("Username atau password salah!")
            st.session_state["attempt_login"] = False
    
    return False

def extract_data_from_pdf(pdf_file, tanggal_faktur):
    data = []
    total_nama_barang_detected = 0
    total_nama_barang_extracted = 0
    
    no_fp, nama_penjual, nama_pembeli = None, None, None
    
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                no_fp_match = re.search(r'Kode dan Nomor Seri Faktur Pajak:\s*(\d+)', text)
                if no_fp_match:
                    no_fp = no_fp_match.group(1)
                
                penjual_match = re.search(r'Nama\s*:\s*([\w\s\-.,&]+)\nAlamat', text)
                if penjual_match:
                    nama_penjual = penjual_match.group(1).strip()
                
                pembeli_match = re.search(r'Pembeli Barang Kena Pajak/Penerima Jasa Kena Pajak:\s*Nama\s*:\s*([\w\s\-.,&]+)\nAlamat', text)
                if pembeli_match:
                    nama_pembeli = pembeli_match.group(1).strip()
            
            table = page.extract_table()
            if table:
                for row in table:
                    if len(row) >= 4 and row[0] and row[0].isdigit():
                        total_nama_barang_detected += 1
                        
                        nama_barang = row[2].strip() if row[2] else ""
                        
                        if nama_barang:
                            data.append([
                                no_fp if no_fp else "Tidak ditemukan", 
                                nama_penjual if nama_penjual else "Tidak ditemukan", 
                                nama_pembeli if nama_pembeli else "Tidak ditemukan", 
                                nama_barang,
                                tanggal_faktur  
                            ])
                            total_nama_barang_extracted += 1
    
    if total_nama_barang_detected != total_nama_barang_extracted:
        st.warning(f"Perbedaan jumlah data: Ditemukan {total_nama_barang_detected} baris nama barang, tetapi hanya {total_nama_barang_extracted} berhasil diekstrak.")
    
    return data

if __name__ == "__main__":
    if login_page():
        st.title("Konversi Faktur Pajak PDF ke Excel")
        uploaded_files = st.file_uploader("Upload Faktur Pajak (PDF, bisa lebih dari satu)", type=["pdf"], accept_multiple_files=True)
        
        if uploaded_files:
            all_data = []
            file_dict = {file.name: file for file in uploaded_files}
            selected_files = st.multiselect("Pilih file yang ingin dihapus", list(file_dict.keys()))
            
            if st.button("Hapus File yang Dipilih"):
                for file_name in selected_files:
                    del file_dict[file_name]
                uploaded_files = list(file_dict.values())
                st.rerun()
            
            for uploaded_file in uploaded_files:
                tanggal_faktur = "2025-02-18"  # Contoh, bisa diubah sesuai ekstraksi tanggal faktur
                extracted_data = extract_data_from_pdf(uploaded_file, tanggal_faktur)
                if extracted_data:
                    all_data.extend(extracted_data)
            
            if all_data:
                df = pd.DataFrame(all_data, columns=["No FP", "Nama Penjual", "Nama Pembeli", "Nama Barang", "Tanggal Faktur"])
                df.index = df.index + 1  
                
                st.write("### Pratinjau Data yang Diekstrak")
                st.dataframe(df)
                
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=True, sheet_name='Faktur Pajak')
                output.seek(0)
                
                st.download_button(label="\U0001F4E5 Unduh Excel", data=output, file_name="Faktur_Pajak.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            else:
                st.error("Gagal mengekstrak data. Pastikan format faktur sesuai.")
