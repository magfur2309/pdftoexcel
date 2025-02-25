import streamlit as st
import pandas as pd
import pdfplumber
import io
import re
import bcrypt
from supabase import create_client, Client
import datetime

# Inisialisasi Supabase
SUPABASE_URL = "https://ukajqoitsfsolloyewsj.supabase.co"  # Ganti dengan URL Supabase Anda
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVrYWpxb2l0c2Zzb2xsb3lld3NqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDAwMjUyMDEsImV4cCI6MjA1NTYwMTIwMX0.vllN8bcBG-wpjA9g7jjTMQ6_Xf-OgJdeIOu3by_cGP0"  # Ganti dengan API Key Supabase Anda

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# Fungsi Hash Password
def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


# Fungsi Verifikasi Password
def verify_password(password, hashed_password):
    return bcrypt.checkpw(password.encode(), hashed_password.encode())


# Fungsi Logout
def logout():
    st.session_state.clear()
    st.rerun()


# Fungsi Login
def login_page():
    st.title("Login Konversi Faktur Pajak")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        response = supabase.table("users").select("*").eq("username", username).execute()
        user_data = response.data

        if user_data and verify_password(password, user_data[0]["password"]):
            st.session_state["logged_in"] = True
            st.session_state["username"] = username
            st.session_state["role"] = user_data[0]["role"]
            st.session_state["upload_quota"] = user_data[0]["upload_quota"]
            st.rerun()
        else:
            st.error("Username atau password salah!")


# Fungsi untuk Cek Kuota Upload
def check_upload_quota(username):
    today = datetime.date.today().isoformat()
    response = supabase.table("uploads").select("*").eq("username", username).eq("date", today).execute()
    return len(response.data)  # Mengembalikan jumlah upload hari ini


# Fungsi untuk Menyimpan Log Upload
def log_upload(username):
    today = datetime.date.today().isoformat()
    supabase.table("uploads").insert({"username": username, "date": today}).execute()


# Fungsi Admin Panel
def admin_panel():
    st.title("Manajemen Pengguna")

    with st.form("add_user_form"):
        new_username = st.text_input("Username baru")
        new_password = st.text_input("Password baru", type="password")
        role = st.selectbox("Role", ["user", "admin"])
        upload_quota = st.number_input("Kuota Upload", min_value=1, value=1)
        submit = st.form_submit_button("Tambah User")

        if submit:
            if new_username and new_password:
                hashed_password = hash_password(new_password)
                response = supabase.table("users").select("id").eq("username", new_username).execute()

                if response.data:
                    st.error("Username sudah digunakan!")
                else:
                    supabase.table("users").insert({
                        "username": new_username,
                        "password": hashed_password,
                        "role": role,
                        "upload_quota": upload_quota
                    }).execute()
                    st.success(f"User {new_username} berhasil ditambahkan!")
                    st.rerun()
            else:
                st.error("Harap isi semua kolom!")

    users = supabase.table("users").select("id, username, role, upload_quota").execute().data

    for user in users:
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.write(user["username"])
        col2.write(user["role"])
        quota = col3.number_input(f"Kuota {user['username']}", value=user["upload_quota"], min_value=1, step=1)

        if col4.button(f"Update {user['username']}"):
            supabase.table("users").update({"upload_quota": quota}).eq("id", user["id"]).execute()
            st.success("Kuota diperbarui!")
            st.rerun()

        if col5.button(f"Hapus {user['username']}"):
            supabase.table("users").delete().eq("id", user["id"]).execute()
            st.warning(f"User {user['username']} dihapus!")
            st.rerun()


# Fungsi Utama Aplikasi
def main_app():
    st.title("Konversi Faktur Pajak PDF To Excel")

    if st.session_state["role"] == "user":
        today_uploads = check_upload_quota(st.session_state["username"])
        if today_uploads >= st.session_state["upload_quota"]:
            st.warning("Anda telah mencapai batas upload untuk hari ini.")
            return

    uploaded_files = st.file_uploader("Upload Faktur Pajak (PDF)", type=["pdf"], accept_multiple_files=True)

    if uploaded_files:
        all_data = []
        for uploaded_file in uploaded_files:
            log_upload(st.session_state["username"])  # Simpan log upload

            # Simulasi ekstraksi data (tidak ada perubahan pada fungsi utama)
            extracted_data = [["123456789", "Nama Penjual", "Nama Pembeli", "01/01/2025", "Barang A", 2, "pcs", 10000, 0, 20000, 18000, 2000]]
            all_data.extend(extracted_data)

        if all_data:
            df = pd.DataFrame(all_data, columns=[
                "No FP", "Nama Penjual", "Nama Pembeli", "Tanggal Faktur", "Nama Barang",
                "Qty", "Satuan", "Harga", "Potongan Harga", "Total", "DPP", "PPN"
            ])
            df.index += 1
            st.dataframe(df)

            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                df.to_excel(writer, index=True, sheet_name="Faktur Pajak")
            output.seek(0)

            st.download_button(
                label="\U0001F4E5 Unduh Excel",
                data=output,
                file_name="Faktur_Pajak.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.error("Gagal mengekstrak data!")


# Menjalankan Aplikasi
if __name__ == "__main__":
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False

    if not st.session_state["logged_in"]:
        login_page()
    else:
        st.sidebar.write(f"**User: {st.session_state['username']}**")
        if st.sidebar.button("Logout"):
            logout()

        if st.session_state["role"] == "admin":
            st.sidebar.button("Kelola Pengguna", on_click=lambda: st.session_state.update({"admin_panel": True}))
            if st.session_state.get("admin_panel"):
                admin_panel()
            else:
                main_app()
        else:
            main_app()
