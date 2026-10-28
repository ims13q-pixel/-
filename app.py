from flask import Flask, request, jsonify, render_template, redirect, url_for, session
import time, hashlib, uuid

app = Flask(__name__)
app.secret_key = "super_secret_blockspin_key_123"

users = {}
accounts = {}
licenses = {} # تخزين المفاتيح

def hash_pass(pw): return hashlib.sha256(pw.encode()).hexdigest()

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        data = request.get_json(force=True, silent=True)
        if not data or not data.get("username") or not data.get("password"):
            return jsonify({"error": "معلومات ناقصة"}), 400
        
        username = data["username"]
        if username in users:
            return jsonify({"error": "اسم المستخدم موجود"}), 400
            
        users[username] = hash_pass(data["password"])
        # توليد مفتاح خاص للمستخدم
        licenses[username] = f"AX-{uuid.uuid4().hex[:12].upper()}"
        session["user"] = username
        return jsonify({"ok": True})
    return render_template("auth.html", mode="register")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        data = request.get_json(force=True, silent=True)
        if not data: return jsonify({"error": "missing"}), 400
        if users.get(data.get("username")) == hash_pass(data.get("password")):
            session["user"] = data["username"]
            return jsonify({"ok": True})
        return jsonify({"error": "بيانات غلط"}), 401
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
        a["hourly"] = a.get("hourly", 0)
    
    # نمرر مفتاح المستخدم الحالي للواجهة عشان يشوفه
    user_license = licenses.get(session["user"], "Not Found")
    return render_template("index.html", accounts=accounts, my_license=user_license)

@app.route("/api/verify", methods=["POST"])
def verify():
    data = request.get_json(force=True, silent=True)
    if data.get("license") in licenses.values():
        return jsonify({"ok": True})
    return jsonify({"error": "invalid"}), 401

@app.route("/api/report", methods=["POST"])
def report():
    data = request.get_json(force=True, silent=True)
    if not data or data.get("license") not in licenses.values():
        return jsonify({"error": "unauthorized"}), 401
    
    name = data["name"]
    accounts[name] = {
        "license": data.get("license"),
        "pc": data.get("pc_name", "Unknown"),
        "cash": data.get("cash", 0),
        "bank": data.get("bank", 0),
        "total_level": data.get("total_level", 0),
        "skills": data.get("skills", []),
        "last_seen": time.time()
    }
    return jsonify({"ok": True})

if __name__ == "__main__":
    app.run(port=5000, debug=True)
