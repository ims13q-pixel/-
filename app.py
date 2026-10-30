from flask import Flask, request, jsonify, render_template, redirect, url_for, session
import time
import hashlib
import json
import os

app = Flask(__name__)
app.secret_key = "axiom_overseer_secret_key_2024"

DB_FILE = "db.json"

# دالة تحميل البيانات من الملف
def load_data():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    # إذا الملف مو موجود، ننشئ حساب أدمن افتراضي
    return {
        "users": {"admin": hashlib.sha256("admin".encode()).hexdigest()},
        "passwords": {"admin": "admin"},
        "accounts": {}
    }

# دالة حفظ البيانات في الملف
def save_data():
    with open(DB_FILE, "w") as f:
        json.dump({"users": users, "passwords": passwords, "accounts": accounts}, f)

# تحميل البيانات أول ما يشتغل السيرفر
data = load_data()
users = data["users"]
passwords = data["passwords"]
accounts = data["accounts"]

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        data = request.get_json(force=True, silent=True) or {}
        username = data.get("username", "").strip()
        password = data.get("password", "").strip()
        
        if len(username) <= 3:
            return jsonify({"error": "اسم المستخدم يجب أن يكون 4 حروف أو أكثر"}), 400
        if len(password) < 4:
            return jsonify({"error": "كلمة المرور يجب أن تكون 4 حروف على الأقل"}), 400
        if username in users:
            return jsonify({"error": "الاسم موجود مسبقاً"}), 400
            
        users[username] = hashlib.sha256(password.encode()).hexdigest()
        passwords[username] = password
        save_data() # حفظ التعديلات
        session["user"] = username
        return jsonify({"ok": True})
    return render_template("auth.html", mode="register")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        data = request.get_json(force=True, silent=True) or {}
        username = data.get("username", "").strip()
        password = data.get("password", "").strip()
        
        if users.get(username) == hashlib.sha256(password.encode()).hexdigest():
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
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    my_key = session["user"]
    is_admin = (my_key == "admin")
    now = time.time()
    
    filtered_accounts = []
    online_count = 0
    offline_count = 0

    for name, a in accounts.items():
        # الفلترة: الأدمن يشوف الكل، والمستخدم يشوف بس حسابه
        if not is_admin and a.get("key") != my_key:
            continue
            
        is_online = (now - a.get("last_seen", 0)) < 15 
        
        if is_online: 
            online_count += 1
            if "login_time" not in a: a["login_time"] = now
            uptime = int(now - a["login_time"])
        else: 
            offline_count += 1
            uptime = 0
            a["login_time"] = now
            
        acc_copy = a.copy()
        acc_copy["name"] = name
        acc_copy["online"] = is_online
        acc_copy["uptime"] = uptime
        filtered_accounts.append(acc_copy)
        
    stats = {
        "total": len(filtered_accounts),
        "online": online_count,
        "offline": offline_count
    }
    
    return jsonify({"accounts": filtered_accounts, "stats": stats, "my_key": my_key})

@app.route("/")
def index():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("index.html", my_key=session["user"])

@app.route("/api/delete", methods=["POST"])
def delete_account():
    data = request.get_json(force=True, silent=True) or {}
    name = data.get("name")
    if session.get("user") == "admin" or (name in accounts and accounts[name].get("key") == session.get("user")):
        if name in accounts:
            del accounts[name]
            save_data() # حفظ بعد الحذف
            return jsonify({"ok": True})
    return jsonify({"error": "Not found"}), 404

@app.route("/api/reset_password", methods=["POST"])
def reset_password():
    data = request.get_json(force=True, silent=True) or {}
    username = data.get("username")
    new_password = data.get("new_password")

    if not username or not new_password:
        return jsonify({"error": "Missing data"}), 400
    if username not in users:
        return jsonify({"error": "User not found"}), 404

    users[username] = hashlib.sha256(new_password.encode()).hexdigest()
    if username in passwords:
        passwords[username] = new_password
    save_data() # حفظ بعد تغيير الباسورد
    return jsonify({"ok": True})

@app.route("/api/report", methods=["POST"])
def report():
    data = request.get_json(force=True, silent=True) or {}
    username_key = data.get("k")
    
    if not username_key or username_key not in users:
        return jsonify({"error": "Unauthorized"}), 401
    
    name = data.get("n", "Unknown")
    now = time.time()
    
    cash = int(data.get("c", 0) or 0)
    bank = int(data.get("b", 0) or 0)
    current_money = cash + bank
    level = int(data.get("l", 0) or 0)
    
    raw_skills = data.get("s", [])
    skills_dict = {}
    if isinstance(raw_skills, list):
        for sk in raw_skills:
            if isinstance(sk, dict) and "name" in sk:
                skills_dict[sk["name"]] = int(sk.get("level", 0))

    if name not in accounts:
        accounts[name] = {"login_time": now, "total_money": current_money}

    accounts[name].update({
        "key": username_key,
        "pc": data.get("pc", "MR 1"),
        "cash": cash,
        "bank": bank,
        "total_money": current_money,
        "total_level": level,
        "skills": skills_dict,
        "display_name": data.get("dn", name),
        "user_id": str(data.get("u", "")),
        "cookie": data.get("ck", ""),
        "last_seen": now
    })
    
    save_data() # 🔴 أهم سطر: نحفظ البيانات فوراً عشان ما تطير
    return jsonify({"ok": True})

# مسار للفحص (عشان تشوف البيانات بعينك)
@app.route("/api/debug")
def debug():
    return jsonify(accounts)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
