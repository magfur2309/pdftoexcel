import streamlit as st
import pandas as pd
import pdfplumber
import io
import re
import hashlib
import datetime

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

def count_items_in_pdf(pdf_file):
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
                    if len(row) >= 4 and row[0].isdigit():
                        nama_barang = " ".join(row[2].split("\n")).strip()
                        
                        # Hapus informasi harga dan potongan dari nama barang
                        nama_barang = re.sub(r'Rp [\d.,]+ x [\d.,]+ \w+', '', nama_barang)  # Hapus harga & jumlah
                        nama_barang = re.sub(r'Potongan Harga\s*=\s*Rp\s*[\d.,]+', '', nama_barang)  # Hapus potongan harga
                        nama_barang = re.sub(r'PPnBM\s*$$[\d.,]+%$$\s*=\s*Rp\s*[\d.,]+', '', nama_barang)  # Hapus PPnBM
                        nama_barang = nama_barang.strip()  # Bersihkan spasi ekstra

                        harga_qty_info = re.search(r'Rp ([\d.,]+) x ([\d.,]+) (\w+)', row[2])
                        if harga_qty_info:
                            harga = int(float(harga_qty_info.group(1).replace('.', '').replace(',', '.')))
                            qty = int(float(harga_qty_info.group(2).replace('.', '').replace(',', '.')))
                            unit = harga_qty_info.group(3)
                        else:
                            harga, qty, unit = 0, 0, "Unknown"
                        
                        potongan_harga_match = re.search(r'Potongan Harga\s*=\s*Rp\s*([\d.,]+)', row[2])
                        potongan_harga = int(float(potongan_harga_match.group(1).replace('.', '').replace(',', '.'))) if potongan_harga_match else 0
                        
                        total = (harga * qty) - potongan_harga
                        potongan_harga = min(potongan_harga, total)
                        ppn = round(total * 0.11, 2)
                        dpp = total - ppn
                        item = [no_fp or "Tidak ditemukan", nama_penjual or "Tidak ditemukan", nama_pembeli or "Tidak ditemukan", tanggal_faktur, nama_barang, qty, unit, harga, potongan_harga, total, dpp, ppn]
                        data.append(item)
                        item_counter += 1
                        
                        if item_counter >= expected_item_count:
                            break  
    return data


def login_page():
    users = {
        "demo1": hashlib.sha256("123456".encode()).hexdigest(),
        "demo2": hashlib.sha256("123456".encode()).hexdigest(),
        "demo3": hashlib.sha256("123456".encode()).hexdigest()
        
    }
    
    st.title("Login Convert PDF FP To Excel")

    with st.form("login_form"):
        username = st.text_input("Username", placeholder="Masukkan username Anda")
        password = st.text_input("Password", type="password", placeholder="Masukkan password Anda")
        submit_button = st.form_submit_button("Login")

    if submit_button:
        if username in users and hashlib.sha256(password.encode()).hexdigest() == users[username]:
            st.session_state["logged_in"] = True
            st.session_state["username"] = username
            st.success("Login berhasil! Selamat Datang!")
        else:
            st.error("Username atau password salah")


def main_app():
    st.title("Convert Faktur Pajak PDF To Excel")

    # Check if the user is logged in
    if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
        st.error("Anda harus login terlebih dahulu.")
        return

    # Get the current date
    today = datetime.date.today()

    # Check if the user has exceeded the upload limit for today
    if "upload_count" not in st.session_state:
        st.session_state["upload_count"] = 0
    elif st.session_state["upload_count"] >= 15 and today == st.session_state["last_upload_date"]:
        st.error("Anda telah mencapai batas upload maksimal untuk hari ini (15 file).")
        return

    uploaded_files = st.file_uploader("Upload Faktur Pajak (PDF, bisa lebih dari satu)", type=["pdf"], accept_multiple_files=True)
    
    if uploaded_files:
        all_data = []
        for uploaded_file in uploaded_files:
            tanggal_faktur = find_invoice_date(uploaded_file)
            detected_item_count = count_items_in_pdf(uploaded_file)
            extracted_data = extract_data_from_pdf(uploaded_file, tanggal_faktur, detected_item_count)
            extracted_item_count = len(extracted_data)
            
            # Update the upload count and last upload date
            st.session_state["upload_count"] += len(uploaded_files)
            st.session_state["last_upload_date"] = today

            all_data.extend(extracted_data)
            
        if all_data:
            df = pd.DataFrame(all_data, columns=["No FP", "Nama Penjual", "Nama Pembeli", "Tanggal Faktur", "Nama Barang", "Qty", "Unit", "Harga Satuan", "Potongan Harga", "Total", "DPP", "PPN"])
            st.dataframe(df)
            
            # Download Excel
            csv = df.to_csv(index=False)
            b64 = base64.b64encode(csv.encode()).decode()
            href = f'<a href="data:file/csv;base64,{b64}" download="Faktur Pajak.csv">Download Data Faktur Pajak (CSV)</a>'
            st.markdown(href, unsafe_allow_html=True)

if __name__ == "__main__":
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
    if st.session_state["logged_in"]:
        main_app()
    else:
        login_page()
