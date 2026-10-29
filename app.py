from flask import Flask, request, jsonify, render_template, redirect, url_for, session
import time
import hashlib
import traceback

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
    
    try:
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
                h = uptime // 3600
                m = (uptime % 3600) // 60
                a["session"] = f"{h}h {m}m" if h > 0 else f"{m}m"
            else: 
                offline_count += 1
                a["session"] = "—"
                a["login_time"] = now
                
            a["online"] = is_online
            a["seen"] = "just now" if is_online else "offline"
            
            acc_copy = a.copy()
            acc_copy["name"] = name
            filtered_accounts.append(acc_copy)
            
        stats = {
            "total": len(filtered_accounts),
            "online": online_count,
            "offline": offline_count
        }
            
        return render_template("index.html", accounts=filtered_accounts, my_key=my_key, stats=stats)
    
    except Exception as e:
        # هذا السطر بيكشف لك أي خطأ مخفي في السيرفر
        return f"<h1>Server Error</h1><p>{str(e)}</p><pre>{traceback.format_exc()}</pre>", 500

@app.route("/api/delete", methods=["POST"])
def delete_account():
    data = request.get_json(force=True, silent=True) or {}
    name = data.get("name")
    
    if session.get("user") == "admin" or (name in accounts and accounts[name].get("key") == session.get("user")):
        if name in accounts:
            del accounts[name]
            return jsonify({"ok": True})
            
    return jsonify({"error": "Not found or unauthorized"}), 404

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

    rate = 0
    if name in accounts and (now - accounts[name].get("last_seen", now)) > 10:
        old_money = accounts[name].get("total_money", current_money)
        time_diff = now - accounts[name]["last_seen"]
        if time_diff > 0:
            rate = int(((current_money - old_money) / time_diff) * 3600)

    if name not in accounts:
        accounts[name] = {"login_time": now, "total_money": current_money}

    accounts[name].update({
        "key": username_key,
        "pc": data.get("pc", "MR 1"),
        "server": "Server 1",
        "server_count": "19/28",
        "cash": cash,
        "bank": bank,
        "total_money": current_money,
        "rate": rate,
        "total_level": level,
        "skills": skills_dict,
        "display_name": data.get("dn", name),
        "user_id": str(data.get("u", "")),
        "last_seen": now
    })
    
    return jsonify({"ok": True})

if __name__ == "__main__":
    app.run(port=5000)
