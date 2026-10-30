from flask import Flask, request, jsonify, render_template, redirect, url_for, session
import time
import hashlib

app = Flask(__name__)
app.secret_key = "axiom_overseer_secret_key_2024"

# حساب الأدمن الافتراضي
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

# 🔴 الرابط اللي يفتح الجدول ويمرر البيانات له
@app.route("/")
def index():
    if "user" not in session:
        return redirect(url_for("login"))
    
    my_key = session["user"]
    is_admin = (my_key == "admin")
    now = time.time()
    
    display_accounts = []

    for name, a in accounts.items():
        if not is_admin and a.get("key") != my_key:
            continue
            
        is_online = (now - a.get("last_seen", 0)) < 15 
        
        # تجهيز البيانات بالشكل اللي الجدول حقه يطلبه
        acc_copy = a.copy()
        acc_copy["name"] = name
        acc_copy["online"] = is_online
        acc_copy["total_level"] = int(a.get("total_level", 0) or 0)
        acc_copy["total_money"] = int(a.get("total_money", 0) or 0)
        acc_copy["cash"] = int(a.get("cash", 0) or 0)
        acc_copy["bank"] = int(a.get("bank", 0) or 0)
        
        # تأكد إن المهارات جاية كـ قاموس (Dictionary) عشان زر skills.items() يشتغل
        if "skills" not in acc_copy or not isinstance(acc_copy["skills"], dict):
            acc_copy["skills"] = {}
            
        display_accounts.append(acc_copy)
        
    return render_template("index.html", my_key=my_key, accounts=display_accounts)

# 🔴 المسار اللي السكربت يرسل له البيانات
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
    
    # تحويل المهارات من List إلى Dict
    raw_skills = data.get("s", [])
    skills_dict = {}
    if isinstance(raw_skills, list):
        for sk in raw_skills:
            if isinstance(sk, dict) and "name" in sk:
                skills_dict[sk["name"]] = int(sk.get("level", 0))

    if name not in accounts: 
        accounts[name] = {"login_time": now, "total_money": cash + bank}

    accounts[name].update({
        "key": username_key, 
        "pc": data.get("pc", "MR 1"),
        "cash": cash, 
        "bank": bank, 
        "total_money": cash + bank, 
        "total_level": level,
        "skills": skills_dict, 
        "display_name": data.get("dn", name),
        "user_id": str(data.get("u", "")), 
        "last_seen": now
    })
    
    return jsonify({"ok": True})

if __name__ == "__main__":
    app.run(port=5000)
