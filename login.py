# auth.py - Menangani autentikasi dengan Supabase
import streamlit as st
from supabase import create_client
import bcrypt

# Mengambil credential dari secrets
SUPABASE_URL = st.secrets.get("SUPABASE_URL", None)
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", None)

# Periksa apakah URL dan KEY tersedia sebelum membuat client
if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    st.error("Gagal menghubungkan ke Supabase: Periksa konfigurasi secrets!")

def hash_password(password):
    """Mengenkripsi password menggunakan bcrypt."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password, hashed_password):
    """Memverifikasi password yang dimasukkan dengan hash yang tersimpan."""
    return bcrypt.checkpw(password.encode(), hashed_password.encode())

def authenticate_user(username, password):
    """Mengecek apakah username dan password cocok dengan database."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None  # Hindari error jika Supabase tidak dikonfigurasi
    
    response = supabase.table("users").select("id, username, password, role").eq("username", username).execute()
    
    if response.data:
        user = response.data[0]
        if verify_password(password, user["password"]):
            return user  # Return data user jika berhasil login
    return None

def login_page():
    """Menampilkan halaman login."""
    st.title("Login Konversi Faktur Pajak")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    
    if st.button("Login"):
        user = authenticate_user(username, password)
        if user:
            st.session_state["logged_in"] = True
            st.session_state["username"] = user["username"]
            st.session_state["role"] = user["role"]
            st.success(f"Selamat datang, {user['username']}!")
            st.rerun()  # Refresh halaman setelah login
        else:
            st.error("Username atau password salah")

