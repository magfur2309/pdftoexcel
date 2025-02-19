import streamlit as st
import pandas as pd
import pdfplumber
import io
import re
from decimal import Decimal

def count_items_in_pdf(pdf_file):
    """Menghitung jumlah item dalam PDF berdasarkan pola nomor urut."""
    item_count = 0
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                matches = re.findall(r'^\d{1,3}\s+000000', text, re.MULTILINE)
                item_count += len(matches)
    return item_count

def clean_nama_barang(nama_barang):
    """Membersihkan nama barang dari informasi harga, kuantitas, potongan harga, dan PPnBM."""
    nama_barang = re.sub(r'Rp\s[\d.,]+\sx\s[\d.,]+\s\w+', '', nama_barang).strip()
    nama_barang = re.sub(r'Potongan Harga\s*=\s*Rp\s*[\d.,]+', '', nama_barang).strip()
    nama_barang = re.sub(r'PPnBM\s*\([\d.,]+%\)\s*=\s*Rp\s*[\d.,]+', '', nama_barang).strip()
    return nama_barang

def parse_number(value):
    """Mengonversi string angka dari format Indonesia ke float."""
    try:
        return Decimal(value.replace('.', '').replace(',', '.'))
    except:
        return Decimal(0)

def extract_data_from_pdf(pdf_file):
    data = []
    no_fp, nama_penjual, nama_pembeli, tanggal_faktur = None, None, None, None
    item_counter = 0
    
    with pdfplumber.open(pdf_file) as pdf:
        previous_row = None
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                if not tanggal_faktur:
                    tanggal_match = re.search(r'Tanggal Faktur:\s*(\d{4}-\d{2}-\d{2})', text)
                    if tanggal_match:
                        tanggal_faktur = tanggal_match.group(1)
                
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
                            previous_row[3] += " " + clean_nama_barang(row[2])
                            continue
                        
                        nama_barang = clean_nama_barang(row[2])
                        harga_qty_info = re.search(r'Rp ([\d.,]+) x ([\d.,]+) (\w+)', row[2])
                        
                        if harga_qty_info:
                            harga = parse_number(harga_qty_info.group(1))
                            qty = parse_number(harga_qty_info.group(2))
                            unit = harga_qty_info.group(3)
                        else:
                            harga, qty, unit = Decimal(0), Decimal(0), "Unknown"
                        
                        total = harga * qty
                        dpp = total / Decimal(1.11)
                        ppn = total - dpp
                        
                        item = [
                            no_fp if no_fp else "Tidak ditemukan", 
                            nama_penjual if nama_penjual else "Tidak ditemukan", 
                            nama_pembeli if nama_pembeli else "Tidak ditemukan", 
                            nama_barang, 
                            float(harga), unit, int(qty), float(total), float(dpp), float(ppn), 
                            tanggal_faktur if tanggal_faktur else "Tidak ditemukan"
                        ]
                        data.append(item)
                        previous_row = item
                        item_counter += 1
    return data

def main_app():
    st.title("Konversi Faktur Pajak PDF ke Excel")
    uploaded_files = st.file_uploader("Upload Faktur Pajak (PDF, bisa lebih dari satu)", type=["pdf"], accept_multiple_files=True)
    
    if uploaded_files:
        all_data = []
        for uploaded_file in uploaded_files:
            extracted_data = extract_data_from_pdf(uploaded_file)
            
            if extracted_data:
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
