import streamlit as st
import json
import os

USERS_FILE = "users.json"

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f)

users = load_users()

def login():
    st.subheader("🔐 Login")
    username_key = f"login_user_{st.session_state.rerun_key}"
    password_key = f"login_pass_{st.session_state.rerun_key}"
    login_button_key = f"login_btn_{st.session_state.rerun_key}"
    register_button_key = f"reg_btn_{st.session_state.rerun_key}"
    
    username = st.text_input("Username", key=username_key)
    password = st.text_input("Password", type="password", key=password_key)

    if st.button("Login", key=login_button_key):
        if username in users and users[username] == password:
            st.session_state.logged_in = True
            st.session_state.username = username
            st.session_state.page = "main"
            st.rerun()
        else:
            st.error("Incorrect username or password.")

    if st.button("Create an account", key=register_button_key):
        st.session_state.page = "register"
        st.rerun()

def register():
    st.subheader("📝 Register")
    new_user_key = f"new_user_{st.session_state.rerun_key}"
    new_pass_key = f"new_pass_{st.session_state.rerun_key}"
    reg_button_key = f"reg_btn_{st.session_state.rerun_key}"
    back_button_key = f"back_btn_{st.session_state.rerun_key}"
    
    new_username = st.text_input("Choose a username", key=new_user_key)
    new_password = st.text_input("Choose a password", type="password", key=new_pass_key)

    if st.button("Register", key=reg_button_key):
        if new_username == "" or new_password == "":
            st.warning("Username and password cannot be empty.")
        elif new_username in users:
            st.error("Username already exists.")
        else:
            users[new_username] = new_password
            save_users(users)
            st.success("Account created! You can now log in.")
            st.session_state.page = "login"
            st.rerun()

    if st.button("Back to login", key=back_button_key):
        st.session_state.page = "login"
        st.rerun()