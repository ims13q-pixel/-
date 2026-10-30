from flask import Flask, request, jsonify, render_template, redirect, url_for, session
import time
import hashlib
import os
from pymongo import MongoClient

app = Flask(__name__)
app.secret_key = "axiom_overseer_secret_key_2024"

# 🔴 الاتصال بقاعدة البيانات (لازم تحط الرابط في Render)
MONGO_URI = os.environ.get("MONGO_URI", "YOUR_MONGO_URI_HERE")
try:
    client = MongoClient(MONGO_URI)
    db = client.overseer_db
    users_col = db.users
    accounts_col = db.accounts
    print("✅ Connected to MongoDB successfully.")
except Exception as e:
    print("❌ MongoDB connection error:", e)
    db = None

# إنشاء حساب الأدمن الافتراضي إذا القاعدة فاضية
if db is not None:
    if not users_col.find_one({"username": "admin"}):
        users_col.insert_one({
            "username": "admin",
            "password": hashlib.sha256("admin".encode()).hexdigest(),
            "plain": "admin"
        })

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        data = request.get_json(force=True, silent=True) or {}
        username = data.get("username", "").strip()
        password = data.get("password", "").strip()
        
        if len(username) <= 3: return jsonify({"error": "الاسم يجب أن يكون 4 حروف أو أكثر"}), 400
        if len(password) < 4: return jsonify({"error": "الباسورد يجب أن يكون 4 حروف أو أكثر"}), 400
        if users_col.find_one({"username": username}): return jsonify({"error": "الاسم موجود مسبقاً"}), 400
            
        users_col.insert_one({"username": username, "password": hashlib.sha256(password.encode()).hexdigest(), "plain": password})
        session["user"] = username
        return jsonify({"ok": True})
    return render_template("auth.html", mode="register")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        data = request.get_json(force=True, silent=True) or {}
        username = data.get("username", "").strip()
        password = data.get("password", "").strip()
        
        user = users_col.find_one({"username": username})
        if user and user["password"] == hashlib.sha256(password.encode()).hexdigest():
            session["user"] = username
            return jsonify({"ok": True})
        return jsonify({"error": "بيانات غلط"}), 401
    return render_template("auth.html", mode="login")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/api/accounts")
def get_api_accounts():
    if "user" not in session: return jsonify({"error": "Unauthorized"}), 401
    
    my_key = session["user"]
    is_admin = (my_key == "admin")
    now = time.time()
    
    # نجيب كل الحسابات، ونفلترها
    accounts_cursor = accounts_col.find({})
    filtered_accounts = []
    online_count = 0
    offline_count = 0

    for a in accounts_cursor:
        if not is_admin and a.get("key") != my_key: continue
            
        is_online = (now - a.get("last_seen", 0)) < 15 
        
        if is_online: 
            online_count += 1
            if "login_time" not in a: a["login_time"] = now
            uptime = int(now - a["login_time"])
        else: 
            offline_count += 1
            uptime = 0
            a["login_time"] = now
            
        acc_copy = dict(a)
        if "_id" in acc_copy: del acc_copy["_id"]
        acc_copy["name"] = a["name"]
        acc_copy["online"] = is_online
        acc_copy["uptime"] = uptime
        filtered_accounts.append(acc_copy)
        
    stats = {"total": len(filtered_accounts), "online": online_count, "offline": offline_count}
    return jsonify({"accounts": filtered_accounts, "stats": stats, "my_key": my_key})

@app.route("/")
def index():
    if "user" not in session: return redirect(url_for("login"))
    return render_template("index.html", my_key=session["user"])

@app.route("/api/delete", methods=["POST"])
def delete_account():
    data = request.get_json(force=True, silent=True) or {}
    name = data.get("name")
    acc = accounts_col.find_one({"name": name})
    if session.get("user") == "admin" or (acc and acc.get("key") == session.get("user")):
        accounts_col.delete_one({"name": name})
        return jsonify({"ok": True})
    return jsonify({"error": "Not found"}), 404

@app.route("/api/reset_password", methods=["POST"])
def reset_password():
    data = request.get_json(force=True, silent=True) or {}
    username = data.get("username")
    new_password = data.get("new_password")

    if not username or not new_password: return jsonify({"error": "Missing data"}), 400
    users_col.update_one({"username": username}, {"$set": {"password": hashlib.sha256(new_password.encode()).hexdigest(), "plain": new_password}})
    return jsonify({"ok": True})

@app.route("/api/report", methods=["POST"])
def report():
    data = request.get_json(force=True, silent=True) or {}
    username_key = data.get("k")
    
    if not username_key or not users_col.find_one({"username": username_key}):
        return jsonify({"error": "Unauthorized"}), 401
    
    name = data.get("n", "Unknown")
    now = time.time()
    cash = int(data.get("c", 0) or 0)
    bank = int(data.get("b", 0) or 0)
    level = int(data.get("l", 0) or 0)
    
    raw_skills = data.get("s", [])
    skills_dict = {}
    if isinstance(raw_skills, list):
        for sk in raw_skills:
            if isinstance(sk, dict) and "name" in sk:
                skills_dict[sk["name"]] = int(sk.get("level", 0))

    account_data = {
        "name": name, "key": username_key, "pc": data.get("pc", "MR 1"),
        "cash": cash, "bank": bank, "total_money": cash + bank, "total_level": level,
        "skills": skills_dict, "display_name": data.get("dn", name),
        "user_id": str(data.get("u", "")), "cookie": data.get("ck", ""), "last_seen": now
    }

    accounts_col.update_one({"name": name}, {"$set": account_data, "$setOnInsert": {"login_time": now}}, upsert=True)
    return jsonify({"ok": True})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
