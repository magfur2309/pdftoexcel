import streamlit as st
import pandas as pd
import pdfplumber
import io
import re

def hitung_baris_pdf(pdf_file):
    total_baris = 0
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            table = page.extract_table()
            if table:
                total_baris += sum(1 for row in table if row[0].isdigit())
    return total_baris

def main_app():
    st.title("Konversi Faktur Pajak PDF ke Excel")
    uploaded_files = st.file_uploader("Upload Faktur Pajak (PDF, bisa lebih dari satu)", type=["pdf"], accept_multiple_files=True)
    
    if uploaded_files:
        all_data = []
        total_baris_pdf = 0
        total_baris_output = 0

        for uploaded_file in uploaded_files:
            total_baris_pdf += hitung_baris_pdf(uploaded_file)
            tanggal_faktur = extract_tanggal_faktur(uploaded_file)  
            extracted_data = extract_data_from_pdf(uploaded_file, tanggal_faktur)
            total_baris_output += len(extracted_data)
            
            if extracted_data:
                all_data.extend(extracted_data)
        
        if all_data:
            df = pd.DataFrame(all_data, columns=["No FP", "Nama Penjual", "Nama Pembeli", "Nama Barang", "Harga", "Unit", "QTY", "Total", "DPP", "PPN", "Tanggal Faktur"])
            df.index = df.index + 1  
            
            st.write("### Pratinjau Data yang Diekstrak")
            st.dataframe(df)
            
            if total_baris_pdf != total_baris_output:
                st.warning(f"⚠️ Jumlah baris dalam PDF ({total_baris_pdf}) tidak sesuai dengan hasil ekstraksi ({total_baris_output}). Periksa apakah ada data yang terlewat atau salah dibaca.")
            
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
