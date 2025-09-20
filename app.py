from flask import Flask, render_template, request, redirect, url_for, session, jsonify, g, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import os, datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'khata.db')

app = Flask(__name__)
app.secret_key = "khata_secret_key_please_change"

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DB_PATH)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exc):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        username TEXT UNIQUE,
        password_hash TEXT,
        shop_name TEXT,
        shop_address TEXT,
        language TEXT DEFAULT 'en',
        created_at TEXT
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        name TEXT,
        unit TEXT,
        price REAL
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS bills (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        total REAL,
        payment_method TEXT,
        created_at TEXT
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS bill_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bill_id INTEGER,
        item_name TEXT,
        unit TEXT,
        price_per_unit REAL,
        quantity REAL,
        subtotal REAL
    )""")
    db.commit()

@app.before_first_request
def before_first():
    init_db()

# user loader
def current_user():
    if 'user_id' in session:
        db = get_db()
        u = db.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],)).fetchone()
        return u
    return None

@app.route('/')
def index():
    if current_user():
        return redirect(url_for('billing'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        username = request.form['username']
        password = request.form['password']
        shop_name = request.form['shop_name']
        shop_address = request.form['shop_address']
        lang = request.form.get('language','en')
        phash = generate_password_hash(password)
        db = get_db()
        try:
            db.execute("INSERT INTO users (name, username, password_hash, shop_name, shop_address, language, created_at) VALUES (?,?,?,?,?,?,?)",
                       (name, username, phash, shop_name, shop_address, lang, datetime.datetime.now().isoformat()))
            db.commit()
            flash("Registered. Please login.", "success")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("Username already exists.", "danger")
    return render_template('register.html', user=None)

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        u = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if u and check_password_hash(u['password_hash'], password):
            session['user_id'] = u['id']
            session['username'] = u['username']
            return redirect(url_for('billing'))
        else:
            flash("Invalid credentials", "danger")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/profile', methods=['GET','POST'])
def profile():
    u = current_user()
    if not u:
        return redirect(url_for('login'))
    db = get_db()
    if request.method == 'POST':
        name = request.form['name']
        shop_name = request.form['shop_name']
        shop_address = request.form['shop_address']
        language = request.form.get('language','en')
        db.execute("UPDATE users SET name=?, shop_name=?, shop_address=?, language=? WHERE id=?",
                   (name, shop_name, shop_address, language, u['id']))
        db.commit()
        flash("Profile updated", "success")
        return redirect(url_for('profile'))
    return render_template('profile.html', user=u)

@app.route('/items', methods=['GET','POST'])
def items():
    u = current_user()
    if not u:
        return redirect(url_for('login'))
    db = get_db()
    if request.method == 'POST':
        name = request.form['name']
        unit = request.form['unit']
        price = float(request.form['price'])
        db.execute("INSERT INTO items (user_id, name, unit, price) VALUES (?,?,?,?)",
                   (u['id'], name, unit, price))
        db.commit()
        flash("Item added.", "success")
        return redirect(url_for('items'))
    cur = db.execute("SELECT * FROM items WHERE user_id = ?", (u['id'],))
    items = cur.fetchall()
    return render_template('items.html', items=items, user=u)

@app.route('/api/items')
def api_items():
    u = current_user()
    if not u:
        return jsonify([]), 401
    db = get_db()
    cur = db.execute("SELECT id,name,unit,price FROM items WHERE user_id = ?", (u['id'],))
    data = [dict(x) for x in cur.fetchall()]
    return jsonify(data)

@app.route('/save_bill', methods=['POST'])
def save_bill():
    u = current_user()
    if not u:
        return jsonify({"error":"not logged in"}), 401
    data = request.get_json()
    items = data.get('items', [])
    total = float(data.get('total', 0))
    payment_method = data.get('payment_method', 'Cash')
    db = get_db()
    cur = db.cursor()
    cur.execute("INSERT INTO bills (user_id, total, payment_method, created_at) VALUES (?,?,?,?)",
                (u['id'], total, payment_method, datetime.datetime.now().isoformat()))
    bill_id = cur.lastrowid
    for it in items:
        cur.execute("INSERT INTO bill_items (bill_id, item_name, unit, price_per_unit, quantity, subtotal) VALUES (?,?,?,?,?,?)",
                    (bill_id, it['name'], it.get('unit','unit'), float(it['price']), float(it['qty']), float(it['subtotal'])))
    db.commit()
    return jsonify({"status":"ok", "bill_id": bill_id})

@app.route('/saved_bills')
def saved_bills():
    u = current_user()
    if not u:
        return redirect(url_for('login'))
    db = get_db()
    bills = db.execute("SELECT * FROM bills WHERE user_id = ? ORDER BY created_at DESC", (u['id'],)).fetchall()
    return render_template('saved_bills.html', bills=bills, user=u)

@app.route('/bill/<int:bill_id>')
def bill_view(bill_id):
    u = current_user()
    if not u:
        return redirect(url_for('login'))
    db = get_db()
    bill = db.execute("SELECT * FROM bills WHERE id = ? AND user_id = ?", (bill_id, u['id'])).fetchone()
    if not bill:
        flash("Bill not found", "danger")
        return redirect(url_for('saved_bills'))
    items = db.execute("SELECT * FROM bill_items WHERE bill_id = ?", (bill_id,)).fetchall()
    return render_template('bill_view.html', bill=bill, items=items, user=u)

@app.route('/delete_item/<int:item_id>', methods=['POST'])
def delete_item(item_id):
    u = current_user()
    if not u:
        return redirect(url_for('login'))
    db = get_db()
    db.execute("DELETE FROM items WHERE id = ? AND user_id = ?", (item_id, u['id']))
    db.commit()
    return redirect(url_for('items'))

@app.route('/billing')
def billing():
    u = current_user()
    if not u:
        return redirect(url_for('login'))
    return render_template('billing.html', user=u)

if __name__ == '__main__':
    # allow running with python app.py
    app.run(debug=True)
