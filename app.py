import streamlit as st
import pandas as pd
import pdfplumber
import io
import re

def clean_number(value):
    """ Membersihkan nilai numerik dari karakter yang tidak valid """
    if value:
        value = re.sub(r'[^0-9,.]', '', value)  # Hanya angka, koma, dan titik
        value = value.replace(',', '.')  # Ganti koma dengan titik jika perlu
        try:
            return float(value)
        except ValueError:
            return 0
    return 0

def extract_data_from_pdf(pdf_file, tanggal_faktur, expected_item_count):
    data = []
    no_fp, nama_penjual, nama_pembeli = None, None, None
    item_counter = 0
    
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
                for row in table:
                    if len(row) >= 10 and row[0].isdigit():  # Pastikan baris valid
                        nama_barang = " ".join(row[2].split("\n")).strip()
                        qty = clean_number(row[3])
                        unit = row[4].strip() if row[4] else "Unknown"
                        harga = clean_number(row[5])
                        potongan_harga = clean_number(row[6])
                        total = clean_number(row[7])
                        dpp = clean_number(row[8])
                        ppn = clean_number(row[9])
                        
                        item = [no_fp if no_fp else "Tidak ditemukan", nama_penjual if nama_penjual else "Tidak ditemukan", nama_pembeli if nama_pembeli else "Tidak ditemukan", tanggal_faktur, nama_barang, qty, unit, harga, potongan_harga, total, dpp, ppn]
                        data.append(item)
                        item_counter += 1
                        
                        if item_counter >= expected_item_count:
                            break  
    return data

def main_app():
    st.title("Konversi Faktur Pajak PDF ke Excel")
    uploaded_files = st.file_uploader("Upload Faktur Pajak (PDF, bisa lebih dari satu)", type=["pdf"], accept_multiple_files=True)
    
    if uploaded_files:
        all_data = []
        for uploaded_file in uploaded_files:
            tanggal_faktur = "01/01/2024"  # Simulasi pencarian tanggal
            detected_item_count = 10  # Placeholder untuk jumlah item yang dideteksi
            extracted_data = extract_data_from_pdf(uploaded_file, tanggal_faktur, detected_item_count)
            
            if extracted_data:
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
    main_app()
