# login.py - Menangani autentikasi dengan Supabase
import streamlit as st
from supabase import create_client
import bcrypt
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password, hashed_password):
    return bcrypt.checkpw(password.encode(), hashed_password.encode())

def authenticate_user(username, password):
    response = supabase.table("users").select("id, username, password, role").eq("username", username).execute()
    if response.data:
        user = response.data[0]
        if verify_password(password, user["password"]):
            return user
    return None

def login_page():
    st.title("Login Konversi Faktur Pajak")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    
    if st.button("Login"):
        user = authenticate_user(username, password)
        if user:
            st.session_state["logged_in"] = True
            st.session_state["username"] = user["username"]
            st.session_state["role"] = user["role"]
            st.rerun()
        else:
            st.error("Username atau password salah")

# app.py - Menjalankan aplikasi utama
import streamlit as st
import pandas as pd
import pdfplumber
import io
import re
from datetime import datetime
from supabase import create_client
import os

def check_upload_quota(username):
    today = datetime.now().date()
    response = supabase.table("upload_logs").select("id").eq("username", username).eq("date", today).execute()
    user_quota = supabase.table("users").select("upload_quota").eq("username", username).execute()
    
    if response.data and len(response.data) >= user_quota.data[0]["upload_quota"]:
        return False
    return True

def log_upload(username):
    supabase.table("upload_logs").insert({
        "username": username,
        "date": datetime.now().date()
    }).execute()

def admin_panel():
    st.title("Manajemen Pengguna")
    users = supabase.table("users").select("id, username, role, upload_quota").execute().data
    
    for user in users:
        col1, col2, col3, col4 = st.columns(4)
        col1.write(user["username"])
        col2.write(user["role"])
        quota = col3.number_input(f"Kuota {user['username']}", value=user["upload_quota"], min_value=1, step=1)
        
        if col4.button(f"Update {user['username']}"):
            supabase.table("users").update({"upload_quota": quota}).eq("id", user["id"]).execute()
            st.success("Kuota diperbarui!")
            st.rerun()

def main_app():
    st.title("Konversi Faktur Pajak PDF To Excel")
    uploaded_files = st.file_uploader("Upload Faktur Pajak (PDF, bisa lebih dari satu)", type=["pdf"], accept_multiple_files=True)
    
    if uploaded_files:
        if st.session_state["role"] != "admin" and not check_upload_quota(st.session_state["username"]):
            st.error("Anda telah mencapai batas upload harian.")
        else:
            log_upload(st.session_state["username"])
            st.success("Upload berhasil, lanjutkan pemrosesan faktur.")
            
    if st.session_state["role"] == "admin":
        admin_panel()

if __name__ == "__main__":
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
    
    if not st.session_state["logged_in"]:
        import login
        login.login_page()
    else:
        main_app()
