import streamlit as st
import pandas as pd
import pdfplumber
import io
import re

def extract_tanggal_faktur(text):
    """Mengekstrak tanggal faktur dari teks PDF."""
    match = re.search(r'(\d{2})\s*([A-Za-z]+)\s*(\d{4})', text)
    if match:
        bulan_mapping = {
            "Januari": "01", "Februari": "02", "Maret": "03", "April": "04", "Mei": "05", "Juni": "06",
            "Juli": "07", "Agustus": "08", "September": "09", "Oktober": "10", "November": "11", "Desember": "12"
        }
        day, month, year = match.groups()
        month = bulan_mapping.get(month, "00")
        return f"{year}-{month}-{day}"
    return "Tidak ditemukan"

def extract_data_from_pdf(pdf_file):
    data = []
    no_fp, nama_penjual, nama_pembeli, tanggal_faktur = None, None, None, None
    
    with pdfplumber.open(pdf_file) as pdf:
        previous_row = None
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                if not tanggal_faktur:
                    tanggal_faktur = extract_tanggal_faktur(text)
                
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
                        if previous_row and row[0] == "":
                            previous_row[3] += " " + " ".join(row[2].split("\n")).strip()
                            continue
                        
                        nama_barang = " ".join(row[2].split("\n")).strip()
                        nama_barang = re.sub(r'Rp [\d.,]+ x [\d.,]+ \w+', '', nama_barang)
                        nama_barang = re.sub(r'Potongan Harga = Rp [\d.,]+', '', nama_barang)
                        nama_barang = re.sub(r'PPnBM \([\d.,]+%\) = Rp [\d.,]+', '', nama_barang)
                        nama_barang = nama_barang.strip()
                        
                        harga_qty_info = re.search(r'Rp ([\d.,]+) x ([\d.,]+) (\w+)', row[2])
                        if harga_qty_info:
                            harga = int(float(harga_qty_info.group(1).replace('.', '').replace(',', '.')))
                            qty = int(float(harga_qty_info.group(2).replace('.', '').replace(',', '.')))
                            unit = harga_qty_info.group(3)
                        else:
                            harga, qty, unit = 0, 0, "Unknown"
                        
                        total = harga * qty
                        dpp = total / 1.11
                        ppn = total - dpp
                        
                        item = [
                            no_fp if no_fp else "Tidak ditemukan", 
                            nama_penjual if nama_penjual else "Tidak ditemukan", 
                            nama_pembeli if nama_pembeli else "Tidak ditemukan", 
                            nama_barang, harga, unit, qty, total, dpp, ppn, 
                            tanggal_faktur  
                        ]
                        data.append(item)
                        previous_row = item
    return data

def main_app():
    st.title("Konversi Faktur Pajak PDF ke Excel")
    uploaded_files = st.file_uploader("Upload Faktur Pajak (PDF, bisa lebih dari satu)", type=["pdf"], accept_multiple_files=True)
    
    if uploaded_files:
        all_data = []
        for uploaded_file in uploaded_files:
            extracted_data = extract_data_from_pdf(uploaded_file)
            all_data.extend(extracted_data)
        
        if all_data:
            df = pd.DataFrame(all_data, columns=["No FP", "Nama Penjual", "Nama Pembeli", "Nama Barang", "Harga", "Unit", "QTY", "Total", "DPP", "PPN", "Tanggal Faktur"])
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
