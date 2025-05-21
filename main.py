import streamlit as st
import auth 
import app 
import time
from database import database_manager

# Session state initialization
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.page = "login"
    st.session_state.username = ""
    st.session_state.rerun_key = 0
    st.session_state.uploaded_pdfs = {}
    st.session_state.selected_pdf = None
    st.session_state.last_rerun = time.time()

# Generate unique keys based on rerun count and timestamp
def generate_key(prefix):
    return f"{prefix}_{st.session_state.rerun_key}_{time.time()}"

# Main routing logic
def main():
    # database_setup.main()
    database_manager.sync_projects_directory()
    app.main_app()
    # if st.session_state.logged_in and st.session_state.page == "login":
    #     st.session_state.page = "main"
    #     st.session_state.rerun_key += 1
    #     st.rerun()
    #
    # if st.session_state.page == "login":
    #     auth.login()
    # elif st.session_state.page == "register":
    #     auth.register()
    # elif st.session_state.page == "main" and st.session_state.logged_in:
    #     app.main_app()
    # else:
    #     st.warning("You must log in first.")
    #     st.session_state.page = "login"
    #     st.session_state.rerun_key += 1
    #     st.rerun()

if __name__ == "__main__":
    main()