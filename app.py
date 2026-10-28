from flask import Flask, request, jsonify, render_template, redirect, url_for, session
import time
import hashlib

app = Flask(__name__)
app.secret_key = "super_secret_blockspin_key_123"

users = {}
accounts = {}

def hash_pass(password):
    return hashlib.sha256(password.encode()).hexdigest()

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
        session["user"] = username # يسجل دخولك فوراً
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
    if "user" not in session:
        return redirect(url_for("login"))
    
    now = time.time()
    for name, a in accounts.items():
        a["online"] = (now - a.get("last_seen", 0)) < 120
        a["total_money"] = a.get("cash", 0) + a.get("bank", 0)
        
    return render_template("index.html", accounts=accounts)

@app.route("/api/report", methods=["POST"])
def report():
    data = request.get_json(force=True, silent=True)
    if not data or "name" not in data:
        return jsonify({"error": "missing data"}), 400
    
    name = data["name"]
    
    # نحدث البيانات ونحتفظ بالمهارات
    accounts[name] = {
        "cash": data.get("cash", 0),
        "bank": data.get("bank", 0),
        "total_level": data.get("total_level", 0),
        "skills": data.get("skills", []),
        "last_seen": time.time(),
    }
    return jsonify({"ok": True})

if __name__ == "__main__":
    app.run(port=5000, debug=True)
