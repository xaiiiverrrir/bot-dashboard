import os
import urllib.parse as urlparse
import psycopg2
from flask import Flask, render_template_string, jsonify, request, redirect, url_for

app = Flask(__name__)

def get_db_connection():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        return None
    try:
        url = urlparse.urlparse(database_url.strip().strip('"').strip("'"))
        return psycopg2.connect(
            dbname=url.path[1:],
            user=url.username,
            password=url.password,
            host=url.hostname,
            port=url.port,
            sslmode='require'
        )
    except Exception as e:
        print(f"Connection error: {e}")
        return None

def get_live_stats():
    stats = {
        "active_users": 0,
        "total_cards_claimed": 0,
        "coins_in_circulation": "0",
        "completed_trades": 0
    }
    
    conn = get_db_connection()
    if conn:
        try:
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
            
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"Database read error: {e}")
            
    return stats

LIQUID_GLASS_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Bot Overview & Control Panel</title>
    <script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
    <style>
        .glass-panel {
            background: rgba(255, 255, 255, 0.03);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid rgba(255, 255, 255, 0.08);
            box-shadow: inset 0 1px 0 0 rgba(255, 255, 255, 0.1), 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        }
        .glass-input {
            background: rgba(0, 0, 0, 0.3);
            border: 1px solid rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(8px);
        }
        .glass-input:focus {
            outline: none;
            border-color: rgba(168, 85, 247, 0.5);
        }
        .bg-mesh {
            background-image: radial-gradient(at 10% 20%, rgba(56, 189, 248, 0.06) 0px, transparent 50%),
                              radial-gradient(at 90% 80%, rgba(168, 85, 247, 0.06) 0px, transparent 50%);
        }
    </style>
</head>
<body class="bg-neutral-950 bg-mesh text-white min-h-screen p-6 flex flex-col items-center justify-center">
    <div class="w-full max-w-2xl space-y-6">
        
        <!-- Header -->
        <div class="glass-panel px-6 py-4 rounded-2xl flex justify-between items-center">
            <h1 class="text-sm font-medium tracking-wide text-neutral-300">Bot Overview (Cloud Synced)</h1>
            <span class="text-xs text-emerald-400 flex items-center gap-2">
                <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse shadow-[0_0_8px_rgba(52,211,153,0.6)]"></span>
                Live
            </span>
        </div>

        <!-- Metrics Grid -->
        <div class="grid grid-cols-2 gap-4">
            <div class="glass-panel p-6 rounded-2xl">
                <p class="text-xs text-neutral-400 tracking-wider uppercase mb-2">Active Users</p>
                <p id="stat-users" class="text-3xl font-light tracking-tight text-white">{{ stats.active_users }}</p>
            </div>
            <div class="glass-panel p-6 rounded-2xl">
                <p class="text-xs text-neutral-400 tracking-wider uppercase mb-2">Cards Claimed</p>
                <p id="stat-cards" class="text-3xl font-light tracking-tight text-white">{{ stats.total_cards_claimed }}</p>
            </div>
            <div class="glass-panel p-6 rounded-2xl">
                <p class="text-xs text-neutral-400 tracking-wider uppercase mb-2">Coins in Circulation</p>
                <p id="stat-coins" class="text-3xl font-light tracking-tight text-amber-300/90">{{ stats.coins_in_circulation }}</p>
            </div>
            <div class="glass-panel p-6 rounded-2xl">
                <p class="text-xs text-neutral-400 tracking-wider uppercase mb-2">Completed Trades</p>
                <p id="stat-trades" class="text-3xl font-light tracking-tight text-purple-300/90">{{ stats.completed_trades }}</p>
            </div>
        </div>

        <!-- Interactive Admin Controls -->
        <div class="glass-panel p-6 rounded-2xl space-y-4">
            <h2 class="text-xs text-neutral-400 tracking-wider uppercase">Interactive Management</h2>
            
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <!-- Add Coins Form -->
                <form action="/action/add-coins" method="POST" class="space-y-3">
                    <p class="text-xs text-neutral-300 font-medium">Add Coins to User</p>
                    <input type="text" name="user_id" placeholder="User ID" required class="w-full px-4 py-2 rounded-xl text-sm glass-input text-white placeholder-neutral-500">
                    <input type="number" name="amount" placeholder="Amount" required class="w-full px-4 py-2 rounded-xl text-sm glass-input text-white placeholder-neutral-500">
                    <button type="submit" class="w-full py-2 bg-amber-500/20 hover:bg-amber-500/30 border border-amber-500/30 text-amber-300 rounded-xl text-xs font-medium tracking-wide transition cursor-pointer">Give Coins</button>
                </form>

                <!-- Add Card Form -->
                <form action="/action/add-card" method="POST" class="space-y-3">
                    <p class="text-xs text-neutral-300 font-medium">Give Card to User</p>
                    <input type="text" name="user_id" placeholder="User ID" required class="w-full px-4 py-2 rounded-xl text-sm glass-input text-white placeholder-neutral-500">
                    <input type="text" name="card_id" placeholder="Card ID or Name" required class="w-full px-4 py-2 rounded-xl text-sm glass-input text-white placeholder-neutral-500">
                    <button type="submit" class="w-full py-2 bg-purple-500/20 hover:bg-purple-500/30 border border-purple-500/30 text-purple-300 rounded-xl text-xs font-medium tracking-wide transition cursor-pointer">Give Card</button>
                </form>
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
        setInterval(fetchStats, 10000);
    </script>
</body>
</html>
"""

@app.route('/')
def dashboard():
    stats = get_live_stats()
    return render_template_string(LIQUID_GLASS_HTML, stats=stats)

@app.route('/api/stats')
def api_stats():
    return jsonify(get_live_stats())

@app.route('/action/add-coins', methods=['POST'])
def add_coins():
    user_id = request.form.get('user_id')
    amount = request.form.get('amount')
    conn = get_db_connection()
    if conn and user_id and amount:
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET balance = balance + %s WHERE user_id = %s;", (amount, user_id))
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"Error adding coins: {e}")
    return redirect(url_for('dashboard'))

@app.route('/action/add-card', methods=['POST'])
def add_card():
    user_id = request.form.get('user_id')
    card_id = request.form.get('card_id')
    conn = get_db_connection()
    if conn and user_id and card_id:
        try:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO user_cards (user_id, card_id) VALUES (%s, %s);", (user_id, card_id))
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"Error adding card: {e}")
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
