# login.py - Menangani autentikasi dengan Supabase
import streamlit as st
from supabase import create_client
import bcrypt
import os
from dotenv import load_dotenv
import streamlit as st

# Load environment variables
load_dotenv()
st.write("SUPABASE_URL:", st.secrets.get("https://ukajqoitsfsolloyewsj.supabase.co"))
st.write("SUPABASE_KEY:", st.secrets.get("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVrYWpxb2l0c2Zzb2xsb3lld3NqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDAwMjUyMDEsImV4cCI6MjA1NTYwMTIwMX0.vllN8bcBG-wpjA9g7jjTMQ6_Xf-OgJdeIOu3by_cGP0"))
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
