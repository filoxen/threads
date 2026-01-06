import sqlite3
import os
from datetime import datetime
from typing import Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "database.db")

def init_db():
    """Initializes the database and creates the necessary table."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        
        # Check if we need to migrate uploaded_assets
        cursor.execute("PRAGMA table_info(uploaded_assets)")
        columns = {col[1]: col for col in cursor.fetchall()}
        
        # If the table exists and image_hash is the sole PK, migrate it
        # col[5] is the 'pk' indicator in PRAGMA table_info
        if "image_hash" in columns and columns["image_hash"][5] == 1 and ("asset_type" not in columns or columns["asset_type"][5] == 0):
            print("Migrating uploaded_assets to composite primary key...")
            
            # 1. Rename old table
            cursor.execute("ALTER TABLE uploaded_assets RENAME TO uploaded_assets_old")
            
            # 2. Create new table
            cursor.execute("""
                CREATE TABLE uploaded_assets (
                    image_hash TEXT,
                    asset_type INTEGER,
                    original_asset_id INTEGER NOT NULL,
                    new_asset_id INTEGER NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (image_hash, asset_type)
                )
            """)
            
            # 3. Copy data (defaulting old records to Shirt type = 11 if unknown)
            cursor.execute("""
                INSERT INTO uploaded_assets (image_hash, asset_type, original_asset_id, new_asset_id, created_at)
                SELECT image_hash, COALESCE(asset_type, 11), original_asset_id, new_asset_id, created_at
                FROM uploaded_assets_old
            """)
            
            # 4. Drop old table
            cursor.execute("DROP TABLE uploaded_assets_old")
            print("Migration complete.")
        else:
            # Standard creation if not exists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS uploaded_assets (
                    image_hash TEXT,
                    asset_type INTEGER,
                    original_asset_id INTEGER NOT NULL,
                    new_asset_id INTEGER NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (image_hash, asset_type)
                )
            """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS onsale_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asset_id INTEGER NOT NULL,
                original_asset_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                group_id INTEGER NOT NULL,
                asset_type TEXT NOT NULL,
                retry_count INTEGER DEFAULT 0,
                next_retry DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

def get_uploaded_asset(image_hash: str, asset_type: int) -> Optional[int]:
    """
    Checks if an image hash and asset type already exists in the database.
    Returns the new_asset_id if found, else None.
    """
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT new_asset_id FROM uploaded_assets WHERE image_hash = ? AND asset_type = ?",
            (image_hash, asset_type)
        )
        row = cursor.fetchone()
        return row[0] if row else None

def save_uploaded_asset(image_hash: str, asset_type: int, original_asset_id: int, new_asset_id: int):
    """Saves a new upload record to the database."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO uploaded_assets (image_hash, asset_type, original_asset_id, new_asset_id) VALUES (?, ?, ?, ?)",
            (image_hash, asset_type, original_asset_id, new_asset_id)
        )
        conn.commit()

def add_to_onsale_queue(asset_id: int, original_asset_id: int, name: str, description: str, group_id: int, asset_type: str):
    """Adds an asset to the onsale retry queue."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO onsale_queue (asset_id, original_asset_id, name, description, group_id, asset_type) VALUES (?, ?, ?, ?, ?, ?)",
            (asset_id, original_asset_id, name, description, group_id, asset_type)
        )
        conn.commit()

def get_pending_onsale_items():
    """Retrieves items from the queue that are ready for retry."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM onsale_queue WHERE next_retry <= CURRENT_TIMESTAMP"
        )
        return cursor.fetchall()

def remove_from_onsale_queue(queue_id: int):
    """Removes an item from the onsale queue."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM onsale_queue WHERE id = ?", (queue_id,))
        conn.commit()

def increment_retry_onsale(queue_id: int, delay_seconds: int = 300):
    """Increments retry count and sets next retry time."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE onsale_queue 
            SET retry_count = retry_count + 1, 
                next_retry = datetime('now', '+' || ? || ' seconds')
            WHERE id = ?
            """,
            (delay_seconds, queue_id)
        )
        conn.commit()

# Initialize the DB on module import
init_db()
