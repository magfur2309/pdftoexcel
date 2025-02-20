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
            table = page.extract_table()
            if table:
                item_count += sum(1 for row in table if row and row[0].isdigit())
    return item_count

def extract_data_from_pdf(pdf_file, tanggal_faktur):
    data = []
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            table = page.extract_table()
            if table:
                for row in table:
                    if len(row) >= 7 and row[0].isdigit():
                        nama_barang = " ".join(row[2].split("\n")).strip()
                        qty = int(re.sub(r'[^\d]', '', row[3]) or "0")
                        unit = row[4].strip() if row[4] else "Unknown"
                        harga = int(re.sub(r'[^\d]', '', row[5]) or "0")
                        potongan_harga = int(re.sub(r'[^\d]', '', row[6]) or "0")
                        total = int(re.sub(r'[^\d]', '', row[7]) or "0")
                        dpp = int(re.sub(r'[^\d]', '', row[8]) or "0") if len(row) > 8 else 0
                        ppn = int(re.sub(r'[^\d]', '', row[9]) or "0") if len(row) > 9 else 0
                        
                        item = [tanggal_faktur, nama_barang, qty, unit, harga, potongan_harga, total, dpp, ppn]
                        data.append(item)
    return data

def main_app():
    st.title("Konversi Faktur Pajak PDF ke Excel")
    uploaded_files = st.file_uploader("Upload Faktur Pajak (PDF, bisa lebih dari satu)", type=["pdf"], accept_multiple_files=True)
    
    if uploaded_files:
        all_data = []
        for uploaded_file in uploaded_files:
            tanggal_faktur = find_invoice_date(uploaded_file)
            detected_item_count = count_items_in_pdf(uploaded_file)
            extracted_data = extract_data_from_pdf(uploaded_file, tanggal_faktur)
            
            if len(extracted_data) != detected_item_count:
                st.warning(f"Jumlah item tidak cocok untuk {uploaded_file.name}: Ditemukan {detected_item_count}, diekstrak {len(extracted_data)}")
            
            all_data.extend(extracted_data)
        
        if all_data:
            df = pd.DataFrame(all_data, columns=[
                "Tanggal Faktur", "Nama Barang", "Qty", "Satuan", "Harga", "Potongan Harga", "Total", "DPP", "PPN"
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
