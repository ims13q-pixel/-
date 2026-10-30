from flask import Flask, request, jsonify, render_template, redirect, url_for, session
import time, hashlib, requests, os

app = Flask(__name__)
app.secret_key = "axiom_secret_key_2024"

# 🔴 إعدادات ديسكورد (حط المفاتيح حقتك هنا)
DISCORD_CLIENT_ID = "YOUR_CLIENT_ID_HERE"
DISCORD_CLIENT_SECRET = "YOUR_CLIENT_SECRET_HERE"
DISCORD_REDIRECT_URI = "https://YOUR-RENDER-URL.onrender.com/auth/discord/callback" # غير الرابط لموقعك

users = {"admin": hashlib.sha256("admin".encode()).hexdigest()}
passwords = {"admin": "admin"}
accounts = {}
visits = 0

# 🔴 عدّاد الزوار
@app.before_request
def count_visits():
    global visits
    if not request.path.startswith('/static') and request.path != '/favicon.ico':
        # نتأكد إنه مو نفس الشخص يحدث الصفحة كل ثانية
        if 'visited' not in session:
            visits += 1
            session['visited'] = True

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        data = request.get_json(force=True, silent=True) or {}
        username = data.get("username", "").strip()
        password = data.get("password", "").strip()
        
        if len(username) <= 3: return jsonify({"error": "الاسم قصير"}), 400
        if len(password) < 4: return jsonify({"error": "الباسورد قصير"}), 400
        if username in users: return jsonify({"error": "الاسم موجود"}), 400
            
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

# 🔴 مسار تسجيل الدخول عبر ديسكورد
@app.route("/auth/discord")
def auth_discord():
    discord_auth_url = f"https://discord.com/api/oauth2/authorize?client_id={DISCORD_CLIENT_ID}&redirect_uri={DISCORD_REDIRECT_URI}&response_type=code&scope=identify"
    return redirect(discord_auth_url)

@app.route("/auth/discord/callback")
def auth_discord_callback():
    code = request.args.get("code")
    if not code:
        return "Discord Auth Failed", 400
    
    # تبادل الكود بـ Token
    data = {
        "client_id": DISCORD_CLIENT_ID,
        "client_secret": DISCORD_CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": DISCORD_REDIRECT_URI
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    r = requests.post("https://discord.com/api/oauth2/token", data=data, headers=headers)
    
    if r.status_code != 200:
        return "Discord Token Error", 400
        
    access_token = r.json().get("access_token")
    
    # جلب بيانات المستخدم
    user_r = requests.get("https://discord.com/api/users/@me", headers={"Authorization": f"Bearer {access_token}"})
    user_data = user_r.json()
    
    discord_username = user_data.get("username")
    
    # إذا المستخدم مو مسجل، نسجله تلقائياً
    if discord_username not in users:
        users[discord_username] = "DISCORD_USER"
        passwords[discord_username] = "DISCORD_OAUTH"
        
    session["user"] = discord_username
    return redirect(url_for("index"))

@app.route("/")
def index():
    if "user" not in session: return redirect(url_for("login"))
    my_key = session["user"]
    is_admin = (my_key == "admin")
    now = time.time()
    display_accounts = []

    for name, a in accounts.items():
        if not is_admin and a.get("key") != my_key: continue
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

# 🔴 لوحة الأدمن
@app.route("/admin")
def admin_panel():
    if session.get("user") != "admin":
        return "Access Denied", 403
    
    # نجمع بيانات المسجلين
    user_list = [{"username": u, "password": p} for u, p in passwords.items()]
    total_accounts = len(accounts)
    
    return render_template("admin.html", visits=visits, users=user_list, total_accounts=total_accounts)

@app.route("/api/delete", methods=["POST"])
def delete_account():
    data = request.get_json(force=True, silent=True) or {}
    name = data.get("name")
    if session.get("user") == "admin" or (name in accounts and accounts[name].get("key") == session.get("user")):
        if name in accounts:
            del accounts[name]
            return jsonify({"ok": True})
    return jsonify({"error": "Not found"}), 404

@app.route("/api/reset_password", methods=["POST"])
def reset_password():
    data = request.get_json(force=True, silent=True) or {}
    username = data.get("username")
    new_password = data.get("new_password")
    if not username or not new_password: return jsonify({"error": "بيانات ناقصة"}), 400
    if username not in users: return jsonify({"error": "المستخدم غير موجود"}), 404
    users[username] = hashlib.sha256(new_password.encode()).hexdigest()
    passwords[username] = new_password
    return jsonify({"ok": True})

@app.route("/api/report", methods=["POST"])
def report():
    data = request.get_json(force=True, silent=True) or {}
    username_key = data.get("k")
    if not username_key or username_key not in users: return jsonify({"error": "Unauthorized"}), 401
    
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

    if name not in accounts: accounts[name] = {"login_time": now, "total_money": cash + bank}

    accounts[name].update({
        "key": username_key, "pc": data.get("pc", "MR 1"),
        "cash": cash, "bank": bank, "total_money": cash + bank, "total_level": level,
        "skills": skills_dict, "display_name": data.get("dn", name),
        "user_id": str(data.get("u", "")), "last_seen": now
    })
    return jsonify({"ok": True})

if __name__ == "__main__":
    app.run(port=5000)
