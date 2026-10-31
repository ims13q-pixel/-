@app.route("/")
def index():
    if "user" not in session: return redirect(url_for("login"))
    my_key = session["user"]
    is_admin = (my_key == "admin")
    now = time.time()
    display_accounts = []

    _, _, _, accounts = load_db()

    online_count = 0
    offline_count = 0
    total_farmed = 0

    for name, a in accounts.items():
        if not is_admin and a.get("key") != my_key: continue
        is_online = (now - a.get("last_seen", 0)) < 60 
        if is_online: online_count += 1
        else: offline_count += 1
        
        cash = int(a.get("cash", 0) or 0)
        bank = int(a.get("bank", 0) or 0)
        total = cash + bank
        
        start_time = a.get("session_start_time", now)
        start_money = a.get("session_start_money", total)
        
        uptime_sec = int(now - start_time)
        farmed = total - start_money
        total_farmed += farmed
        
        if uptime_sec < 60:
            uptime_str = "أقل من دقيقة"
        else:
            hours = uptime_sec // 3600
            minutes = (uptime_sec % 3600) // 60
            uptime_str = f"{hours}س {minutes}د" if hours > 0 else f"{minutes}د"
        
        acc_copy = a.copy()
        acc_copy["name"] = name
        acc_copy["online"] = is_online
        acc_copy["total_level"] = int(a.get("total_level", 0) or 0)
        acc_copy["total_money"] = total
        acc_copy["cash"] = cash
        acc_copy["bank"] = bank
        acc_copy["uptime_str"] = uptime_str
        acc_copy["farmed"] = farmed
        if "skills" not in acc_copy or not isinstance(acc_copy["skills"], dict): acc_copy["skills"] = {}
        display_accounts.append(acc_copy)
        
    return render_template("index.html", my_key=my_key, accounts=display_accounts, online_count=online_count, offline_count=offline_count, total_farmed=total_farmed)
