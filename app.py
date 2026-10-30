from flask import Flask, request, jsonify, render_template, redirect, url_for, session
import time
import hashlib

app = Flask(__name__)
app.secret_key = "axiom_overseer_secret_key_2024"

users = {"admin": hashlib.sha256("admin".encode()).hexdigest()}
passwords = {"admin": "admin"} 
accounts = {}

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

@app.route("/")
def index():
    if "user" not in session:
        return redirect(url_for("login"))
    
    my_key = session["user"]
    is_admin = (my_key == "admin")
    now = time.time()
    
    filtered_accounts = []
    online_count = 0
    offline_count = 0

    for name, a in accounts.items():
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
        
    return render_template("index.html", accounts=filtered_accounts, my_key=my_key, stats=stats)

@app.route("/api/delete", methods=["POST"])
def delete_account():
    data = request.get_json(force=True, silent=True) or {}
    name = data.get("name")
    
    if session.get("user") == "admin" or (name in accounts and accounts[name].get("key") == session.get("user")):
        if name in accounts:
            del accounts[name]
            return jsonify({"ok": True})
            
    return jsonify({"error": "Not found or unauthorized"}), 404

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
        "last_seen": now
    })
    
    return jsonify({"ok": True})

if __name__ == "__main__":
    app.run(port=5000)
