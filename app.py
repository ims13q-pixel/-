from flask import Flask, request, jsonify, render_template, redirect, url_for, session
import time, hashlib, requests, json, os
from upstash_redis import Redis

app = Flask(__name__)
app.secret_key = "axiom_secret_key_2024"

DISCORD_CLIENT_ID = "1457756445599858822"
DISCORD_CLIENT_SECRET = os.environ.get("DISCORD_CLIENT_SECRET", "K14al_OVQ7nRvIo6TQjJATxtI8Ky5cA3")
DISCORD_REDIRECT_URI = "https://flame-ten-18.vercel.app/auth/discord/callback"

REDIS_URL = os.environ.get("KV_REST_API_URL") or os.environ.get("UPSTASH_REDIS_REST_URL")
REDIS_TOKEN = os.environ.get("KV_REST_API_TOKEN") or os.environ.get("UPSTASH_REDIS_REST_TOKEN")
redis = Redis(url=REDIS_URL, token=REDIS_TOKEN) if REDIS_URL and REDIS_TOKEN else None

def load_db():
    if redis:
        u = redis.get("users"); p = redis.get("passwords"); d = redis.get("discord_profiles"); a = redis.get("accounts")
        # 🔴 إضافة حماية للبيانات التالفة
        try: u_data = json.loads(u) if u else {"admin": hashlib.sha256("admin".encode()).hexdigest()}
        except: u_data = {"admin": hashlib.sha256("admin".encode()).hexdigest()}
        
        try: p_data = json.loads(p) if p else {"admin": "admin"}
        except: p_data = {"admin": "admin"}
        
        try: d_data = json.loads(d) if d else {}
        except: d_data = {}
        
        try: a_data = json.loads(a) if a else {}
        except: a_data = {}

        return (u_data, p_data, d_data, a_data)
    return ({"admin": hashlib.sha256("admin".encode()).hexdigest()}, {"admin": "admin"}, {}, {})

def save_db(u, p, d, a):
    if redis:
        redis.set("users", json.dumps(u)); redis.set("passwords", json.dumps(p))
        redis.set("discord_profiles", json.dumps(d)); redis.set("accounts", json.dumps(a))

@app.before_request
def count_visits():
    if request.path in ['/', '/login', '/register']:
        if 'visited' not in session:
            session['visited'] = True
            if redis: redis.incr("visits")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        try:
            data = request.get_json(force=True, silent=True) or {}
            username = data.get("username", "").strip()
            password = data.get("password", "").strip()
            users, passwords, _, _ = load_db()
            if len(username) <= 3: return jsonify({"error": "Username too short"}), 400
            if len(password) < 4: return jsonify({"error": "Password too short"}), 400
            if username in users: return jsonify({"error": "Username already exists"}), 400
            users[username] = hashlib.sha256(password.encode()).hexdigest()
            passwords[username] = password
            save_db(users, passwords, {}, {})
            session["user"] = username
            return jsonify({"ok": True})
        except Exception as e:
            return jsonify({"error": f"Server Error: {str(e)}"}), 500
    return render_template("auth.html", mode="register")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        try:
            data = request.get_json(force=True, silent=True) or {}
            username = data.get("username", "").strip()
            password = data.get("password", "").strip()
            users, _, _, _ = load_db()
            if users.get(username) == hashlib.sha256(password.encode()).hexdigest():
                session["user"] = username
                return jsonify({"ok": True})
            return jsonify({"error": "Invalid credentials"}), 401
        except Exception as e:
            return jsonify({"error": f"Server Error: {str(e)}"}), 500
    return render_template("auth.html", mode="login")

# ... (باقي مسارات الموقع مثل index و api_data وغيرها كما هي من الكود السابق) ...
# انسخهم من الرسالة السابقة وضعهم هنا
