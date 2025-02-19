import streamlit as st
import pandas as pd
import pdfplumber
import io
import re

def login_page():
    st.set_page_config(page_title="Login", page_icon="🔐")
    
    st.markdown(
        """
        <style>
            .login-container {
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                height: 80vh;
            }
            .login-input {
                width: 300px;
                padding: 10px;
                margin: 5px;
                border-radius: 5px;
                border: 1px solid #ccc;
            }
            .login-button {
                width: 320px;
                padding: 10px;
                background-color: #007bff;
                color: white;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                font-size: 16px;
            }
            .login-button:hover {
                background-color: #0056b3;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )
    
    st.markdown("<div class='login-container'>", unsafe_allow_html=True)
    st.header("Login Form")
    username = st.text_input("Username :", key="username")
    password = st.text_input("Password :", type="password", key="password")
    
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Don't have an account?"):
            st.warning("Redirect to signup page (Not implemented)")
    with col2:
        if st.button("Login"):
            if username == "admin" and password == "password":  # Example credentials
                st.success("Login successful!")
                main_app()
            else:
                st.error("Invalid username or password")
    
    st.markdown("</div>", unsafe_allow_html=True)

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

def main_app():
    st.title("Konversi Faktur Pajak PDF ke Excel")
    uploaded_files = st.file_uploader("Upload Faktur Pajak (PDF, bisa lebih dari satu)", type=["pdf"], accept_multiple_files=True)
    
    if uploaded_files:
        all_data = []
        for uploaded_file in uploaded_files:
            tanggal_faktur = find_invoice_date(uploaded_file)
            extracted_data = []  # Placeholder for the actual extraction function
            
            if extracted_data:
                all_data.extend(extracted_data)
        
        if all_data:
            df = pd.DataFrame(all_data, columns=["No FP", "Nama Penjual", "Nama Pembeli", "Nama Barang", "Harga", "Unit", "QTY", "Total", "Potongan Harga", "DPP", "PPN", "Tanggal Faktur"])
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
    login_page()
