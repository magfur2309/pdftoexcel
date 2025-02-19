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

def extract_tanggal_faktur(pdf):
    month_mapping = {
        "Januari": "01", "Februari": "02", "Maret": "03", "April": "04",
        "Mei": "05", "Juni": "06", "Juli": "07", "Agustus": "08",
        "September": "09", "Oktober": "10", "November": "11", "Desember": "12"
    }
    tanggal_faktur = "Tidak ditemukan"
    
    with pdfplumber.open(pdf) as pdf_obj:
        for page in pdf_obj.pages:
            text = page.extract_text()
            if text:
                date_match = re.search(r'(\d{1,2})\s*(Januari|Februari|Maret|April|Mei|Juni|Juli|Agustus|September|Oktober|November|Desember)\s*(\d{4})', text, re.IGNORECASE)
                if date_match:
                    day, month, year = date_match.groups()
                    tanggal_faktur = f"{year}-{month_mapping[month]}-{day.zfill(2)}"
                    break  
    
    return tanggal_faktur

def extract_data_from_pdf(pdf_file, tanggal_faktur):
    data = []
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
                    if len(row) >= 4 and row[0].isdigit():
                        nama_barang = row[2].strip()
                        harga = int(row[3].replace('.', '').replace(',', '.')) if row[3] else 0
                        qty = int(row[4].replace('.', '').replace(',', '.')) if row[4] else 0
                        total = harga * qty
                        dpp = total / 1.11
                        ppn = total - dpp
                        
                        data.append([
                            no_fp if no_fp else "Tidak ditemukan", 
                            nama_penjual if nama_penjual else "Tidak ditemukan", 
                            nama_pembeli if nama_pembeli else "Tidak ditemukan", 
                            nama_barang, harga, qty, total, dpp, ppn, tanggal_faktur
                        ])
    return data

def main_app():
    st.title("Konversi Faktur Pajak PDF ke Excel")
    uploaded_files = st.file_uploader("Upload Faktur Pajak (PDF, bisa lebih dari satu)", type=["pdf"], accept_multiple_files=True)
    
    if uploaded_files:
        all_data = []
        for uploaded_file in uploaded_files:
            tanggal_faktur = extract_tanggal_faktur(uploaded_file)  
            extracted_data = extract_data_from_pdf(uploaded_file, tanggal_faktur)
            if extracted_data:
                all_data.extend(extracted_data)
                ditemukan = len(extracted_data)
                diekstrak = sum(1 for item in extracted_data if item[3])
                if ditemukan > 0 and ditemukan != diekstrak:
                    st.warning(f"Jumlah item tidak cocok untuk {uploaded_file.name}: Ditemukan {ditemukan}, diekstrak {diekstrak}")
        
        if all_data:
            df = pd.DataFrame(all_data, columns=["No FP", "Nama Penjual", "Nama Pembeli", "Nama Barang", "Harga", "QTY", "Total", "DPP", "PPN", "Tanggal Faktur"])
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

if __name__ == "__main__":
    if login_page():
        main_app()
