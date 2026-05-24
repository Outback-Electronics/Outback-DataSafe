import sqlite3
from pathlib import Path
from contextlib import contextmanager
from datetime import datetime
from typing import Optional, List, Dict
import json

class Database:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.init_database()
    
    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def init_database(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    quota INTEGER NOT NULL,
                    used_space INTEGER DEFAULT 0,
                    tier TEXT DEFAULT 'free',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_admin BOOLEAN DEFAULT FALSE
                )
            """)
            
            # Files table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    filename TEXT NOT NULL,
                    original_filename TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    mime_type TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    parent_id INTEGER,
                    is_directory BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    FOREIGN KEY (parent_id) REFERENCES files(id)
                )
            """)
            
            # Photos table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS photos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    file_id INTEGER NOT NULL,
                    file_path TEXT NOT NULL,
                    thumbnail_path TEXT,
                    width INTEGER,
                    height INTEGER,
                    capture_date TIMESTAMP,
                    location TEXT,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    FOREIGN KEY (file_id) REFERENCES files(id)
                )
            """)
            
            # Faces table (for face recognition)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS faces (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    photo_id INTEGER NOT NULL,
                    face_encoding TEXT NOT NULL,
                    face_box TEXT NOT NULL,
                    confidence REAL,
                    person_id INTEGER,
                    FOREIGN KEY (photo_id) REFERENCES photos(id)
                )
            """)
            
            # People table (for identified persons)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS people (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            
            # Sharing table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS shares (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_id INTEGER NOT NULL,
                    shared_by INTEGER NOT NULL,
                    shared_with INTEGER,
                    share_token TEXT UNIQUE,
                    expires_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (file_id) REFERENCES files(id),
                    FOREIGN KEY (shared_by) REFERENCES users(id),
                    FOREIGN KEY (shared_with) REFERENCES users(id)
                )
            """)
            
            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_user_id ON files(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_parent_id ON files(parent_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_photos_user_id ON photos(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_faces_photo_id ON faces(photo_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_faces_person_id ON faces(person_id)")
    
    def create_user(self, username: str, email: str, password_hash: str, quota: int, tier: str = "free", is_admin: bool = False) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (username, email, password_hash, quota, tier, is_admin) VALUES (?, ?, ?, ?, ?, ?)",
                (username, email, password_hash, quota, tier, is_admin)
            )
            return cursor.lastrowid
    
    def get_user(self, username: str) -> Optional[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def update_user_storage(self, user_id: int, size_change: int):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET used_space = used_space + ? WHERE id = ?",
                (size_change, user_id)
            )
    
    def create_file(self, user_id: int, filename: str, original_filename: str, 
                   file_path: str, file_size: int, mime_type: str, 
                   parent_id: Optional[int] = None, is_directory: bool = False) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO files (user_id, filename, original_filename, file_path, file_size, 
                   mime_type, parent_id, is_directory) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (user_id, filename, original_filename, file_path, file_size, mime_type, parent_id, is_directory)
            )
            file_id = cursor.lastrowid
            # Update user storage
            if not is_directory:
                self.update_user_storage(user_id, file_size)
            return file_id
    
    def get_files(self, user_id: int, parent_id: Optional[int] = None) -> List[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if parent_id is None:
                cursor.execute("SELECT * FROM files WHERE user_id = ? AND parent_id IS NULL", (user_id,))
            else:
                cursor.execute("SELECT * FROM files WHERE user_id = ? AND parent_id = ?", (user_id, parent_id))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def get_file(self, file_id: int) -> Optional[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM files WHERE id = ?", (file_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def delete_file(self, file_id: int):
        file_data = self.get_file(file_id)
        if file_data and not file_data['is_directory']:
            self.update_user_storage(file_data['user_id'], -file_data['file_size'])
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM files WHERE id = ?", (file_id,))
    
    def create_photo(self, user_id: int, file_id: int, file_path: str, 
                    width: int, height: int, capture_date: Optional[str] = None,
                    location: Optional[str] = None, metadata: Optional[str] = None) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO photos (user_id, file_id, file_path, width, height, capture_date, location, metadata) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (user_id, file_id, file_path, width, height, capture_date, location, metadata)
            )
            return cursor.lastrowid
    
    def get_photos(self, user_id: int, limit: int = 100, offset: int = 0) -> List[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM photos WHERE user_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (user_id, limit, offset)
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def update_photo_thumbnail(self, photo_id: int, thumbnail_path: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE photos SET thumbnail_path = ? WHERE id = ?",
                (thumbnail_path, photo_id)
            )
