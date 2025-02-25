import streamlit as st
import pandas as pd
import pdfplumber
import io
import supabase
import hashlib
import datetime

# Inisialisasi Supabase
SUPABASE_URL = "https://ukajqoitsfsolloyewsj.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVrYWpxb2l0c2Zzb2xsb3lld3NqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDAwMjUyMDEsImV4cCI6MjA1NTYwMTIwMX0.vllN8bcBG-wpjA9g7jjTMQ6_Xf-OgJdeIOu3by_cGP0"
sb = supabase.create_client(SUPABASE_URL, SUPABASE_KEY)

# Fungsi hashing password
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Cek login session
if "user" not in st.session_state:
    st.session_state.user = None

# Tampilan login
if st.session_state.user is None:
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        response = sb.table("users").select("username, password, role").eq("username", username).execute()
        user_data = response.data
        if user_data and user_data[0]["password"] == hash_password(password):
            st.session_state.user = {"username": username, "role": user_data[0]["role"]}
            st.experimental_rerun()
        else:
            st.error("Username atau password salah")
else:
    st.title("Konversi PDF ke Excel")
    st.write(f"Login sebagai: {st.session_state.user['username']} ({st.session_state.user['role']})")
    
    # Ambil data upload user hari ini
    today = datetime.date.today().isoformat()
    user_uploads = sb.table("uploads").select("id").eq("username", st.session_state.user["username"]).eq("date", today).execute().data
    
    # Cek batasan upload untuk non-admin
    if st.session_state.user["role"] != "admin" and user_uploads:
        st.warning("Anda hanya bisa mengunggah 1 file per hari.")
    else:
        uploaded_files = st.file_uploader("Upload file PDF", type=["pdf"], accept_multiple_files=(st.session_state.user["role"] == "admin"))
        
        if uploaded_files:
            all_data = []
            for uploaded_file in uploaded_files:
                with pdfplumber.open(uploaded_file) as pdf:
                    text = "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])
                    all_data.append({"Filename": uploaded_file.name, "Content": text})
                
                # Catat upload ke database
                sb.table("uploads").insert({"username": st.session_state.user["username"], "date": today, "filename": uploaded_file.name}).execute()
            
            df = pd.DataFrame(all_data)
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                df.to_excel(writer, index=False, sheet_name="Data PDF")
            st.download_button(label="Download Excel", data=output.getvalue(), file_name="output.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    
    # Admin dapat melihat daftar user dan aktivitas upload
    if st.session_state.user["role"] == "admin":
        st.subheader("Manajemen User dan Upload")
        users_data = sb.table("users").select("username, role").execute().data
        st.write(pd.DataFrame(users_data))
        uploads_data = sb.table("uploads").select("username, date, filename").execute().data
        st.write(pd.DataFrame(uploads_data))
    
    if st.button("Logout"):
        st.session_state.user = None
        st.experimental_rerun()
