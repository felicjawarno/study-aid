import sqlite3
from sqlite3 import Error
from pathlib import Path

def create_connection(db_file="database/projects.db"):
    """Create a database connection"""
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        # Enable foreign key constraints
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    except Error as e:
        print(f"Connection error: {e}")
        return None

def setup_database(conn, sql_file="database/db_setup.sql"):
    """Execute SQL from external file"""
    try:
        sql_script = Path(sql_file).read_text()
        conn.executescript(sql_script)
        print(f"Database schema loaded from {sql_file}")
    except Error as e:
        print(f"Setup error: {e}")
    except FileNotFoundError:
        print(f"SQL file not found: {sql_file}")

if __name__ == "__main__":
    db_conn = create_connection()
    if db_conn:
        setup_database(db_conn)
        db_conn.close()
        print("Database setup completed.")