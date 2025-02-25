import streamlit as st
import pandas as pd
import pdfplumber
import io
import re
import hashlib
from datetime import datetime
from supabase import create_client

# Konfigurasi Supabase
SUPABASE_URL = "https://ukajqoitsfsolloyewsj.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVrYWpxb2l0c2Zzb2xsb3lld3NqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDAwMjUyMDEsImV4cCI6MjA1NTYwMTIwMX0.vllN8bcBG-wpjA9g7jjTMQ6_Xf-OgJdeIOu3by_cGP0"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_user(username):
    response = supabase.table("users").select("username, password, is_admin, expiry_date, last_upload_date").eq("username", username).execute()
    return response.data[0] if response.data else None

def update_last_upload(username):
    today = datetime.now().strftime("%Y-%m-%d")
    supabase.table("users").update({"last_upload_date": today}).eq("username", username).execute()

def login_page():
    st.title("Login Convert PDF FP To Excel")
    with st.form("login_form"):
        username = st.text_input("Username", placeholder="Masukkan username Anda")
        password = st.text_input("Password", type="password", placeholder="Masukkan password Anda")
        submit_button = st.form_submit_button("Login")

    if submit_button:
        user = get_user(username)
        if user and hashlib.sha256(password.encode()).hexdigest() == user["password"]:
            expiry_date = datetime.strptime(user["expiry_date"], "%Y-%m-%d")
            if expiry_date < datetime.now():
                st.error("Akun Anda telah kedaluwarsa. Silakan hubungi admin.")
            else:
                st.session_state["logged_in"] = True
                st.session_state["username"] = username
                st.session_state["is_admin"] = user["is_admin"]
                st.success("Login berhasil! Selamat datang, " + username)
                st.rerun()
        else:
            st.error("Username atau password salah")

def logout():
    st.session_state.clear()
    st.success("Logout berhasil!")
    st.rerun()

def main_app():
    st.title("Convert Faktur Pajak PDF To Excel")
    st.sidebar.button("Logout", on_click=logout)
    
    username = st.session_state["username"]
    user = get_user(username)
    
    if not user:
        st.error("User tidak ditemukan.")
        return
    
    today = datetime.now().strftime("%Y-%m-%d")
    if not user["is_admin"] and user["last_upload_date"] == today:
        st.warning("Anda hanya dapat mengupload 1 file per hari.")
        return

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
            df = pd.DataFrame(all_data, columns=["No FP", "Nama Penjual", "Nama Pembeli", "Tanggal Faktur", "Nama Barang", "Qty", "Satuan", "Harga", "Potongan Harga", "Total", "DPP", "PPN"])
            st.write("### Pratinjau Data yang Diekstrak")
            st.dataframe(df)
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=True, sheet_name='Faktur Pajak')
            output.seek(0)
            st.download_button(label="\U0001F4E5 Unduh Excel", data=output, file_name="Faktur_Pajak.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            
            if not user["is_admin"]:
                update_last_upload(username)

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    login_page()
else:
    main_app()
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
                        
                        # **Hapus informasi harga dan potongan dari nama barang**
                        nama_barang = re.sub(r'Rp [\d.,]+ x [\d.,]+ \w+', '', nama_barang)  # Hapus harga & jumlah
                        nama_barang = re.sub(r'Potongan Harga\s*=\s*Rp\s*[\d.,]+', '', nama_barang)  # Hapus potongan harga
                        nama_barang = re.sub(r'PPnBM\s*\([\d.,]+%\)\s*=\s*Rp\s*[\d.,]+', '', nama_barang)  # Hapus PPnBM
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
    def main_app():
    st.title("Convert Faktur Pajak PDF To Excel")
    uploaded_files = st.file_uploader("Upload Faktur Pajak (PDF, bisa lebih dari satu)", type=["pdf"], accept_multiple_files=True)
    
    if uploaded_files:
        all_data = []
        for uploaded_file in uploaded_files:
            tanggal_faktur = find_invoice_date(uploaded_file)
            detected_item_count = count_items_in_pdf(uploaded_file)
            extracted_data = extract_data_from_pdf(uploaded_file, tanggal_faktur, detected_item_count)
            extracted_item_count = len(extracted_data)
            
            if detected_item_count != extracted_item_count and detected_item_count != 0:
                st.warning(f"Jumlah item tidak cocok untuk {uploaded_file.name}: Ditemukan {detected_item_count}, diekstrak {extracted_item_count}")
            
            if extracted_data:
                all_data.extend(extracted_data)
        
        if all_data:
            df = pd.DataFrame(all_data, columns=["No FP", "Nama Penjual", "Nama Pembeli", "Tanggal Faktur", "Nama Barang", "Qty", "Satuan", "Harga", "Potongan Harga", "Total", "DPP", "PPN"])
            df.index = df.index + 1  
            st.write("### Pratinjau Data yang Diekstrak")
            st.dataframe(df)
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=True, sheet_name='Faktur Pajak')
            output.seek(0)
            st.download_button(label="\U0001F4E5 Unduh Excel", data=output, file_name="Faktur_Pajak.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    login_page()
else:
    main_app()

