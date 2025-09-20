import sqlite3
from werkzeug.security import generate_password_hash
import datetime

conn = sqlite3.connect('khata.db')
c = conn.cursor()

# create tables
c.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    username TEXT UNIQUE,
    password_hash TEXT,
    shop_name TEXT,
    shop_address TEXT,
    language TEXT DEFAULT 'en',
    created_at TEXT
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    name TEXT,
    unit TEXT,
    price REAL,
    FOREIGN KEY(user_id) REFERENCES users(id)
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS bills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    total REAL,
    payment_method TEXT,
    created_at TEXT,
    FOREIGN KEY(user_id) REFERENCES users(id)
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS bill_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bill_id INTEGER,
    item_name TEXT,
    unit TEXT,
    price_per_unit REAL,
    quantity REAL,
    subtotal REAL,
    FOREIGN KEY(bill_id) REFERENCES bills(id)
)
""")

# Insert a demo user and demo items if not exists
c.execute("SELECT id FROM users WHERE username = ?", ('demo',))
if not c.fetchone():
    now = datetime.datetime.now().isoformat()
    c.execute("INSERT INTO users (name, username, password_hash, shop_name, shop_address, language, created_at) VALUES (?,?,?,?,?,?,?)",
              ('Demo User','demo', generate_password_hash('demo123'), 'Demo Shop', 'Demo Address', 'en', now))
    user_id = c.lastrowid
    # add demo items
    items = [
        ('Sugar', 'kg', 45.0),
        ('Milk', 'liter', 55.0),
        ('Biscuit Pack', 'unit', 20.0)
    ]
    for name, unit, price in items:
        c.execute("INSERT INTO items (user_id, name, unit, price) VALUES (?,?,?)", (user_id, name, unit, price))

conn.commit()
conn.close()
print("DB initialized (khata.db)")
