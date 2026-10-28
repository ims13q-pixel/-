from flask import Flask, request, jsonify, render_template, redirect, url_for, session
import time, hashlib

app = Flask(__name__)
app.secret_key = "axiom_blockspin_secret_123"

# تخزين في الذاكرة (Vercel يمسحها إذا طفى السيرفر)
users = {"admin": hashlib.sha256("admin".encode()).hexdigest()}
passwords = {"admin": "admin"} # نحفظ الباسورد العادي عشان الأدمن يشوفه
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
    
    total_accounts = 0
    online_count = 0
    offline_count = 0
    total_cash_all = 0
    total_bank_all = 0
    all_accounts = []

    for name, a in accounts.items():
        if not is_admin and a.get("key") != my_key:
            continue
            
        total_accounts += 1
        is_online = (now - a.get("last_seen", 0)) < 15 
        a["online"] = is_online
        
        if is_online: 
            online_count += 1
            if "login_time" not in a: a["login_time"] = now
            a["uptime"] = int(now - a["login_time"])
        else: 
            offline_count += 1
            a["uptime"] = 0
            a["login_time"] = now
            
        a["total_money"] = a.get("cash", 0) + a.get("bank", 0)
        if "hourly" not in a: a["hourly"] = 0
        
        total_cash_all += a.get("cash", 0)
        total_bank_all += a.get("bank", 0)
        
        acc_copy = a.copy()
        acc_copy["name"] = name
        all_accounts.append(acc_copy)
        
    stats = {
        "total": total_accounts,
        "online": online_count,
        "offline": offline_count,
        "total_cash": total_cash_all,
        "total_bank": total_bank_all
    }
        
    return render_template("index.html", accounts=all_accounts, my_key=my_key, stats=stats, is_admin=is_admin)

@app.route("/admin")
def admin_panel():
    if session.get("user") != "admin":
        return "Access Denied", 403
    
    game_accounts = []
    for name, a in accounts.items():
        acc = a.copy()
        acc["name"] = name
        game_accounts.append(acc)
        
    return render_template("admin.html", users=passwords, accounts=game_accounts)

@app.route("/api/delete", methods=["POST"])
def delete_account():
    data = request.get_json(force=True, silent=True) or {}
    name = data.get("name")
    if name in accounts:
        del accounts[name]
        return jsonify({"ok": True})
    return jsonify({"error": "Not found"}), 404

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
    skills = [{"name": sk.get("name"), "level": int(sk.get("level", 0))} for sk in raw_skills]
    
    hourly = 0
    if name in accounts and (now - accounts[name].get("last_seen", now)) > 10:
        old_money = accounts[name].get("total_money", current_money)
        time_diff = now - accounts[name]["last_seen"]
        hourly = ((current_money - old_money) / time_diff) * 3600

    if name not in accounts:
        accounts[name] = {"login_time": now, "total_money": current_money}

    accounts[name].update({
        "key": username_key,
        "pc": data.get("pc", "DESKTOP"),
        "cash": cash,
        "bank": bank,
        "total_money": current_money,
        "hourly": hourly,
        "total_level": level,
        "skills": skills,
        "last_seen": now
    })
    return jsonify({"ok": True})

if __name__ == "__main__":
    app.run(port=5000)
