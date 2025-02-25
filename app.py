import streamlit as st
import pandas as pd
import pdfplumber
import io
import re
import hashlib
from datetime import datetime, date
from supabase import create_client

# Konfigurasi Supabase
SUPABASE_URL = "YOUR_SUPABASE_URL"
SUPABASE_KEY = "YOUR_SUPABASE_KEY"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def find_invoice_date(pdf_file):
    month_map = {"Januari": "01", "Februari": "02", "Maret": "03", "April": "04", "Mei": "05", "Juni": "06", 
                 "Juli": "07", "Agustus": "08", "September": "09", "Oktober": "10", "November": "11", "Desember": "12"}
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                date_match = re.search(r'(\d{1,2})\s*(Januari|Februari|Maret|April|Mei|Juni|Juli|Agustus|September|Oktober|November|Desember)\s*(\d{4})', text, re.IGNORECASE)
                if date_match:
                    day, month, year = date_match.groups()
                    return f"{day.zfill(2)}/{month_map[month]}/{year}"
    return "Tidak ditemukan"

def login_page():
    st.title("Login Convert PDF FP To Excel")

    with st.form("login_form"):
        username = st.text_input("Username", placeholder="Masukkan username Anda")
        password = st.text_input("Password", type="password", placeholder="Masukkan password Anda")
        submit_button = st.form_submit_button("Login")

    if submit_button or st.session_state.get("enter_pressed", False):
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        user_query = supabase.table("users").select("username, password, expires_at, role, last_upload").eq("username", username).execute()
        if user_query.data:
            user = user_query.data[0]
            if user["password"] == hashed_password:
                if user["expires_at"] and date.today() > datetime.strptime(user["expires_at"], "%Y-%m-%d").date():
                    st.error("Akun Anda telah kedaluwarsa")
                else:
                    st.session_state["logged_in"] = True
                    st.session_state["username"] = username
                    st.session_state["role"] = user["role"]
                    st.session_state["last_upload"] = user["last_upload"]
                    st.success("Login berhasil! Selamat Datang Member ijfugroup")
                    st.rerun()
            else:
                st.error("Username atau password salah")
        else:
            st.error("Username tidak ditemukan")

def main_app():
    st.title("Convert Faktur Pajak PDF To Excel")
    username = st.session_state["username"]
    role = st.session_state["role"]
    last_upload = st.session_state.get("last_upload")

    # Batasi upload 1 file per hari untuk user biasa
    if role == "user" and last_upload and last_upload == str(date.today()):
        st.warning("Anda hanya bisa mengupload 1 file per hari")
        return
    
    uploaded_files = st.file_uploader("Upload Faktur Pajak (PDF, bisa lebih dari satu)", type=["pdf"], accept_multiple_files=True)
    
    if uploaded_files:
        all_data = []
        for uploaded_file in uploaded_files:
            tanggal_faktur = find_invoice_date(uploaded_file)
            extracted_data = [["Contoh Data", "12345", tanggal_faktur]]  # Placeholder
            all_data.extend(extracted_data)
        
        if all_data:
            df = pd.DataFrame(all_data, columns=["No FP", "Nama Penjual", "Tanggal Faktur"])
            st.write("### Pratinjau Data yang Diekstrak")
            st.dataframe(df)
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=True, sheet_name='Faktur Pajak')
            output.seek(0)
            st.download_button(label="\U0001F4E5 Unduh Excel", data=output, file_name="Faktur_Pajak.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        
        # Update tanggal upload terakhir user di database
        supabase.table("users").update({"last_upload": str(date.today())}).eq("username", username).execute()

def logout():
    st.session_state.clear()
    st.rerun()

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    login_page()
else:
    st.sidebar.button("Logout", on_click=logout)
    main_app()
