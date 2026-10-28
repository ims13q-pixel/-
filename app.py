from flask import Flask, request, jsonify, render_template, redirect, url_for, session
import time
import hashlib
import os

app = Flask(__name__)
app.secret_key = os.urandom(24) # مفتاح تشفير الجلسات

# قاعدة بيانات وهمية في الذاكرة
users = {}
accounts = {}

def hash_pass(password):
    return hashlib.sha256(password.encode()).hexdigest()

# --- مسارات الموقع ---

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        data = request.get_json(force=True, silent=True)
        if not data or not data.get("username") or not data.get("password"):
            return jsonify({"error": "معلومات ناقصة"}), 400
        
        username = data["username"]
        if username in users:
            return jsonify({"error": "اسم المستخدم موجود مسبقاً"}), 400
            
        users[username] = hash_pass(data["password"])
        return jsonify({"ok": True, "message": "تم التسجيل بنجاح"})
    return render_template("auth.html", mode="register")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        data = request.get_json(force=True, silent=True)
        if not data or not data.get("username") or not data.get("password"):
            return jsonify({"error": "معلومات ناقصة"}), 400
        
        username = data["username"]
        password_hash = hash_pass(data["password"])
        
        if users.get(username) == password_hash:
            session["user"] = username
            return jsonify({"ok": True})
        return jsonify({"error": "اسم المستخدم أو كلمة المرور غلط"}), 401
    return render_template("auth.html", mode="login")

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))

@app.route("/")
def index():
    # حماية الصفحة: إذا مو مسجل دخول، يوديه للتسجيل
    if "user" not in session:
        return redirect(url_for("login"))
    
    now = time.time()
    for name, a in accounts.items():
        a["uptime_display"] = round(a.get("uptime", 0), 2)
        a["online"] = (now - a.get("last_seen", 0)) < 120
    return render_template("index.html", accounts=accounts)

# --- API للسكربت حق اللعبة ---
@app.route("/api/report", methods=["POST"])
def report():
    data = request.get_json(force=True, silent=True)
    if not data or "name" not in data:
        return jsonify({"error": "missing data"}), 400
    
    name = data["name"]
    now = time.time()
    
    uptime = accounts.get(name, {}).get("uptime", 0)
    if name in accounts and (now - accounts[name]["last_seen"]) < 120:
        uptime += (now - accounts[name]["last_seen"]) / 3600
        
    accounts[name] = {
        "level": data.get("level", 0),
        "money": data.get("money", 0),
        "hourly": data.get("hourly", 0),
        "uptime": uptime,
        "last_seen": now,
    }
    return jsonify({"ok": True})

if __name__ == "__main__":
    app.run(port=5000, debug=True)
