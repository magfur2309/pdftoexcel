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
                        
                        nama_barang = re.sub(r'Rp [\d.,]+ x [\d.,]+ \w+', '', nama_barang)
                        nama_barang = re.sub(r'Potongan Harga\s*=\s*Rp\s*[\d.,]+', '', nama_barang)
                        nama_barang = re.sub(r'PPnBM\s*\([\d.,]+%\)\s*=\s*Rp\s*[\d.,]+', '', nama_barang)
                        nama_barang = nama_barang.strip()

                        item = [no_fp or "Tidak ditemukan", nama_penjual or "Tidak ditemukan", nama_pembeli or "Tidak ditemukan", tanggal_faktur, nama_barang]
                        data.append(item)
                        item_counter += 1
                        
                        if item_counter >= expected_item_count:
                            break  
    return data

def login_page():
    users = {
        "user1": hashlib.sha256("ijfugroup1".encode()).hexdigest(),
        "user2": hashlib.sha256("ijfugroup2".encode()).hexdigest(),
        "user3": hashlib.sha256("ijfugroup3".encode()).hexdigest(),
        "user4": hashlib.sha256("ijfugroup4".encode()).hexdigest(),
        "admin": hashlib.sha256("bismillah".encode()).hexdigest()
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
            st.success(f"Login berhasil! Selamat Datang, {username}")
        else:
            st.error("Username atau password salah")

def main_app():
    st.title("Convert Faktur Pajak PDF To Excel")
    username = st.session_state.get("username", "")
    today = datetime.date.today().isoformat()
    
    if "upload_history" not in st.session_state:
        st.session_state["upload_history"] = {}
    
    user_uploads = st.session_state["upload_history"].get(username, {})
    
    if username != "admin" and user_uploads.get("date") == today:
        st.warning("Anda hanya dapat mengunggah 1 file PDF per hari.")
        return
    
    uploaded_files = st.file_uploader("Upload Faktur Pajak (PDF, bisa lebih dari satu)", type=["pdf"], accept_multiple_files=(username == "admin"))
    
    if uploaded_files:
        st.session_state["upload_history"][username] = {"date": today}
        all_data = []
        for uploaded_file in uploaded_files:
            tanggal_faktur = find_invoice_date(uploaded_file)
            detected_item_count = count_items_in_pdf(uploaded_file)
            extracted_data = extract_data_from_pdf(uploaded_file, tanggal_faktur, detected_item_count)
            if extracted_data:
                all_data.extend(extracted_data)
        
        if all_data:
            df = pd.DataFrame(all_data, columns=["No FP", "Nama Penjual", "Nama Pembeli", "Tanggal Faktur", "Nama Barang"])
            st.write("### Pratinjau Data yang Diekstrak")
            st.dataframe(df)

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    login_page()
else:
    main_app()
