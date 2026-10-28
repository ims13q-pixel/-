from flask import Flask, request, jsonify, render_template, redirect, url_for, session
import time, hashlib

app = Flask(__name__)
app.secret_key = "axiom_blockspin_secret_123"

# قاعدة بيانات وهمية في الذاكرة
users = {}      # يخزن (اسم المستخدم : الباسورد المشفر)
accounts = {}   # يخزن بيانات اللعبة

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        data = request.get_json(force=True, silent=True) or {}
        username = data.get("username")
        password = data.get("password")
        
        if not username or not password:
            return jsonify({"error": "أدخل اسم وكلمة مرور"}), 400
        if username in users:
            return jsonify({"error": "الاسم موجود مسبقاً"}), 400
            
        users[username] = hashlib.sha256(password.encode()).hexdigest()
        session["user"] = username
        return jsonify({"ok": True})
    return render_template("auth.html", mode="register")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        data = request.get_json(force=True, silent=True) or {}
        username = data.get("username")
        password = data.get("password")
        
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
    
    # المفتاح هو اسم المستخدم
    my_key = session["user"]
    
    now = time.time()
    for name, a in accounts.items():
        a["online"] = (now - a.get("last_seen", 0)) < 120
        a["total_money"] = a.get("cash", 0) + a.get("bank", 0)
        if "hourly" not in a: a["hourly"] = 0
        
    return render_template("index.html", accounts=accounts, my_key=my_key)

# --- مسار حذف الحساب ---
@app.route("/api/delete", methods=["POST"])
def delete_account():
    data = request.get_json(force=True, silent=True) or {}
    name = data.get("name")
    if name in accounts:
        del accounts[name]
        return jsonify({"ok": True})
    return jsonify({"error": "Not found"}), 404

# --- استقبال البيانات من السكربت ---
@app.route("/api/report", methods=["POST"])
def report():
    data = request.get_json(force=True, silent=True) or {}
    
    # السكربت يرسل اسم المستخدم كـ "key"
    username_key = data.get("key")
    if not username_key:
        return jsonify({"error": "No key provided"}), 401

    # التحقق: هل المفتاح (اسم المستخدم) موجود في قائمة المسجلين؟
    if username_key not in users:
        return jsonify({"error": "Unauthorized"}), 401
    
    name = data.get("name", "Unknown")
    now = time.time()
    current_money = data.get("cash", 0) + data.get("bank", 0)
    hourly = 0
    
    # حساب الأرباح في الساعة
    if name in accounts and (now - accounts[name].get("last_seen", now)) > 10:
        old_money = accounts[name].get("total_money", current_money)
        time_diff = now - accounts[name]["last_seen"]
        hourly = ((current_money - old_money) / time_diff) * 3600

    accounts[name] = {
        "pc": data.get("pc_name", "DESKTOP"),
        "cash": data.get("cash", 0),
        "bank": data.get("bank", 0),
        "total_money": current_money,
        "hourly": hourly,
        "total_level": data.get("total_level", 0),
        "skills": data.get("skills", []),
        "last_seen": now
    }
    return jsonify({"ok": True})

if __name__ == "__main__":
    app.run(port=5000)
