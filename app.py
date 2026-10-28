from flask import Flask, request, jsonify, render_template, redirect, url_for, session
import time, hashlib, json, os

app = Flask(__name__)
app.secret_key = "axiom_blockspin_secret_123"

# غيرنا اسم ملف الحفظ عشان نتجنب مشكلة "الاسم موجود مسبقاً"
DB_FILE = "users_database.json"
accounts = {}

# تحميل وحفظ المستخدمين في ملف
def load_users():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    # إنشاء حساب الأدمن الافتراضي إذا الملف مو موجود
    admin_pass = hashlib.sha256("admin".encode()).hexdigest()
    return {"admin": admin_pass}

def save_users(users_data):
    with open(DB_FILE, "w") as f:
        json.dump(users_data, f)

users = load_users()

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        data = request.get_json(force=True, silent=True) or {}
        username = data.get("username", "").strip()
        password = data.get("password", "").strip()
        
        # شرط: الاسم أكثر من 3 حروف
        if len(username) <= 3:
            return jsonify({"error": "اسم المستخدم يجب أن يكون أكثر من 3 حروف"}), 400
        if len(password) < 4:
            return jsonify({"error": "كلمة المرور يجب أن تكون 4 حروف على الأقل"}), 400
        if username in users:
            return jsonify({"error": "الاسم موجود مسبقاً"}), 400
            
        users[username] = hashlib.sha256(password.encode()).hexdigest()
        save_users(users)
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

    for name, a in accounts.items():
        # إذا مو أدمن، يشوف بس الحسابات اللي مفتاحها يطابق اسمه
        if not is_admin and a.get("key") != my_key:
            continue
            
        total_accounts += 1
        is_online = (now - a.get("last_seen", 0)) < 120
        a["online"] = is_online
        
        if is_online: online_count += 1
        else: offline_count += 1
            
        a["total_money"] = a.get("cash", 0) + a.get("bank", 0)
        if "hourly" not in a: a["hourly"] = 0
        
        total_cash_all += a.get("cash", 0)
        total_bank_all += a.get("bank", 0)
        
    stats = {
        "total": total_accounts,
        "online": online_count,
        "offline": offline_count,
        "total_cash": total_cash_all,
        "total_bank": total_bank_all
    }
        
    return render_template("index.html", accounts=accounts, my_key=my_key, stats=stats, is_admin=is_admin)

# مسار خاص بالأدمن عشان يشوف المسجلين
@app.route("/admin")
def admin_panel():
    if session.get("user") != "admin":
        return "Access Denied", 403
    
    registered_users = list(users.keys())
    return render_template("admin.html", users=registered_users)

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
    
    username_key = data.get("key")
    if not username_key or username_key not in users:
        return jsonify({"error": "Unauthorized"}), 401
    
    name = data.get("name", "Unknown")
    now = time.time()
    current_money = data.get("cash", 0) + data.get("bank", 0)
    hourly = 0
    
    if name in accounts and (now - accounts[name].get("last_seen", now)) > 10:
        old_money = accounts[name].get("total_money", current_money)
        time_diff = now - accounts[name]["last_seen"]
        hourly = ((current_money - old_money) / time_diff) * 3600

    accounts[name] = {
        "key": username_key, # نحفظ المفتاح عشان نفلتر في الموقع
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
