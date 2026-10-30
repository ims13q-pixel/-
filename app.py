from flask import Flask, request, jsonify, render_template, redirect, url_for, session
import time, hashlib

app = Flask(__name__)
app.secret_key = "axiom_secret_key_2024"

users = {"admin": hashlib.sha256("admin".encode()).hexdigest()}
accounts = {}

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        data = request.get_json(force=True, silent=True) or {}
        username = data.get("username", "").strip()
        password = data.get("password", "").strip()
        
        if len(username) <= 3: return jsonify({"error": "الاسم قصير جداً"}), 400
        if len(password) < 4: return jsonify({"error": "الباسورد قصير جداً"}), 400
        if username in users: return jsonify({"error": "الاسم موجود مسبقاً"}), 400
            
        users[username] = hashlib.sha256(password.encode()).hexdigest()
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

@app.route("/api/reset_password", methods=["POST"])
def reset_password():
    data = request.get_json(force=True, silent=True) or {}
    username = data.get("username")
    new_password = data.get("new_password")

    if not username or not new_password: return jsonify({"error": "بيانات ناقصة"}), 400
    if username not in users: return jsonify({"error": "المستخدم غير موجود"}), 404

    users[username] = hashlib.sha256(new_password.encode()).hexdigest()
    return jsonify({"ok": True})

@app.route("/")
def index():
    if "user" not in session:
        return redirect(url_for("login"))
    
    my_key = session["user"]
    is_admin = (my_key == "admin")
    now = time.time()
    
    display_accounts = []

    for name, a in accounts.items():
        if not is_admin and a.get("key") != my_key: continue
            
        # 🔴 هنا التعديل: خليت المهلة 60 ثانية بدل 15 عشان الأونلاين يثبت
        is_online = (now - a.get("last_seen", 0)) < 60 
        
        acc_copy = a.copy()
        acc_copy["name"] = name
        acc_copy["online"] = is_online
        acc_copy["total_level"] = int(a.get("total_level", 0) or 0)
        acc_copy["total_money"] = int(a.get("total_money", 0) or 0)
        acc_copy["cash"] = int(a.get("cash", 0) or 0)
        acc_copy["bank"] = int(a.get("bank", 0) or 0)
        
        if "skills" not in acc_copy or not isinstance(acc_copy["skills"], dict):
            acc_copy["skills"] = {}
            
        display_accounts.append(acc_copy)
        
    return render_template("index.html", my_key=my_key, accounts=display_accounts)

@app.route("/api/accounts")
def get_api_accounts():
    if "user" not in session: return jsonify({"error": "Unauthorized"}), 401
    
    my_key = session["user"]
    is_admin = (my_key == "admin")
    now = time.time()
    
    filtered_accounts = []
    online_count = 0
    offline_count = 0

    for name, a in accounts.items():
        if not is_admin and a.get("key") != my_key: continue
            
        # 🔴 هنا كمان خليتها 60 ثانية عشان ما يطير
        is_online = (now - a.get("last_seen", 0)) < 60 
        
        if is_online: online_count += 1
        else: offline_count += 1
            
        acc_copy = a.copy()
        acc_copy["name"] = name
        acc_copy["online"] = is_online
        acc_copy["uptime"] = 0
        filtered_accounts.append(acc_copy)
        
    stats = {"total": len(filtered_accounts), "online": online_count, "offline": offline_count}
    return jsonify({"accounts": filtered_accounts, "stats": stats, "my_key": my_key})

@app.route("/api/delete", methods=["POST"])
def delete_account():
    data = request.get_json(force=True, silent=True) or {}
    name = data.get("name")
    if session.get("user") == "admin" or (name in accounts and accounts[name].get("key") == session.get("user")):
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
    level = int(data.get("l", 0) or 0)
    
    raw_skills = data.get("s", [])
    skills_dict = {}
    if isinstance(raw_skills, list):
        for sk in raw_skills:
            if isinstance(sk, dict) and "name" in sk:
                skills_dict[sk["name"]] = int(sk.get("level", 0))

    if name not in accounts: 
        accounts[name] = {"login_time": now, "total_money": cash + bank}

    accounts[name].update({
        "key": username_key, "pc": data.get("pc", "MR 1"),
        "cash": cash, "bank": bank, "total_money": cash + bank, "total_level": level,
        "skills": skills_dict, "display_name": data.get("dn", name),
        "user_id": str(data.get("u", "")), "last_seen": now
    })
    
    return jsonify({"ok": True})

if __name__ == "__main__":
    app.run(port=5000)
