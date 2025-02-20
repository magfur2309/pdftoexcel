import streamlit as st
import pandas as pd
import pdfplumber
import io
import re

def clean_nama_barang(nama_barang):
    """Membersihkan informasi yang tidak perlu dari kolom Nama Barang."""
    nama_barang = re.sub(r'Rp [\d,.]+\s*x\s*[\d,.]+\s*Kilogram', '', nama_barang)
    nama_barang = re.sub(r'Potongan Harga = Rp [\d,.]+', '', nama_barang)
    nama_barang = re.sub(r'PPnBM \([\d,.%]+\) = Rp [\d,.]+', '', nama_barang)
    return nama_barang.strip()

def extract_data_from_pdf(pdf_file, tanggal_faktur):
    data = []
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            table = page.extract_table()
            if table:
                for row in table:
                    if len(row) >= 6 and row[0].isdigit():
                        nama_barang = clean_nama_barang(row[2].strip())
                        qty = row[3].strip() if row[3] else '0'
                        satuan = row[4].strip() if row[4] else '-'
                        harga = row[5].strip() if row[5] else '0'
                        
                        data.append([tanggal_faktur, nama_barang, qty, satuan, harga])
    return data

def main():
    st.title("Ekstrak Faktur Pajak PDF ke Excel")
    uploaded_files = st.file_uploader("Upload Faktur Pajak (PDF)", type=["pdf"], accept_multiple_files=True)
    
    if uploaded_files:
        all_data = []
        for uploaded_file in uploaded_files:
            tanggal_faktur = "01/01/2025"  # Gantilah dengan fungsi pendeteksi tanggal jika tersedia
            extracted_data = extract_data_from_pdf(uploaded_file, tanggal_faktur)
            all_data.extend(extracted_data)
        
        if all_data:
            df = pd.DataFrame(all_data, columns=["Tanggal Faktur", "Nama Barang", "Qty", "Satuan", "Harga"])
            st.dataframe(df)
            
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='Faktur Pajak')
            output.seek(0)
            
            st.download_button("Unduh Excel", data=output, file_name="Faktur_Pajak.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

if __name__ == "__main__":
    main()
