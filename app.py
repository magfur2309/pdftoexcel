import streamlit as st
import pandas as pd
import pdfplumber
import io
import re

def login():
    st.title("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    
    if st.button("Login"):
        if username == "admin" and password == "admin":
            st.session_state["logged_in"] = True
        else:
            st.error("Username atau password salah")

def find_invoice_date(pdf_file):
    month_map = {
        "Januari": "01", "Februari": "02", "Maret": "03", "April": "04", "Mei": "05", "Juni": "06", 
        "Juli": "07", "Agustus": "08", "September": "09", "Oktober": "10", "November": "11", "Desember": "12"
    }
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                date_match = re.search(r'(\d{1,2})\s*(Januari|Februari|Maret|April|Mei|Juni|Juli|Agustus|September|Oktober|November|Desember)\s*(\d{4})', text, re.IGNORECASE)
                if date_match:
                    day, month, year = date_match.groups()
                    return f"{day.zfill(2)}/{month_map[month]}/{year}"
    return "Tidak ditemukan"

def extract_data_from_pdf(pdf_file, tanggal_faktur):
    data = []
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            table = page.extract_table()
            if table:
                for row in table:
                    if len(row) >= 6 and row[0] and row[0].isdigit():
                        nama_barang = " ".join(row[2].split("\n")).strip()
                        
                        try:
                            harga = int(re.sub(r'[^0-9]', '', row[3])) if row[3] else 0
                            qty = int(re.sub(r'[^0-9]', '', row[4])) if row[4] else 0
                        except ValueError:
                            harga, qty = 0, 0
                        
                        unit = row[5] if len(row) > 5 and row[5] else "Unknown"
                        total = harga * qty
                        dpp = total / 1.11
                        ppn = total - dpp
                        
                        data.append(["Tidak ditemukan", "Tidak ditemukan", "Tidak ditemukan", nama_barang, harga, unit, qty, total, 0, dpp, ppn, tanggal_faktur])
    return data

def main_app():
    st.title("Konversi Faktur Pajak PDF ke Excel")
    uploaded_files = st.file_uploader("Upload Faktur Pajak (PDF, bisa lebih dari satu)", type=["pdf"], accept_multiple_files=True)
    
    if uploaded_files:
        all_data = []
        for uploaded_file in uploaded_files:
            tanggal_faktur = find_invoice_date(uploaded_file)
            extracted_data = extract_data_from_pdf(uploaded_file, tanggal_faktur)
            
            if extracted_data:
                all_data.extend(extracted_data)
        
        if all_data:
            df = pd.DataFrame(all_data, columns=["No FP", "Nama Penjual", "Nama Pembeli", "Nama Barang", "Harga", "Unit", "QTY", "Total", "Potongan Harga", "DPP", "PPN", "Tanggal Faktur"])
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
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
    
    if not st.session_state["logged_in"]:
        login()
    else:
        main_app()
