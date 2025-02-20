import streamlit as st
import pandas as pd
import pdfplumber
import io
import re

def find_invoice_date(pdf_file):
    """Mencari tanggal faktur dalam PDF, mulai dari halaman pertama."""
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

def extract_table_data(table):
    """Ekstrak data tabel secara lebih akurat."""
    data = []
    for row in table:
        if len(row) >= 9 and row[0].strip().isdigit():
            nama_barang = " ".join(row[1].split("\n")).strip() if row[1] else "Unknown"
            qty = int(row[2].replace(',', '').strip()) if row[2] and row[2].replace(',', '').isdigit() else 0
            unit = row[3].strip() if row[3] else "Unknown"
            harga = float(row[4].replace(',', '').strip()) if row[4] and row[4].replace(',', '').replace('.', '').isdigit() else 0
            potongan_harga = float(row[5].replace(',', '').strip()) if row[5] and row[5].replace(',', '').replace('.', '').isdigit() else 0
            total = float(row[6].replace(',', '').strip()) if row[6] and row[6].replace(',', '').replace('.', '').isdigit() else 0
            dpp = float(row[7].replace(',', '').strip()) if row[7] and row[7].replace(',', '').replace('.', '').isdigit() else 0
            ppn = float(row[8].replace(',', '').strip()) if row[8] and row[8].replace(',', '').replace('.', '').isdigit() else 0
            data.append([nama_barang, qty, unit, harga, potongan_harga, total, dpp, ppn])
    return data

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
                
                penjual_match = re.search(r'Nama\s*:\s*([\w\s\-.,&()]+)\nAlamat', text)
                if penjual_match:
                    nama_penjual = penjual_match.group(1).strip()
                
                pembeli_match = re.search(r'Pembeli Barang Kena Pajak/Penerima Jasa Kena Pajak:\s*Nama\s*:\s*([\w\s\-.,&()]+)\nAlamat', text)
                if pembeli_match:
                    nama_pembeli = pembeli_match.group(1).strip()
                    nama_pembeli = re.sub(r'\bAlamat\b', '', nama_pembeli, flags=re.IGNORECASE).strip()
            
            table = page.extract_table()
            if table:
                items = extract_table_data(table)
                for item in items:
                    item.insert(0, no_fp if no_fp else "Tidak ditemukan")
                    item.insert(1, nama_penjual if nama_penjual else "Tidak ditemukan")
                    item.insert(2, nama_pembeli if nama_pembeli else "Tidak ditemukan")
                    item.insert(3, tanggal_faktur)
                    data.append(item)
    return data

def main_app():
    """Aplikasi utama setelah login."""
    st.title("Konversi Faktur Pajak PDF ke Excel")
    uploaded_files = st.file_uploader("Upload Faktur Pajak (PDF, bisa lebih dari satu)", type=["pdf"], accept_multiple_files=True)
    
    if uploaded_files:
        all_data = []
        for uploaded_file in uploaded_files:
            tanggal_faktur = find_invoice_date(uploaded_file)
            extracted_data = extract_data_from_pdf(uploaded_file, tanggal_faktur)
            all_data.extend(extracted_data)
        
        if all_data:
            df = pd.DataFrame(all_data, columns=[
                "No FP", "Nama Penjual", "Nama Pembeli", "Tanggal Faktur", "Nama Barang", 
                "Qty", "Satuan", "Harga", "Potongan Harga", "Total", "DPP", "PPN"
            ])
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
        login_page()
    else:
        main_app()
