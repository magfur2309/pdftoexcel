import streamlit as st
import pandas as pd
import pdfplumber
import io
import re
import hashlib
import datetime

# Admin credentials
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = hashlib.sha256("bismillah".encode()).hexdigest()

# Hardcoded users (can be replaced with Supabase later)
users = {
    "demo1": hashlib.sha256("123456".encode()).hexdigest(),
    "demo2": hashlib.sha256("123456".encode()).hexdigest(),
    "demo3": hashlib.sha256("123456".encode()).hexdigest(),
    ADMIN_USERNAME: ADMIN_PASSWORD
}

# Function to track user uploads
def get_upload_count(username):
    today = datetime.date.today().isoformat()
    return st.session_state.get(f"upload_count_{username}_{today}", 0)

def increment_upload_count(username):
    today = datetime.date.today().isoformat()
    st.session_state[f"upload_count_{username}_{today}"] = get_upload_count(username) + 1

def login_page():
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
            st.experimental_rerun()
        else:
            st.error("Username atau password salah")

def main_app():
    st.title("Convert Faktur Pajak PDF To Excel")
    username = st.session_state["username"]
    
    # Aturan Pembatasan Unggahan
    if username.startswith("demo"):
        max_uploads = 15  # Demo user bisa upload maksimal 15 PDF per hari
    elif username == ADMIN_USERNAME:
        max_uploads = float('inf')  # Admin tidak memiliki batasan
    else:
        max_uploads = 1  # User biasa hanya bisa upload 1 file per hari
    
    upload_count = get_upload_count(username)
    
    if upload_count >= max_uploads:
        st.warning(f"Anda telah mencapai batas unggahan ({max_uploads} file per hari).")
        return
    
    uploaded_files = st.file_uploader("Upload Faktur Pajak (PDF, bisa lebih dari satu)", type=["pdf"], accept_multiple_files=True)

    if uploaded_files:
        all_data = []
        for uploaded_file in uploaded_files:
            if upload_count >= max_uploads:
                st.warning(f"Batas unggahan telah tercapai! ({max_uploads} file per hari)")
                break
            
            # (Bagian utama pemrosesan PDF tetap sama)
            
            upload_count += 1
            increment_upload_count(username)  # Catat unggahan

        if all_data:
            df = pd.DataFrame(all_data, columns=["No FP", "Nama Penjual", "Nama Pembeli", "Tanggal Faktur", "Nama Barang", "Qty", "Satuan", "Harga", "Potongan Harga", "Total", "DPP", "PPN"])
            st.dataframe(df)
            
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=True, sheet_name='Faktur Pajak')
            output.seek(0)
            st.download_button(label="\U0001F4E5 Unduh Excel", data=output, file_name="Faktur_Pajak.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# Initialize session state
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    login_page()
else:
    main_app()
