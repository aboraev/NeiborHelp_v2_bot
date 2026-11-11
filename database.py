import sqlite3
import os
import json

DB_PATH = '/data/data/com.termux/files/home/database.db'

class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH)
        self.cursor = self.conn.cursor()
        self.create_tables()
    
    def create_tables(self):
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            role TEXT DEFAULT 'customer',
            categories TEXT DEFAULT '[]'
        )''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            text TEXT,
            category TEXT,
            subcategory TEXT DEFAULT 'Другое',
            status TEXT DEFAULT 'new',
            executor_id INTEGER,
            executor_username TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS ratings (
            user_id INTEGER PRIMARY KEY,
            total_rating INTEGER DEFAULT 0,
            rating_count INTEGER DEFAULT 0
        )''')
        self.conn.commit()
    
    def save_user(self, user_id, username, role, categories):
        cats = json.dumps(categories)
        self.cursor.execute('INSERT OR REPLACE INTO users (id, username, role, categories) VALUES (?, ?, ?, ?)',
                           (user_id, username, role, cats))
        self.conn.commit()
    
    def get_user(self, user_id):
        self.cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        return self.cursor.fetchone()
    
    def save_request(self, user_id, username, text, category, subcategory='Другое'):
        self.cursor.execute('INSERT INTO requests (user_id, username, text, category, subcategory) VALUES (?, ?, ?, ?, ?)',
                           (user_id, username, text, category, subcategory))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def get_request(self, request_id):
        self.cursor.execute('SELECT * FROM requests WHERE id = ?', (request_id,))
        return self.cursor.fetchone()
    
    def get_requests_by_user(self, user_id):
        self.cursor.execute('SELECT id, text, category, status, executor_username, created_at FROM requests WHERE user_id = ? ORDER BY id DESC', (user_id,))
        return self.cursor.fetchall()
    
    def get_requests_by_master(self, master_id):
        self.cursor.execute('SELECT id, text, category, status, subcategory, created_at FROM requests WHERE executor_id = ? ORDER BY id DESC', (master_id,))
        return self.cursor.fetchall()
    
    def update_request_status(self, request_id, status, executor_id=None, executor_username=None):
        self.cursor.execute('UPDATE requests SET status = ?, executor_id = ?, executor_username = ? WHERE id = ?',
                           (status, executor_id, executor_username, request_id))
        self.conn.commit()
    
    def update_request_text(self, request_id, text):
        self.cursor.execute('UPDATE requests SET text = ? WHERE id = ?', (text, request_id))
        self.conn.commit()
    
    def update_rating(self, user_id, rating):
        self.cursor.execute('INSERT OR IGNORE INTO ratings (user_id) VALUES (?)', (user_id,))
        self.cursor.execute('UPDATE ratings SET total_rating = total_rating + ?, rating_count = rating_count + 1 WHERE user_id = ?',
                           (rating, user_id))
        self.conn.commit()