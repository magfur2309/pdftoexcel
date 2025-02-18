import streamlit as st
import pandas as pd
import pdfplumber
import io
import re
import uuid

# Initialize session state variables
if 'upload_count' not in st.session_state:
    st.session_state['upload_count'] = 0

if 'user_authenticated' not in st.session_state:
    st.session_state['user_authenticated'] = False

if 'username' not in st.session_state:
    st.session_state['username'] = None

if 'session_id' not in st.session_state:
    st.session_state['session_id'] = str(uuid.uuid4())  # Generate a unique session ID

# Function to check if the user has exceeded the upload limit
def check_upload_limit():
    if st.session_state.get('username') == 'demo' and st.session_state['upload_count'] >= 50:
        st.warning("Anda sudah melebihi batas maksimal penggunaan untuk demo account (50 file).")
        return True
    return False

# Function to handle user login
def login(username, password):
    # Dummy user credentials for admin and demo
    users = {
        "admin": "123456",
        "demo": "123456"
    }

    # Check if the credentials match
    if username in users and users[username] == password:
        st.session_state['user_authenticated'] = True
        st.session_state['username'] = username
        st.session_state['upload_count'] = 0  # Reset upload count when logged in (for demo user on a new device)
        return True
    return False

# Function to extract the invoice date from the PDF
def extract_tanggal_faktur(pdf):
    month_mapping = {
        "Januari": "01", "Februari": "02", "Maret": "03", "April": "04",
        "Mei": "05", "Juni": "06", "Juli": "07", "Agustus": "08",
        "September": "09", "Oktober": "10", "November": "11", "Desember": "12"
    }
    tanggal_faktur = "Tidak ditemukan"
    
    # Convert uploaded file into a format pdfplumber can work with
    with pdfplumber.open(pdf) as pdf_obj:
        for page in pdf_obj.pages:
            text = page.extract_text()
            if text:
                date_match = re.search(r'(\d{1,2})\s*(Januari|Februari|Maret|April|Mei|Juni|Juli|Agustus|September|Oktober|November|Desember)\s*(\d{4})', text, re.IGNORECASE)
                if date_match:
                    day, month, year = date_match.groups()
                    tanggal_faktur = f"{year}-{month_mapping[month]}-{day.zfill(2)}"
                    break  
    return tanggal_faktur

# Function to extract data from the PDF
def extract_data_from_pdf(pdf_file, tanggal_faktur):
    data = []
    no_fp, nama_penjual, nama_pembeli = None, None, None

    # Convert uploaded file into a format pdfplumber can work with
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
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
                previous_row = None
                for row in table:
                    if len(row) >= 4 and row[0].isdigit():
                        if previous_row and row[0] == "":
                            previous_row[2] += " " + " ".join(row[2].split("\n")).strip()
                            continue
                        
                        nama_barang = " ".join(row[2].split("\n")).strip()
                        harga_qty_info = re.search(r'Rp ([\d.,]+) x ([\d.,]+) (\w+)', row[2])
                        if harga_qty_info:
                            harga = int(float(harga_qty_info.group(1).replace('.', '').replace(',', '.')))
                            qty = int(float(harga_qty_info.group(2).replace('.', '').replace(',', '.')))
                            unit = harga_qty_info.group(3)
                        else:
                            harga, qty, unit = 0, 0, "Unknown"
                        
                        total = harga * qty
                        dpp = total / 1.11
                        ppn = total - dpp
                        
                        item = [
                            no_fp if no_fp else "Tidak ditemukan", 
                            nama_penjual if nama_penjual else "Tidak ditemukan", 
                            nama_pembeli if nama_pembeli else "Tidak ditemukan", 
                            nama_barang, harga, unit, qty, total, dpp, ppn, 
                            tanggal_faktur  
                        ]
                        data.append(item)
                        previous_row = item
    return data

# Display login form if user is not authenticated
if not st.session_state['user_authenticated']:
    # Form layout for login
    with st.form(key="login_form"):
        st.title("Login untuk Mengakses Aplikasi")

        # Form fields
        username = st.text_input("Username", placeholder="Masukkan username Anda")
        password = st.text_input("Password", type="password", placeholder="Masukkan password Anda")
        
        # Submit button
        submit_button = st.form_submit_button(label="Login")

        # Login logic
        if submit_button:
            if login(username, password):
                st.success(f"Selamat datang, {username}!")
            else:
                st.error("Username atau password salah. Coba lagi.")
else:
    # Main application code after login

    # Check upload limit for demo users
    if check_upload_limit():
        st.stop()  # Stop the process if the demo user has exceeded the upload limit

    # Main Application: PDF Upload and Processing
    st.title("Konversi Faktur Pajak PDF ke Excel")

    # File uploader for PDF invoices
    uploaded_files = st.file_uploader("Upload Faktur Pajak (PDF, bisa lebih dari satu)", type=["pdf"], accept_multiple_files=True)

    if uploaded_files:
        all_data = []
        
        for uploaded_file in uploaded_files:
            tanggal_faktur = extract_tanggal_faktur(uploaded_file)  
            extracted_data = extract_data_from_pdf(uploaded_file, tanggal_faktur)
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
                writer.close()
            output.seek(0)
            
            st.download_button(label="📥 Unduh Excel", data=output, file_name="Faktur_Pajak.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            
            # Increment the upload count for demo user
            if st.session_state['username'] == 'demo':
                st.session_state['upload_count'] += len(uploaded_files)
        else:
            st.error("Gagal mengekstrak data. Pastikan format faktur sesuai.")
