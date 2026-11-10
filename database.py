import sqlite3
from datetime import datetime

class Database:
    def __init__(self, db_name="bot.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()
    
    def create_tables(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                role TEXT,
                categories TEXT,
                rating INTEGER DEFAULT 0,
                completed_requests INTEGER DEFAULT 0
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS requests (
                request_id INTEGER PRIMARY KEY AUTOINCREMENT,
                author_id INTEGER,
                author_username TEXT,
                text TEXT,
                category TEXT,
                status TEXT DEFAULT 'new',
                executor_id INTEGER,
                executor_username TEXT,
                rating INTEGER,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        self.conn.commit()
    
    def save_user(self, user_id, username, role, categories=None):
        self.cursor.execute("INSERT OR REPLACE INTO users (user_id, username, role, categories) VALUES (?, ?, ?, ?)", (user_id, username, role, str(categories)))
        self.conn.commit()
    
    def get_user(self, user_id):
        self.cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return self.cursor.fetchone()
    
    def save_request(self, author_id, author_username, text, category):
        now = datetime.now().isoformat()
        self.cursor.execute("INSERT INTO requests (author_id, author_username, text, category, status, created_at, updated_at) VALUES (?, ?, ?, ?, 'new', ?, ?)", (author_id, author_username, text, category, now, now))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def update_request_status(self, request_id, status, executor_id=None, executor_username=None):
        now = datetime.now().isoformat()
        self.cursor.execute("UPDATE requests SET status = ?, executor_id = ?, executor_username = ?, updated_at = ? WHERE request_id = ?", (status, executor_id, executor_username, now, request_id))
        self.conn.commit()
    
    def get_request(self, request_id):
        self.cursor.execute("SELECT * FROM requests WHERE request_id = ?", (request_id,))
        return self.cursor.fetchone()
    
    def get_requests_by_user(self, user_id):
        self.cursor.execute("SELECT request_id, text, category, status, executor_username, created_at FROM requests WHERE author_id = ? ORDER BY created_at DESC", (user_id,))
        return self.cursor.fetchall()
    
    def get_requests_by_master(self, master_id):
        self.cursor.execute("SELECT request_id, text, category, status, executor_username, created_at FROM requests WHERE executor_id = ? ORDER BY created_at DESC", (master_id,))
        return self.cursor.fetchall()
    
    def update_rating(self, executor_id, rating):
        self.cursor.execute("UPDATE users SET rating = ? WHERE user_id = ?", (rating, executor_id))
        self.conn.commit()
