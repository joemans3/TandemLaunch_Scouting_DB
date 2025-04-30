import os
import sqlite3
from pathlib import Path

import requests

DEFAULT_DB_PATH = Path.home() / "scouting-database" / "app.db"
DATABASE_FILE = Path(os.getenv("SCOUTING_DB_PATH", str(DEFAULT_DB_PATH)))
DATABASE_FILE.parent.mkdir(parents=True, exist_ok=True)


def get_connection():
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialize_database():
    conn = get_connection()
    cursor = conn.cursor()

    # Universities with ROR identifiers
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS universities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            ror_id TEXT UNIQUE NOT NULL
        )
    """)

    # Aliases for universities (e.g., MIT -> Massachusetts Institute of Technology)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS university_aliases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alias TEXT UNIQUE NOT NULL,
            university_id INTEGER NOT NULL,
            FOREIGN KEY (university_id) REFERENCES universities(id)
        )
    """)

    # Countries with ISO codes
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS countries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            code TEXT UNIQUE NOT NULL
        )
    """)

    # People table with links to universities and countries
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS people (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            university_id INTEGER NOT NULL,
            country_id INTEGER NOT NULL,
            subfield TEXT NOT NULL,
            subfield_name TEXT NOT NULL,
            role TEXT NOT NULL,
            notes TEXT,
            FOREIGN KEY (university_id) REFERENCES universities(id),
            FOREIGN KEY (country_id) REFERENCES countries(id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS email_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id INTEGER NOT NULL,
            timestamp TEXT NOT NULL,
            subject TEXT,
            body TEXT,
            thread_id TEXT,
            FOREIGN KEY (person_id) REFERENCES people(id)
        )
    """)
    conn.commit()

    preload_countries(conn)
    conn.close()


def preload_countries(conn):
    cursor = conn.cursor()
    try:
        resp = requests.get("https://restcountries.com/v3.1/all")
        resp.raise_for_status()
        data = resp.json()
        for item in data:
            name = item["name"]["common"]
            code = item["cca2"]
            try:
                cursor.execute(
                    "INSERT INTO countries (name, code) VALUES (?, ?)", (name, code)
                )
            except sqlite3.IntegrityError:
                continue
        conn.commit()
    except Exception as e:
        print("Country preload failed:", e)
