import sqlite3
import os
from datetime import datetime
from typing import Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "database.db")

def init_db():
    """Initializes the database and creates the necessary table."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS uploaded_assets (
                image_hash TEXT PRIMARY KEY,
                original_asset_id INTEGER NOT NULL,
                new_asset_id INTEGER NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

def get_uploaded_asset(image_hash: str) -> Optional[int]:
    """
    Checks if an image hash already exists in the database.
    Returns the new_asset_id if found, else None.
    """
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT new_asset_id FROM uploaded_assets WHERE image_hash = ?",
            (image_hash,)
        )
        row = cursor.fetchone()
        return row[0] if row else None

def save_uploaded_asset(image_hash: str, original_asset_id: int, new_asset_id: int):
    """Saves a new upload record to the database."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO uploaded_assets (image_hash, original_asset_id, new_asset_id) VALUES (?, ?, ?)",
            (image_hash, original_asset_id, new_asset_id)
        )
        conn.commit()

# Initialize the DB on module import
init_db()
