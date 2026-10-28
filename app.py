from flask import Flask, request, jsonify, render_template_string
import time

app = Flask(__name__)
accounts = {}

DASHBOARD = """
<!doctype html>
<html><head><meta charset="utf-8"><title>Blockspin Accounts</title>
<style>
body{background:#0d0f12;color:#e6e9ef;font:14px monospace;padding:20px}
table{width:100%;border-collapse:collapse;margin-top:20px}
th,td{padding:12px;text-align:left;border-bottom:1px solid #242830}
th{color:#8b93a3;font-size:12px;text-transform:uppercase;letter-spacing:1px}
.online{color:#4ade80;font-weight:bold}
.offline{color:#f87171;font-weight:bold}
.money{color:#fff;font-weight:bold}
.hourly{color:#4ade80}
</style></head><body>
<h2>Blockspin Live Accounts</h2>
<table>
<tr><th>Account</th><th>Level</th><th>Money</th><th>Last Hour</th><th>Uptime</th><th>Status</th><th>Last Update</th></tr>
{% for name, a in accounts.items() %}
<tr>
  <td>{{ name }}</td>
  <td>{{ a.level }}</td>
  <td class="money">${{ "{:,}".format(a.money) }}</td>
  <td class="hourly">+${{ "{:,}".format(a.hourly) }}/h</td>
  <td>{{ a.uptime }}m</td>
  <td class="{{ 'online' if a.online else 'offline' }}">{{ "Online" if a.online else "Offline" }}</td>
  <td>{{ a.updated }}</td>
</tr>
{% endfor %}
</table>
</body></html>
"""

@app.route("/")
def index():
    # تحديث حالة الأونلاين/الأوفلاين تلقائياً
    now = time.time()
    for name, a in accounts.items():
        if now - a["last_seen"] > 120: # إذا مرت دقيقتين بدون تحديث
            a["online"] = False
    return render_template_string(DASHBOARD, accounts=accounts)

@app.route("/api/report", methods=["POST"])
def report():
    data = request.get_json(force=True, silent=True)
    if not data or "name" not in data:
        return jsonify({"error": "missing name"}), 400
    
    name = data["name"]
    now = time.time()
    
    # حساب الوقت الذي قضاه الحساب متصلاً
    uptime = accounts.get(name, {}).get("uptime", 0)
    if name in accounts and accounts[name]["online"]:
        uptime += 1 # يزيد دقيقة كل ما وصل تقرير
    
    accounts[name] = {
        "level": data.get("level", 0),
        "money": data.get("money", 0),
        "hourly": data.get("hourly", 0),
        "uptime": uptime,
        "online": True,
        "last_seen": now,
        "updated": time.strftime("%H:%M:%S")
    }
    return jsonify({"ok": True})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
