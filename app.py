from flask import Flask, request, jsonify, render_template, redirect, url_for, session
import time, hashlib, requests, sqlite3, json, os, traceback

app = Flask(__name__)
app.secret_key = "axiom_secret_key_2024"

# 🔴 إعدادات ديسكورد
DISCORD_CLIENT_ID = "1457756445599858822"
DISCORD_CLIENT_SECRET = "K14al_OVQ7nRvIo6TQjJATxtI8Ky5cA3"
DISCORD_REDIRECT_URI = "https://flame-ten-18.vercel.app//auth/discord/callback" # غير الرابط لموقعك

DB_FILE = "database.db"

# 🔴 دالة الاتصال بقاعدة البيانات
def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

# 🔴 إنشاء الجداول أول ما يشتغل السيرفر
def init_db():
    with get_db() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS users 
                        (username TEXT PRIMARY KEY, password TEXT, discord_id TEXT, avatar TEXT)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS accounts 
                        (name TEXT PRIMARY KEY, username_key TEXT, cash INTEGER, bank INTEGER, 
                         level INTEGER, skills TEXT, last_seen REAL)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS stats (key TEXT PRIMARY KEY, value INTEGER)''')
        # التأكد من وجود حساب الأدمن
        admin_pass = hashlib.sha256("admin".encode()).hexdigest()
        conn.execute('INSERT OR IGNORE INTO users (username, password) VALUES (?, ?)', ("admin", admin_pass))
        # تصفير الزوار إذا ما كان موجود
        conn.execute('INSERT OR IGNORE INTO stats (key, value) VALUES (?, ?)', ("visits", 0))

init_db()

@app.before_request
def count_visits():
    if request.path in ['/', '/login', '/register']:
        if 'visited' not in session:
            session['visited'] = True
            with get_db() as conn:
                conn.execute('UPDATE stats SET value = value + 1 WHERE key = "visits"')

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        data = request.get_json(force=True, silent=True) or {}
        username = data.get("username", "").strip()
        password = data.get("password", "").strip()
        
        if len(username) <= 3: return jsonify({"error": "الاسم قصير"}), 400
        if len(password) < 4: return jsonify({"error": "الباسورد قصير"}), 400
        
        with get_db() as conn:
            if conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone():
                return jsonify({"error": "الاسم موجود"}), 400
            conn.execute('INSERT INTO users (username, password) VALUES (?, ?)', 
                         (username, hashlib.sha256(password.encode()).hexdigest()))
        
        session["user"] = username
        return jsonify({"ok": True})
    return render_template("auth.html", mode="register")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        data = request.get_json(force=True, silent=True) or {}
        username = data.get("username", "").strip()
        password = data.get("password", "").strip()
        
        with get_db() as conn:
            user = conn.execute('SELECT * FROM users WHERE username = ? AND password = ?', 
                                (username, hashlib.sha256(password.encode()).hexdigest())).fetchone()
            if user:
                session["user"] = username
                return jsonify({"ok": True})
        return jsonify({"error": "بيانات غلط"}), 401
    return render_template("auth.html", mode="login")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# 🔴 ديسكورد OAuth
@app.route("/auth/discord")
def auth_discord():
    url = f"https://discord.com/api/oauth2/authorize?client_id={DISCORD_CLIENT_ID}&redirect_uri={DISCORD_REDIRECT_URI}&response_type=code&scope=identify"
    return redirect(url)

@app.route("/auth/discord/callback")
def auth_discord_callback():
    code = request.args.get("code")
    if not code: return "Auth Failed", 400
    
    data = {"client_id": DISCORD_CLIENT_ID, "client_secret": DISCORD_CLIENT_SECRET,
            "grant_type": "authorization_code", "code": code, "redirect_uri": DISCORD_REDIRECT_URI}
    r = requests.post("https://discord.com/api/oauth2/token", data=data)
    if r.status_code != 200: return "Token Error", 400
        
    access_token = r.json().get("access_token")
    user_r = requests.get("https://discord.com/api/users/@me", headers={"Authorization": f"Bearer {access_token}"})
    u = user_r.json()
    
    d_username, d_id, d_avatar = u.get("username"), u.get("id"), u.get("avatar")
    avatar_url = f"https://cdn.discordapp.com/avatars/{d_id}/{d_avatar}.png" if d_avatar else "https://cdn.discordapp.com/embed/avatars/0.png"
    
    with get_db() as conn:
        conn.execute('INSERT OR IGNORE INTO users (username, password) VALUES (?, ?)', (d_username, "DISCORD_OAUTH"))
        conn.execute('UPDATE users SET discord_id = ?, avatar = ? WHERE username = ?', (d_id, avatar_url, d_username))
        
    session["user"] = d_username
    return redirect(url_for("index"))

@app.route("/")
def index():
    if "user" not in session: return redirect(url_for("login"))
    my_key = session["user"]
    is_admin = (my_key == "admin")
    now = time.time()
    display_accounts = []

    with get_db() as conn:
        if is_admin:
            rows = conn.execute('SELECT * FROM accounts').fetchall()
        else:
            rows = conn.execute('SELECT * FROM accounts WHERE username_key = ?', (my_key,)).fetchall()
            
        for a in rows:
            is_online = (now - a['last_seen']) < 60
            display_accounts.append({
                "name": a['name'], "online": is_online, "total_level": a['level'],
                "total_money": a['cash'] + a['bank'], "cash": a['cash'], "bank": a['bank'],
                "skills": json.loads(a['skills']), "pc": "MR 1"
            })
            
    return render_template("index.html", my_key=my_key, accounts=display_accounts)

# 🔴 لوحة الأدمن المتقدمة
@app.route("/admin")
def admin_panel():
    if session.get("user") != "admin":
        return "Access Denied", 403
    
    try:
        with get_db() as conn:
            visits = conn.execute('SELECT value FROM stats WHERE key = "visits"').fetchone()[0]
            total_accounts = conn.execute('SELECT COUNT(*) FROM accounts').fetchone()[0]
            
            normal_users = [dict(u) for u in conn.execute('SELECT username, password FROM users WHERE password != "DISCORD_OAUTH" AND username != "admin"').fetchall()]
            d_users = [dict(u) for u in conn.execute('SELECT username, discord_id, avatar FROM users WHERE discord_id IS NOT NULL').fetchall()]
            
        return render_template("admin.html", visits=visits, normal_users=normal_users, discord_users=d_users, total_accounts=total_accounts)
    except Exception as e:
        return f"<h1>Error</h1><pre>{traceback.format_exc()}</pre>", 500

@app.route("/api/delete", methods=["POST"])
def delete_account():
    data = request.get_json(force=True, silent=True) or {}
    name = data.get("name")
    with get_db() as conn:
        conn.execute('DELETE FROM accounts WHERE name = ?', (name,))
    return jsonify({"ok": True})

@app.route("/api/report", methods=["POST"])
def report():
    data = request.get_json(force=True, silent=True) or {}
    username_key = data.get("k")
    if not username_key: return jsonify({"error": "Unauthorized"}), 401
    
    name = data.get("n", "Unknown")
    now = time.time()
    cash, bank, level = int(data.get("c", 0) or 0), int(data.get("b", 0) or 0), int(data.get("l", 0) or 0)
    
    skills_dict = {sk["name"]: int(sk.get("level", 0)) for sk in data.get("s", []) if "name" in sk}
    skills_json = json.dumps(skills_dict)

    with get_db() as conn:
        conn.execute('''INSERT INTO accounts (name, username_key, cash, bank, level, skills, last_seen) 
                        VALUES (?, ?, ?, ?, ?, ?, ?) 
                        ON CONFLICT(name) DO UPDATE SET 
                        cash=excluded.cash, bank=excluded.bank, level=excluded.level, 
                        skills=excluded.skills, last_seen=excluded.last_seen''', 
                     (name, username_key, cash, bank, level, skills_json, now))
    return jsonify({"ok": True})

if __name__ == "__main__":
    app.run(port=5000)
