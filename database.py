import sqlite3, json, os
DB_NAME = os.path.expanduser('~/neighbors_bot.db')

def get_conn():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER UNIQUE, username TEXT,
                  role TEXT DEFAULT 'customer', categories TEXT, rating REAL DEFAULT 0.0,
                  rating_count INTEGER DEFAULT 0, is_verified INTEGER DEFAULT 0)''')
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='requests'")
    if not c.fetchone():
        c.execute('''CREATE TABLE requests
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, username TEXT, text TEXT,
                      category TEXT, subcategory TEXT, status TEXT DEFAULT 'new', master_id INTEGER,
                      master_username TEXT, timing TEXT, contact TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    else:
        for col, typ in [('is_verified', 'INTEGER DEFAULT 0'), ('timing', 'TEXT'), ('contact', 'TEXT'), ('created_at', 'TIMESTAMP')]:
            try: c.execute(f'ALTER TABLE requests ADD COLUMN {col} {typ}')
            except: pass
    conn.commit(); conn.close()

def _get_user(uid):
    conn = get_conn()
    try:
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE user_id = ?', (uid,))
        res = c.fetchone()
        if res:
            res = dict(res)
            if res.get('categories'):
                try: res['categories'] = json.loads(res['categories'])
                except: res['categories'] = []
            return res
        return None
    finally: conn.close()

def _save_user(uid, un, role, cats):
    conn = get_conn()
    try:
        c = conn.cursor()
        c.execute('INSERT OR REPLACE INTO users (user_id, username, role, categories) VALUES (?, ?, ?, ?)',
                  (uid, un, role, json.dumps(cats) if cats else '[]'))
        conn.commit()
    finally: conn.close()

def _verify_user(uid):
    conn = get_conn()
    try:
        c = conn.cursor()
        c.execute('UPDATE users SET is_verified = 1 WHERE user_id = ?', (uid,))
        conn.commit()
    finally: conn.close()

def _save_request(uid, un, text, cat, sub, timing=None, contact=None):
    conn = get_conn()
    try:
        c = conn.cursor()
        c.execute('''INSERT INTO requests (user_id, username, text, category, subcategory, status, timing, contact)
                     VALUES (?, ?, ?, ?, ?, 'new', ?, ?)''', (uid, un, text, cat, sub, timing, contact))
        rid = c.lastrowid; conn.commit(); return rid
    finally: conn.close()

def _get_request(rid):
    conn = get_conn()
    try:
        c = conn.cursor()
        c.execute('SELECT * FROM requests WHERE id = ?', (rid,))
        res = c.fetchone(); return dict(res) if res else None
    finally: conn.close()

def _get_reqs_by_user(uid):
    conn = get_conn()
    try:
        c = conn.cursor()
        c.execute('SELECT * FROM requests WHERE user_id = ? ORDER BY id DESC', (uid,))
        return [dict(r) for r in c.fetchall()]
    finally: conn.close()

def _get_reqs_by_master(mid):
    conn = get_conn()
    try:
        c = conn.cursor()
        c.execute('SELECT * FROM requests WHERE master_id = ? ORDER BY id DESC', (mid,))
        return [dict(r) for r in c.fetchall()]
    finally: conn.close()

def _update_status(rid, status, mid=None, mun=None):
    conn = get_conn()
    try:
        c = conn.cursor()
        if mun is not None: c.execute('UPDATE requests SET status=?, master_id=?, master_username=? WHERE id=?', (status, mid, mun, rid))
        else: c.execute('UPDATE requests SET status=?, master_id=? WHERE id=?', (status, mid, rid))
        conn.commit()
    finally: conn.close()

def _update_text(rid, text):
    conn = get_conn()
    try:
        c = conn.cursor()
        c.execute('UPDATE requests SET text=? WHERE id=?', (text, rid))
        conn.commit()
    finally: conn.close()

def _update_rating(mid, rating):
    conn = get_conn()
    try:
        c = conn.cursor()
        c.execute('SELECT rating, rating_count FROM users WHERE user_id=?', (mid,))
        res = c.fetchone()
        if res:
            cr = res['rating'] or 0.0; cnt = res['rating_count'] or 0
            nr = ((cr * cnt) + rating) / (cnt + 1)
            c.execute('UPDATE users SET rating=?, rating_count=? WHERE user_id=?', (nr, cnt + 1, mid))
            conn.commit()
    finally: conn.close()

def _unsub_master(uid):
    conn = get_conn()
    try:
        c = conn.cursor()
        c.execute("UPDATE users SET categories='[]', role='customer' WHERE user_id=?", (uid,))
        conn.commit()
    finally: conn.close()

def _archive_old():
    conn = get_conn()
    try:
        c = conn.cursor()
        c.execute("UPDATE requests SET status='archived' WHERE status='new' AND created_at < datetime('now','-3 days')")
        conn.commit()
    finally: conn.close()

class Database:
    def __init__(self): init_db()
    def get_user(self, uid): return _get_user(uid)
    def save_user(self, uid, un, role, cats): _save_user(uid, un, role, cats)
    def verify_user(self, uid): _verify_user(uid)
    def save_request(self, uid, un, text, cat, sub, timing=None, contact=None): return _save_request(uid, un, text, cat, sub, timing, contact)
    def get_request(self, rid): return _get_request(rid)
    def get_requests_by_user(self, uid): return _get_reqs_by_user(uid)
    def get_requests_by_master(self, mid): return _get_reqs_by_master(mid)
    def update_request_status(self, rid, st, mid=None, mun=None): _update_status(rid, st, mid, mun)
    def update_request_text(self, rid, text): _update_text(rid, text)
    def update_rating(self, mid, r): _update_rating(mid, r)
    def unsubscribe_master(self, uid): _unsub_master(uid)
    def archive_old_requests(self): _archive_old()

init_db()
