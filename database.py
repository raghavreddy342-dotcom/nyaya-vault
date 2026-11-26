"""Database setup and helpers for NYAYA VAULT."""

import sqlite3
import os
from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.dirname(__file__), "nyayavault.db")


def get_db():
    """Return a new database connection with row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create tables and seed demo data if DB doesn't exist."""
    conn = get_db()
    cur = conn.cursor()

    cur.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin', 'officer')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            created_by TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            original_name TEXT NOT NULL,
            case_id TEXT NOT NULL,
            file_type TEXT NOT NULL,
            file_size INTEGER NOT NULL,
            sha256_hash TEXT NOT NULL,
            encrypted_path TEXT NOT NULL,
            uploaded_by TEXT NOT NULL,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (case_id) REFERENCES cases(case_id)
        );

        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            action TEXT NOT NULL,
            details TEXT,
            record_hash TEXT,
            prev_hash TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Seed demo users if table is empty
    cur.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] == 0:
        demo_users = [
            ("admin", generate_password_hash("admin123"), "admin"),
            ("officer1", generate_password_hash("officer123"), "officer"),
        ]
        cur.executemany(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            demo_users,
        )

    # Seed demo cases if table is empty
    cur.execute("SELECT COUNT(*) FROM cases")
    if cur.fetchone()[0] == 0:
        demo_cases = [
            ("CASE-2026-001", "State vs. Sharma", "Financial fraud investigation involving forged documents.", "admin"),
            ("CASE-2026-002", "Property Dispute – Patel", "Land ownership dispute in Ahmedabad district.", "officer1"),
            ("CASE-2026-003", "Cyber Crime Unit – File #7", "Unauthorized access to banking systems.", "admin"),
        ]
        cur.executemany(
            "INSERT INTO cases (case_id, title, description, created_by) VALUES (?, ?, ?, ?)",
            demo_cases,
        )

    conn.commit()
    conn.close()
