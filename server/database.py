import os
import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = Path.home() / ".cache" / "scouting_data" / "app.db"
DATABASE_FILE = Path(os.getenv("SCOUTING_DB_PATH", str(DEFAULT_DB_PATH)))
DATABASE_FILE.parent.mkdir(parents=True, exist_ok=True)


def get_connection():
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row  # access columns by name
    return conn


def initialize_database():
    conn = get_connection()
    cursor = conn.cursor()

    # Universities
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS universities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
    """)

    # Departments
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS departments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            university_id INTEGER NOT NULL,
            FOREIGN KEY(university_id) REFERENCES universities(id) ON DELETE CASCADE
        )
    """)

    # Department Heads
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS department_heads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            department_id INTEGER NOT NULL,
            university_id INTEGER NOT NULL,
            FOREIGN KEY(department_id) REFERENCES departments(id) ON DELETE CASCADE,
            FOREIGN KEY(university_id) REFERENCES universities(id) ON DELETE CASCADE
        )
    """)

    # 🔵 Admins
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            department_id INTEGER NOT NULL,
            university_id INTEGER NOT NULL,
            FOREIGN KEY(department_id) REFERENCES departments(id) ON DELETE CASCADE,
            FOREIGN KEY(university_id) REFERENCES universities(id) ON DELETE CASCADE
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS catalog_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            university_name TEXT NOT NULL,
            department_name TEXT NOT NULL,
            department_head_name TEXT,
            department_head_email TEXT,
            admin_name TEXT,
            admin_email TEXT
        )
    """)
    conn.commit()
    conn.close()
