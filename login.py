import streamlit as st
import hashlib

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def check_login():
    st.title("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    login_button = st.button("Login")
    
    user_data = {
        "admin": hash_password("password123"),
        "user": hash_password("userpass")
    }
    
    if login_button:
        if username in user_data and user_data[username] == hash_password(password):
            st.session_state["authenticated"] = True
            st.success("Login berhasil! Akses diberikan.")
            st.experimental_rerun()
        else:
            st.error("Username atau password salah")

def main():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    
    if not st.session_state["authenticated"]:
        check_login()
    else:
        st.success("Anda sudah login. Silakan buka aplikasi utama.")
        st.write("[Buka Aplikasi Utama](app.py)")

if __name__ == "__main__":
    main()
