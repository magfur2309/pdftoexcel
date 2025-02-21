import streamlit as st
import pandas as pd
import pdfplumber
import io
import re
import hashlib
import base64

from datetime import date

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
                matches = re.findall(r'^\d+', text, re.MULTILINE)
                item_count += len(matches)
    return item_count

def extract_data_from_pdf(pdf_file, tanggal_faktur, expected_item_count):
    data = []
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                matches = re.findall(r'([^\n]+)\s+(\d+)\s+([\d,.]+)', text)
                for match in matches:
                    nama_barang, qty, harga = match
                    qty = int(qty)
                    harga = float(harga.replace(',', ''))
                    total = qty * harga
                    dpp = total / 1.11
                    ppn = total - dpp
                    data.append(["Tidak ditemukan", "Tidak ditemukan", "Tidak ditemukan", tanggal_faktur, nama_barang, qty, "Unit", harga, 0, total, dpp, ppn])
                    if len(data) >= expected_item_count:
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
            st.session_state["upload_count"] = 0
            st.session_state["upload_date"] = date.today()
            st.success("Login berhasil! Selamat Datang!")
        else:
            st.error("Username atau password salah")

def main_app():
    st.title("Convert Faktur Pajak PDF To Excel")
    username = st.session_state.get("username", "")
    is_demo_user = username.startswith("demo")
    today = date.today()

    if "upload_date" not in st.session_state or st.session_state["upload_date"] != today:
        st.session_state["upload_count"] = 0
        st.session_state["upload_date"] = today
    
    uploaded_files = st.file_uploader("Upload Faktur Pajak (PDF, bisa lebih dari satu)", type=["pdf"], accept_multiple_files=True)
    
    if is_demo_user and st.session_state["upload_count"] >= 10:
        st.warning("Ini adalah akun demo. Anda hanya bisa mengunggah maksimal 10 file dalam sehari.")
        return
    
    if uploaded_files:
        if is_demo_user:
            if len(uploaded_files) + st.session_state["upload_count"] > 10:
                st.warning("Anda hanya dapat mengunggah sisa " + str(10 - st.session_state["upload_count"]) + " file hari ini.")
                return
            st.session_state["upload_count"] += len(uploaded_files)
        
        all_data = []
        for uploaded_file in uploaded_files:
            tanggal_faktur = find_invoice_date(uploaded_file)
            detected_item_count = count_items_in_pdf(uploaded_file)
            extracted_data = extract_data_from_pdf(uploaded_file, tanggal_faktur, detected_item_count)
            extracted_item_count = len(extracted_data)
            
            if extracted_data:
                all_data.extend(extracted_data)
        
        if all_data:
            df = pd.DataFrame(all_data, columns=["No FP", "Nama Penjual", "Nama Pembeli", "Tanggal Faktur", "Nama Barang", "Qty", "Satuan", "Harga", "Potongan Harga", "Total", "DPP", "PPN"])
            df.index = df.index + 1  
            st.write("### Pratinjau Data yang Diekstrak")
            st.dataframe(df)
            csv_data = io.StringIO()
            df.to_csv(csv_data, index=False)
            csv_data.seek(0)
            st.download_button(label="📥 Unduh CSV", data=csv_data, file_name="Faktur_Pajak.csv", mime="text/csv")
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=True, sheet_name='Faktur Pajak')
            output.seek(0)
            st.download_button(label="📥 Unduh Excel", data=output, file_name="Faktur_Pajak.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    login_page()
else:
    main_app()
