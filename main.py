import os
import sqlite3
from flask import Flask, render_template_string, jsonify

app = Flask(__name__)

def get_live_stats():
    db_path = "bot.db"
    stats = {
        "active_users": 0,
        "total_cards_claimed": 0,
        "coins_in_circulation": "0",
        "completed_trades": 0
    }
    
    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM users;")
            stats["active_users"] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM user_cards;")
            stats["total_cards_claimed"] = cursor.fetchone()[0]
            
            cursor.execute("SELECT SUM(balance) FROM users;")
            total_coins = cursor.fetchone()[0]
            stats["coins_in_circulation"] = f"{total_coins:,}" if total_coins else "0"
            
            cursor.execute("SELECT COUNT(*) FROM trades WHERE status = 'completed';")
            stats["completed_trades"] = cursor.fetchone()[0]
            
            conn.close()
        except Exception as e:
            print(f"Database read error: {e}")
            
    return stats

MINIMAL_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Bot Stats</title>
    <script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
</head>
<body class="bg-black text-white min-h-screen flex items-center justify-center p-6">
    <div class="w-full max-w-2xl space-y-8">
        <div class="flex justify-between items-baseline border-b border-neutral-900 pb-4">
            <h1 class="text-lg font-medium tracking-tight text-neutral-300">Bot Overview</h1>
            <span class="text-xs text-emerald-400 flex items-center gap-1.5"><span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>Live</span>
        </div>

        <div class="grid grid-cols-2 gap-4">
            <div class="bg-neutral-950 border border-neutral-900 p-6 rounded-2xl">
                <p class="text-xs text-neutral-500 uppercase tracking-wider mb-2">Active Users</p>
                <p id="stat-users" class="text-3xl font-light tracking-tight">{{ stats.active_users }}</p>
            </div>
            <div class="bg-neutral-950 border border-neutral-900 p-6 rounded-2xl">
                <p class="text-xs text-neutral-500 uppercase tracking-wider mb-2">Cards Claimed</p>
                <p id="stat-cards" class="text-3xl font-light tracking-tight">{{ stats.total_cards_claimed }}</p>
            </div>
            <div class="bg-neutral-950 border border-neutral-900 p-6 rounded-2xl">
                <p class="text-xs text-neutral-500 uppercase tracking-wider mb-2">Coins in Circulation</p>
                <p id="stat-coins" class="text-3xl font-light tracking-tight text-yellow-500/90">{{ stats.coins_in_circulation }}</p>
            </div>
            <div class="bg-neutral-950 border border-neutral-900 p-6 rounded-2xl">
                <p class="text-xs text-neutral-500 uppercase tracking-wider mb-2">Completed Trades</p>
                <p id="stat-trades" class="text-3xl font-light tracking-tight text-purple-400/90">{{ stats.completed_trades }}</p>
            </div>
        </div>
    </div>

    <script>
        async function fetchStats() {
            try {
                let response = await fetch('/api/stats');
                let data = await response.json();
                document.getElementById('stat-users').innerText = data.active_users;
                document.getElementById('stat-cards').innerText = data.total_cards_claimed;
                document.getElementById('stat-coins').innerText = data.coins_in_circulation;
                document.getElementById('stat-trades').innerText = data.completed_trades;
            } catch (err) {
                console.error("Failed to sync stats:", err);
            }
        }
        setInterval(fetchStats, 10000); // Automatically updates every 10 seconds
    </script>
</body>
</html>
"""

@app.route('/')
def dashboard():
    stats = get_live_stats()
    return render_template_string(MINIMAL_HTML, stats=stats)

@app.route('/api/stats')
def api_stats():
    return jsonify(get_live_stats())

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
    
