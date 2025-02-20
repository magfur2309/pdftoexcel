import streamlit as st
import pandas as pd
import pdfplumber
import io
import re
import hashlib

# Simulasi database pengguna
USER_CREDENTIALS = {
    "admin": "21232f297a57a5a743894a0e4a801fc3",  # Hash MD5 dari "admin"
    "user": "ee11cbb19052e40b07aac0ca060c23ee"   # Hash MD5 dari "user"
}

def hash_password(password):
    return hashlib.md5(password.encode()).hexdigest()

def login():
    st.title("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    login_button = st.button("Login")
    
    if login_button:
        hashed_password = hash_password(password)
        if username in USER_CREDENTIALS and USER_CREDENTIALS[username] == hashed_password:
            st.success("Login berhasil!")
            st.session_state["authenticated"] = True
            st.session_state["username"] = username
        else:
            st.error("Username atau password salah")

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

def extract_invoice_items(pdf_file):
    """Ekstrak data faktur dari PDF."""
    items = []
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                item_matches = re.findall(r'^(\d{1,3})\s+([A-Za-z0-9 ]+)\s+(\d+)\s+([A-Za-z]+)\s+([\d,.]+)\s+([\d,.]+)\s+([\d,.]+)\s+([\d,.]+)\s+([\d,.]+)\s+([\d,.]+)', text, re.MULTILINE)
                for match in item_matches:
                    items.append(match)
    return items

def main_app():
    st.title("Konversi Faktur Pajak PDF ke Excel")
    uploaded_files = st.file_uploader("Upload Faktur Pajak (PDF, bisa lebih dari satu)", type=["pdf"], accept_multiple_files=True)
    
    if uploaded_files:
        all_data = []
        for uploaded_file in uploaded_files:
            tanggal_faktur = find_invoice_date(uploaded_file)
            extracted_data = extract_invoice_items(uploaded_file)
            extracted_item_count = len(extracted_data)
            
            if extracted_data:
                for item in extracted_data:
                    all_data.append(["", "", "", tanggal_faktur, *item])
            
        if all_data:
            df = pd.DataFrame(all_data, columns=[
                "No FP", "Nama Penjual", "Nama Pembeli", "Tanggal Faktur", "No Item", "Nama Barang", 
                "Qty", "Satuan", "Harga", "Potongan Harga", "Total", "DPP", "PPN"
            ])
            df.index = df.index + 1  # Mulai nomor indeks dari 1
            
            st.write("### Pratinjau Data yang Diekstrak")
            st.dataframe(df)
            
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=True, sheet_name='Faktur Pajak')
            output.seek(0)
            
            st.download_button(label="\U0001F4E5 Unduh Excel", data=output, file_name="Faktur_Pajak.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        else:
            st.error("Gagal mengekstrak data. Pastikan format faktur sesuai.")

def main():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    
    if not st.session_state["authenticated"]:
        login()
    else:
        main_app()
        if st.button("Logout"):
            st.session_state["authenticated"] = False
            st.experimental_rerun()

if __name__ == "__main__":
    main()
