from flask import Flask, request, jsonify, render_template
import time

app = Flask(__name__)
accounts = {}

@app.route("/")
def index():
    now = time.time()
    for name, a in accounts.items():
        # تحويل الثواني لساعات ودقائق للـ Uptime
        a["uptime_display"] = round(a.get("uptime", 0), 2)
        a["online"] = (now - a.get("last_seen", 0)) < 120
    return render_template("index.html", accounts=accounts)

@app.route("/api/report", methods=["POST"])
def report():
    data = request.get_json(force=True, silent=True)
    if not data or "name" not in data:
        return jsonify({"error": "missing data"}), 400
    
    name = data["name"]
    now = time.time()
    
    # حساب الوقت الذي قضاه متصلاً
    uptime = accounts.get(name, {}).get("uptime", 0)
    if name in accounts and (now - accounts[name]["last_seen"]) < 120:
        uptime += (now - accounts[name]["last_seen"]) / 3600 # تحويل لساعات
        
    accounts[name] = {
        "level": data.get("level", 0),
        "money": data.get("money", 0),
        "hourly": data.get("hourly", 0),
        "uptime": uptime,
        "last_seen": now,
    }
    return jsonify({"ok": True})

if __name__ == "__main__":
    app.run(port=5000)
