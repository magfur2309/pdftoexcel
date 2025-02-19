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

def count_items_in_pdf(pdf_file):
    """Menghitung jumlah item dalam PDF berdasarkan pola nomor urut."""
    item_count = 0
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                matches = re.findall(r'^(\d{1,3})\s+000000', text, re.MULTILINE)
                item_count += len(matches)
    return item_count

def extract_data_from_pdf(pdf_file, tanggal_faktur, expected_item_count):
    data = []
    no_fp, nama_penjual, nama_pembeli = None, None, None
    item_counter = 0
    
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                no_fp_match = re.search(r'Kode dan Nomor Seri Faktur Pajak:\s*([\d.-]+)', text)
                if no_fp_match:
                    no_fp = no_fp_match.group(1)
                
                penjual_match = re.search(r'Nama\s*:\s*([\w\s\-.,&()]+)\nAlamat', text)
                if penjual_match:
                    nama_penjual = penjual_match.group(1).strip()
                
                pembeli_match = re.search(r'Pembeli Barang Kena Pajak/Penerima Jasa Kena Pajak:\s*Nama\s*:\s*([\w\s\-.,&()]+)\nAlamat', text)
                if pembeli_match:
                    nama_pembeli = pembeli_match.group(1).strip()
            
            table = page.extract_table()
            if table:
                for row in table:
                    if len(row) >= 5:
                        try:
                            harga = int(float(row[3].replace('.', '').replace(',', '.')))
                            qty = int(float(row[4].replace('.', '').replace(',', '.')))
                            total = harga * qty
                            dpp = round(total / 1.11)
                            ppn = round(total - dpp)
                        except ValueError:
                            harga, qty, total, dpp, ppn = 0, 0, 0, 0, 0

                        data.append([
                            no_fp if no_fp else "Tidak ditemukan", 
                            nama_penjual if nama_penjual else "Tidak ditemukan", 
                            nama_pembeli if nama_pembeli else "Tidak ditemukan", 
                            tanggal_faktur, 
                            row[1] if len(row) > 1 else "Tidak ditemukan", 
                            qty, 
                            row[2] if len(row) > 2 else "Tidak ditemukan", 
                            harga, 
                            total, 
                            dpp, 
                            ppn
                        ])
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
            tanggal_faktur = find_invoice_date(uploaded_file)
            detected_item_count = count_items_in_pdf(uploaded_file)
            extracted_data = extract_data_from_pdf(uploaded_file, tanggal_faktur, detected_item_count)
            
            if extracted_data:
                all_data.extend(extracted_data)
        
        if all_data:
            df = pd.DataFrame(all_data, columns=[
                "No FP", "Nama Penjual", "Nama Pembeli", "Tanggal Faktur", "Nama Barang", 
                "Qty", "Satuan", "Harga", "Total", "DPP", "PPN"
            ])
            df.index += 1
            
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
