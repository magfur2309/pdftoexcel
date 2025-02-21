import streamlit as st
import supabase
import hashlib
import os

# Koneksi ke Supabase
SUPABASE_URL = "https://ukajqoitsfsolloyewsj.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVrYWpxb2l0c2Zzb2xsb3lld3NqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDAwMjUyMDEsImV4cCI6MjA1NTYwMTIwMX0.vllN8bcBG-wpjA9g7jjTMQ6_Xf-OgJdeIOu3by_cGP0"

supabase_client = supabase.create_client(SUPABASE_URL, SUPABASE_KEY)

def get_user(username, password):
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    response = supabase_client.table("users").select("*").eq("username", username).eq("password", hashed_password).execute()
    return response.data if response.data else None

def login_page():
    st.title("Login Convert PDF FP To Excel")

    with st.form("login_form"):
        username = st.text_input("Username", placeholder="Masukkan username Anda")
        password = st.text_input("Password", type="password", placeholder="Masukkan password Anda")
        submit_button = st.form_submit_button("Login")

    if submit_button:
        user = get_user(username, password)
        if user:
            st.session_state["logged_in"] = True
            st.session_state["username"] = username
            st.session_state["role"] = user[0]["role"]
            st.success(f"Login berhasil! Selamat datang, {username}!")
        else:
            st.error("Username atau password salah")

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    login_page()
else:
    st.title("Convert Faktur Pajak PDF To Excel")
    st.write("Selamat datang di aplikasi!")
