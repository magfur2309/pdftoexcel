import streamlit as st
import pandas as pd
import pdfplumber
import io
import re
from datetime import datetime, timedelta
from supabase import create_client

# Inisialisasi Supabase
SUPABASE_URL = "https://ukajqoitsfsolloyewsj.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVrYWpxb2l0c2Zzb2xsb3lld3NqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDAwMjUyMDEsImV4cCI6MjA1NTYwMTIwMX0.vllN8bcBG-wpjA9g7jjTMQ6_Xf-OgJdeIOu3by_cGP0"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

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
                        nama_barang = row[2].strip()
                        qty = int(row[3]) if row[3].isdigit() else 0
                        harga = int(row[4].replace('.', '')) if row[4].replace('.', '').isdigit() else 0
                        total = qty * harga
                        dpp = total / 1.11
                        ppn = total - dpp
                        
                        item = [no_fp if no_fp else "Tidak ditemukan", nama_penjual if nama_penjual else "Tidak ditemukan", nama_pembeli if nama_pembeli else "Tidak ditemukan", tanggal_faktur, nama_barang, qty, harga, total, dpp, ppn]
                        data.append(item)
                        item_counter += 1
                        
                        if item_counter >= expected_item_count:
                            break  
    return data

def check_upload_limit(username):
    """Memeriksa apakah pengguna non-admin telah mengunggah file hari ini."""
    if username == "admin":
        return False  # Admin tidak memiliki batasan
    
    today = datetime.now().strftime("%Y-%m-%d")
    response = supabase.table("uploads").select("upload_date").eq("username", username).execute()
    uploads = response.data if response.data else []
    
    return any(upload["upload_date"] == today for upload in uploads)

def log_upload(username):
    """Menyimpan informasi unggahan pengguna."""
    today = datetime.now().strftime("%Y-%m-%d")
    supabase.table("uploads").insert({"username": username, "upload_date": today}).execute()

def login_page():
    """Menampilkan halaman login."""
    st.title("Login Konversi Faktur Pajak")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    
    if st.button("Login"):
        response = supabase.table("users").select("password, role").eq("username", username).execute()
        user_data = response.data[0] if response.data else None
        
        if user_data and password == user_data["password"]:  # Perbaiki dengan hashing
            st.session_state["logged_in"] = True
            st.session_state["username"] = username
            st.session_state["role"] = user_data["role"]
            st.rerun()
        else:
            st.error("Username atau password salah")

if __name__ == "__main__":
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
    if not st.session_state["logged_in"]:
        login_page()
    else:
        main_app()
