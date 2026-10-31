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
        return (
            json.loads(u) if u else {"admin": hashlib.sha256("admin".encode()).hexdigest()},
            json.loads(p) if p else {"admin": "admin"},
            json.loads(d) if d else {},
            json.loads(a) if a else {}
        )
    else:
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
    return render_template("auth.html", mode="register")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        data = request.get_json(force=True, silent=True) or {}
        username = data.get("username", "").strip()
        password = data.get("password", "").strip()
        users, _, _, _ = load_db()
        if users.get(username) == hashlib.sha256(password.encode()).hexdigest():
            session["user"] = username
            return jsonify({"ok": True})
        return jsonify({"error": "Invalid credentials"}), 401
    return render_template("auth.html", mode="login")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/")
def index():
    if "user" not in session: return redirect(url_for("login"))
    return render_template("index.html", my_key=session["user"])

@app.route("/api/data")
def api_data():
    if "user" not in session: return jsonify({"error": "Unauthorized"}), 401
    my_key = session["user"]
    is_admin = (my_key == "admin")
    now = time.time()
    _, _, _, accounts = load_db()
    
    online_count = 0; total_cash = 0; total_bank = 0; total_farmed = 0; accs_list = []
    
    for name, a in accounts.items():
        if not is_admin and a.get("key") != my_key: continue
        
        is_online = (now - a.get("last_seen", 0)) < 60 
        if is_online: online_count += 1
        
        cash = int(a.get("cash", 0) or 0); bank = int(a.get("bank", 0) or 0); total = cash + bank
        start_time = a.get("session_start_time", now); start_money = a.get("session_start_money", total)
        uptime_sec = int(now - start_time); farmed = total - start_money
        
        total_cash += cash; total_bank += bank; total_farmed += farmed
        
        if uptime_sec < 60: uptime_str = "< 1m"
        else:
            hours = uptime_sec // 3600; minutes = (uptime_sec % 3600) // 60
            uptime_str = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
            
        accs_list.append({
            "name": name, "online": is_online, "level": int(a.get("total_level", 0) or 0),
            "cash": cash, "bank": bank, "total": total, "farmed": farmed,
            "uptime": uptime_str, "pc": a.get("pc", "PC"), "skills": a.get("skills", {})
        })
        
    return jsonify({
        "online_count": online_count, "total_accounts": len(accs_list),
        "total_cash": total_cash, "total_bank": total_bank,
        "total_worth": total_cash + total_bank, "total_farmed": total_farmed, "accounts": accs_list
    })

@app.route("/api/delete", methods=["POST"])
def delete_account():
    data = request.get_json(force=True, silent=True) or {}
    name = data.get("name")
    users, passwords, discord_profiles, accounts = load_db()
    if session.get("user") == "admin" or (name in accounts and accounts[name].get("key") == session.get("user")):
        if name in accounts:
            del accounts[name]
            save_db(users, passwords, discord_profiles, accounts)
            return jsonify({"ok": True})
    return jsonify({"error": "Not found"}), 404

@app.route("/api/report", methods=["POST"])
def report():
    data = request.get_json(force=True, silent=True) or {}
    username_key = data.get("k")
    users, passwords, discord_profiles, accounts = load_db()
    
    if not username_key or username_key not in users: return jsonify({"error": "Unauthorized"}), 401
    
    name = data.get("n", "Unknown"); now = time.time()
    cash = int(data.get("c", 0) or 0); bank = int(data.get("b", 0) or 0); total_money = cash + bank
    level = int(data.get("l", 0) or 0)
    
    raw_skills = data.get("s", [])
    skills_dict = {}
    if isinstance(raw_skills, list):
        for sk in raw_skills:
            if isinstance(sk, dict) and "name" in sk: skills_dict[sk["name"]] = int(sk.get("level", 0))

    if name not in accounts or (now - accounts[name].get("last_seen", 0)) > 120:
        if name not in accounts: accounts[name] = {}
        accounts[name]["session_start_time"] = now
        accounts[name]["session_start_money"] = total_money

    accounts[name].update({
        "key": username_key, "pc": data.get("pc", "DDC 1"),
        "cash": cash, "bank": bank, "total_money": total_money, "total_level": level,
        "skills": skills_dict, "display_name": data.get("dn", name),
        "user_id": str(data.get("u", "")), "last_seen": now
    })
    
    save_db(users, passwords, discord_profiles, accounts)
    return jsonify({"ok": True})

if __name__ == "__main__":
    app.run(port=5000)
