import streamlit as st
import auth 
import app 
import time
from database import database_manager
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.page = "login"
    st.session_state.username = ""
    st.session_state.rerun_key = 0
    st.session_state.uploaded_pdfs = {}
    st.session_state.selected_pdf = None
    st.session_state.last_rerun = time.time()

def generate_key(prefix):
    return f"{prefix}_{st.session_state.rerun_key}_{time.time()}"

def main():
    # database_setup.main() <- initializing db when we start using programme
    database_manager.sync_projects_directory()
    app.main_app()
if __name__ == "__main__":
    main()