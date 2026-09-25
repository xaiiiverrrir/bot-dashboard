"""
Martin Bot Dashboard - Flask Backend
Connects to martin.db and provides API endpoints for admin dashboard
"""

from flask import Flask, render_template, jsonify, request, session
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import sqlite3
import json
import os
from functools import wraps
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-change-this')
CORS(app)

# Database path - point to your bot's database
DB_PATH = os.getenv('DB_PATH', '../martin.db')

# Owner IDs for authentication
OWNERS = [int(x) for x in os.getenv('OWNERS', '1488177833925808318,1202143213037826092').split(',')]

def get_db():
    """Get database connection with row factory"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def require_owner(f):
    """Decorator to require owner authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        owner_id = session.get('owner_id')
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if not owner_id and not token:
            return jsonify({'error': 'Unauthorized'}), 401
        
        # For now, token-based auth is simplified
        # In production, validate token against Discord OAuth
        return f(*args, **kwargs)
    return decorated_function

# ============================================================================
# AUTHENTICATION ROUTES
# ============================================================================

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Login endpoint - validate owner token"""
    data = request.json
    token = data.get('token')
    owner_id = data.get('owner_id')
    
    if owner_id in OWNERS:
        session['owner_id'] = owner_id
        return jsonify({'success': True, 'owner_id': owner_id})
    
    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    """Logout endpoint"""
    session.clear()
    return jsonify({'success': True})

@app.route('/api/auth/status', methods=['GET'])
def auth_status():
    """Check if user is logged in"""
    owner_id = session.get('owner_id')
    return jsonify({'authenticated': owner_id is not None, 'owner_id': owner_id})

# ============================================================================
# DASHBOARD STATS ROUTES
# ============================================================================

@app.route('/api/stats/overview', methods=['GET'])
def stats_overview():
    """Get overall bot statistics"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        # Total users
        cursor.execute('SELECT COUNT(*) as count FROM users')
        total_users = cursor.fetchone()['count']
        
        # Total cards in circulation
        cursor.execute('SELECT COUNT(*) as count FROM cards')
        total_cards = cursor.fetchone()['count']
        
        # Total coins distributed
        cursor.execute('SELECT SUM(coins) as total FROM users')
        total_coins = cursor.fetchone()['total'] or 0
        
        # Total coers distributed
        cursor.execute('SELECT SUM(coers) as total FROM users')
        total_coers = cursor.fetchone()['total'] or 0
        
        # Active trades
        cursor.execute("SELECT COUNT(*) as count FROM trades WHERE status = 'pending'")
        active_trades = cursor.fetchone()['count']
        
        # Registered guilds
        cursor.execute("SELECT COUNT(*) as count FROM guild_settings WHERE is_registered = 1")
        registered_guilds = cursor.fetchone()['count']
        
        # Cards by rarity
        cursor.execute("""
            SELECT rarity, COUNT(*) as count 
            FROM cards 
            GROUP BY rarity
        """)
        rarity_dist = {row['rarity']: row['count'] for row in cursor.fetchall()}
        
        return jsonify({
            'total_users': total_users,
            'total_cards': total_cards,
            'total_coins': int(total_coins),
            'total_coers': int(total_coers),
            'active_trades': active_trades,
            'registered_guilds': registered_guilds,
            'rarity_distribution': rarity_dist
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/stats/leaderboard/<type>', methods=['GET'])
def get_leaderboard(type):
    """Get leaderboard by type: coins, cards, trades, earnings"""
    limit = request.args.get('limit', 10, type=int)
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        if type == 'coins':
            cursor.execute("""
                SELECT user_id, username, coins, cards_owned 
                FROM users 
                ORDER BY coins DESC 
                LIMIT ?
            """, (limit,))
        elif type == 'cards':
            cursor.execute("""
                SELECT user_id, username, cards_owned, coins 
                FROM users 
                ORDER BY cards_owned DESC 
                LIMIT ?
            """, (limit,))
        elif type == 'trades':
            cursor.execute("""
                SELECT user_id, COUNT(*) as trade_count 
                FROM trades 
                WHERE status = 'completed'
                GROUP BY user_id 
                ORDER BY trade_count DESC 
                LIMIT ?
            """, (limit,))
        elif type == 'earnings':
            cursor.execute("""
                SELECT user_id, SUM(amount) as total_earned 
                FROM transactions 
                WHERE type = 'earn'
                GROUP BY user_id 
                ORDER BY total_earned DESC 
                LIMIT ?
            """, (limit,))
        else:
            return jsonify({'error': 'Invalid leaderboard type'}), 400
        
        rows = cursor.fetchall()
        data = [dict(row) for row in rows]
        
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# ============================================================================
# USER MANAGEMENT ROUTES
# ============================================================================

@app.route('/api/users', methods=['GET'])
@require_owner
def get_users():
    """Get list of all users with pagination"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    search = request.args.get('search', '').strip()
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        if search:
            cursor.execute("""
                SELECT * FROM users 
                WHERE username LIKE ? OR user_id = ?
                LIMIT ? OFFSET ?
            """, (f'%{search}%', search, per_page, (page - 1) * per_page))
        else:
            cursor.execute("""
                SELECT * FROM users 
                LIMIT ? OFFSET ?
            """, (per_page, (page - 1) * per_page))
        
        rows = cursor.fetchall()
        data = [dict(row) for row in rows]
        
        return jsonify({
            'users': data,
            'page': page,
            'per_page': per_page,
            'total': len(data)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/users/<int:user_id>', methods=['GET'])
def get_user_detail(user_id):
    """Get detailed user info"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        user = cursor.fetchone()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        user_dict = dict(user)
        
        # Get user's cards
        cursor.execute("""
            SELECT code, idol_name, group_name, rarity, serial_num, condition, obtained_at
            FROM cards 
            WHERE user_id = ?
            ORDER BY obtained_at DESC
        """, (user_id,))
        
        cards = [dict(row) for row in cursor.fetchall()]
        
        # Get user's albums
        cursor.execute("""
            SELECT album_id, name, created_at, completion_percentage
            FROM albums 
            WHERE user_id = ?
        """, (user_id,))
        
        albums = [dict(row) for row in cursor.fetchall()]
        
        # Get transaction history
        cursor.execute("""
            SELECT * FROM transactions 
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT 20
        """, (user_id,))
        
        transactions = [dict(row) for row in cursor.fetchall()]
        
        return jsonify({
            'user': user_dict,
            'cards': cards,
            'albums': albums,
            'transactions': transactions
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/users/<int:user_id>/balance', methods=['POST'])
@require_owner
def set_user_balance(user_id):
    """Adjust user's balance (owner only)"""
    data = request.json
    coins = data.get('coins')
    coers = data.get('coers')
    reason = data.get('reason', 'Admin adjustment')
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        if coins is not None:
            cursor.execute('UPDATE users SET coins = ? WHERE user_id = ?', (coins, user_id))
            cursor.execute("""
                INSERT INTO transactions (user_id, type, amount, reason, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, 'admin_adjustment', coins, reason, datetime.now().isoformat()))
        
        if coers is not None:
            cursor.execute('UPDATE users SET coers = ? WHERE user_id = ?', (coers, user_id))
        
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# ============================================================================
# CARD MANAGEMENT ROUTES
# ============================================================================

@app.route('/api/cards', methods=['GET'])
def get_cards():
    """Get cards with filters"""
    rarity = request.args.get('rarity', '').strip()
    group = request.args.get('group', '').strip()
    idol = request.args.get('idol', '').strip()
    limit = request.args.get('limit', 100, type=int)
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        query = 'SELECT * FROM cards WHERE 1=1'
        params = []
        
        if rarity:
            query += ' AND rarity = ?'
            params.append(rarity)
        if group:
            query += ' AND group_name LIKE ?'
            params.append(f'%{group}%')
        if idol:
            query += ' AND idol_name LIKE ?'
            params.append(f'%{idol}%')
        
        query += ' LIMIT ?'
        params.append(limit)
        
        cursor.execute(query, params)
        cards = [dict(row) for row in cursor.fetchall()]
        
        return jsonify(cards)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/cards/<code>', methods=['GET'])
def get_card_detail(code):
    """Get specific card details"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute('SELECT * FROM cards WHERE code = ?', (code,))
        card = cursor.fetchone()
        
        if not card:
            return jsonify({'error': 'Card not found'}), 404
        
        return jsonify(dict(card))
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/cards/<code>/burn', methods=['POST'])
@require_owner
def burn_card(code):
    """Delete a card from the database"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute('SELECT user_id FROM cards WHERE code = ?', (code,))
        card = cursor.fetchone()
        
        if not card:
            return jsonify({'error': 'Card not found'}), 404
        
        user_id = card['user_id']
        
        # Delete card
        cursor.execute('DELETE FROM cards WHERE code = ?', (code,))
        
        # Update user's card count
        cursor.execute('SELECT COUNT(*) as count FROM cards WHERE user_id = ?', (user_id,))
        new_count = cursor.fetchone()['count']
        cursor.execute('UPDATE users SET cards_owned = ? WHERE user_id = ?', (new_count, user_id))
        
        conn.commit()
        return jsonify({'success': True, 'message': f'Card {code} burned'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/cards/add', methods=['POST'])
@require_owner
def add_card():
    """Add a new card directly to inventory"""
    data = request.json
    required = ['user_id', 'idol_name', 'group_name', 'image_url', 'rarity']
    
    if not all(k in data for k in required):
        return jsonify({'error': 'Missing required fields'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        # Generate code if not provided
        code = data.get('code') or f"{data['group_name'][:3].upper()}-{data['idol_name'][:3].upper()}-{datetime.now().timestamp()}"
        serial_num = data.get('serial_num', '001')
        condition = data.get('condition', 'mint')
        
        cursor.execute("""
            INSERT INTO cards (
                user_id, code, idol_name, group_name, rarity, 
                serial_num, image_url, condition, obtained_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data['user_id'], code, data['idol_name'], data['group_name'],
            data['rarity'], serial_num, data['image_url'], condition,
            datetime.now().isoformat()
        ))
        
        # Update card count
        cursor.execute('SELECT COUNT(*) as count FROM cards WHERE user_id = ?', (data['user_id'],))
        count = cursor.fetchone()['count']
        cursor.execute('UPDATE users SET cards_owned = ? WHERE user_id = ?', (count, data['user_id']))
        
        conn.commit()
        return jsonify({'success': True, 'code': code})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# ============================================================================
# ANALYTICS ROUTES
# ============================================================================

@app.route('/api/analytics/activity', methods=['GET'])
def analytics_activity():
    """Get activity over time"""
    days = request.args.get('days', 30, type=int)
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        # Commands used in last N days
        cursor.execute("""
            SELECT DATE(timestamp) as date, COUNT(*) as count
            FROM transactions
            WHERE timestamp > datetime('now', '-' || ? || ' days')
            GROUP BY DATE(timestamp)
            ORDER BY date
        """, (days,))
        
        activity = [dict(row) for row in cursor.fetchall()]
        
        return jsonify(activity)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/analytics/economy', methods=['GET'])
def analytics_economy():
    """Get economy metrics"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        # Total coins in system
        cursor.execute('SELECT SUM(coins) as total FROM users')
        total_coins = cursor.fetchone()['total'] or 0
        
        # Average coins per user
        cursor.execute('SELECT AVG(coins) as avg FROM users')
        avg_coins = cursor.fetchone()['avg'] or 0
        
        # Coins earned last 24h
        cursor.execute("""
            SELECT SUM(amount) as total FROM transactions
            WHERE type = 'earn' AND timestamp > datetime('now', '-1 day')
        """)
        coins_earned_24h = cursor.fetchone()['total'] or 0
        
        # Coins spent last 24h
        cursor.execute("""
            SELECT SUM(amount) as total FROM transactions
            WHERE type IN ('purchase', 'trade', 'gift') AND timestamp > datetime('now', '-1 day')
        """)
        coins_spent_24h = cursor.fetchone()['total'] or 0
        
        return jsonify({
            'total_coins': int(total_coins),
            'avg_coins_per_user': float(avg_coins),
            'coins_earned_24h': int(coins_earned_24h),
            'coins_spent_24h': int(coins_spent_24h)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# ============================================================================
# ADMIN CONTROL ROUTES
# ============================================================================

@app.route('/api/admin/maintenance', methods=['GET', 'POST'])
@require_owner
def maintenance_mode():
    """Get or set maintenance mode status"""
    if request.method == 'POST':
        data = request.json
        enabled = data.get('enabled', False)
        # This would need to be stored in system_settings table
        return jsonify({'success': True, 'maintenance': enabled})
    
    return jsonify({'maintenance': False})

@app.route('/api/admin/events', methods=['GET'])
@require_owner
def get_events():
    """Get active seasonal events"""
    events = ['christmas', 'halloween', 'newyear', 'valentines', 'easter']
    
    # Check which events are currently active by date
    month = datetime.now().month
    active_events = {}
    
    active_events['christmas'] = month == 12
    active_events['newyear'] = month == 1
    active_events['valentines'] = month == 2
    active_events['easter'] = month == 4
    active_events['halloween'] = month == 10
    
    return jsonify(active_events)

@app.route('/api/admin/events/<event>', methods=['POST'])
@require_owner
def toggle_event(event):
    """Enable/disable an event"""
    data = request.json
    enabled = data.get('enabled', False)
    
    # This would need bot integration to update system_settings
    return jsonify({'success': True, 'event': event, 'enabled': enabled})

@app.route('/api/admin/logs', methods=['GET'])
@require_owner
def get_logs():
    """Get recent admin logs"""
    limit = request.args.get('limit', 100, type=int)
    
    # Return recent transactions (proxy for logs)
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT * FROM transactions
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))
        
        logs = [dict(row) for row in cursor.fetchall()]
        return jsonify(logs)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# ============================================================================
# SERVER ROUTES
# ============================================================================

@app.route('/api/servers', methods=['GET'])
def get_servers():
    """Get all registered servers"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT * FROM guild_settings
            WHERE is_registered = 1
            ORDER BY guild_id
        """)
        
        servers = [dict(row) for row in cursor.fetchall()]
        return jsonify(servers)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM users')
        user_count = cursor.fetchone()[0]
        conn.close()
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'users': user_count
        })
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500

# ============================================================================
# FRONTEND ROUTES
# ============================================================================

@app.route('/')
def index():
    """Serve dashboard homepage"""
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    """Main dashboard page"""
    return render_template('dashboard.html')

@app.route('/users')
def users_page():
    """Users management page"""
    return render_template('users.html')

@app.route('/cards')
def cards_page():
    """Cards management page"""
    return render_template('cards.html')

@app.route('/analytics')
def analytics_page():
    """Analytics page"""
    return render_template('analytics.html')

@app.route('/admin')
def admin_page():
    """Admin controls page"""
    return render_template('admin.html')

if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('PORT', 5000)),
        debug=os.getenv('FLASK_ENV') == 'development'
    )
s': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# ============================================================================
# CARD MANAGEMENT ROUTES
# ============================================================================

@app.route('/api/cards', methods=['GET'])
def get_cards():
    """Get cards with filters"""
    rarity = request.args.get('rarity', '').strip()
    group = request.args.get('group', '').strip()
    idol = request.args.get('idol', '').strip()
    limit = request.args.get('limit', 100, type=int)
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        query = 'SELECT * FROM cards WHERE 1=1'
        params = []
        
        if rarity:
            query += ' AND rarity = ?'
            params.append(rarity)
        if group:
            query += ' AND group_name LIKE ?'
            params.append(f'%{group}%')
        if idol:
            query += ' AND idol_name LIKE ?'
            params.append(f'%{idol}%')
        
        query += ' LIMIT ?'
        params.append(limit)
        
        cursor.execute(query, params)
        cards = [dict(row) for row in cursor.fetchall()]
        
        return jsonify(cards)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/cards/<code>', methods=['GET'])
def get_card_detail(code):
    """Get specific card details"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute('SELECT * FROM cards WHERE code = ?', (code,))
        card = cursor.fetchone()
        
        if not card:
            return jsonify({'error': 'Card not found'}), 404
        
        return jsonify(dict(card))
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/cards/<code>/burn', methods=['POST'])
@require_owner
def burn_card(code):
    """Delete a card from the database"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute('SELECT user_id FROM cards WHERE code = ?', (code,))
        card = cursor.fetchone()
        
        if not card:
            return jsonify({'error': 'Card not found'}), 404
        
        user_id = card['user_id']
        
        # Delete card
        cursor.execute('DELETE FROM cards WHERE code = ?', (code,))
        
        # Update user's card count
        cursor.execute('SELECT COUNT(*) as count FROM cards WHERE user_id = ?', (user_id,))
        new_count = cursor.fetchone()['count']
        cursor.execute('UPDATE users SET cards_owned = ? WHERE user_id = ?', (new_count, user_id))
        
        conn.commit()
        return jsonify({'success': True, 'message': f'Card {code} burned'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/cards/add', methods=['POST'])
@require_owner
def add_card():
    """Add a new card directly to inventory"""
    data = request.json
    required = ['user_id', 'idol_name', 'group_name', 'image_url', 'rarity']
    
    if not all(k in data for k in required):
        return jsonify({'error': 'Missing required fields'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        # Generate code if not provided
        code = data.get('code') or f"{data['group_name'][:3].upper()}-{data['idol_name'][:3].upper()}-{datetime.now().timestamp()}"
        serial_num = data.get('serial_num', '001')
        condition = data.get('condition', 'mint')
        
        cursor.execute("""
            INSERT INTO cards (
                user_id, code, idol_name, group_name, rarity, 
                serial_num, image_url, condition, obtained_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data['user_id'], code, data['idol_name'], data['group_name'],
            data['rarity'], serial_num, data['image_url'], condition,
            datetime.now().isoformat()
        ))
        
        # Update card count
        cursor.execute('SELECT COUNT(*) as count FROM cards WHERE user_id = ?', (data['user_id'],))
        count = cursor.fetchone()['count']
        cursor.execute('UPDATE users SET cards_owned = ? WHERE user_id = ?', (count, data['user_id']))
        
        conn.commit()
        return jsonify({'success': True, 'code': code})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# ============================================================================
# ANALYTICS ROUTES
# ============================================================================

@app.route('/api/analytics/activity', methods=['GET'])
def analytics_activity():
    """Get activity over time"""
    days = request.args.get('days', 30, type=int)
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        # Commands used in last N days
        cursor.execute("""
            SELECT DATE(timestamp) as date, COUNT(*) as count
            FROM transactions
            WHERE timestamp > datetime('now', '-' || ? || ' days')
            GROUP BY DATE(timestamp)
            ORDER BY date
        """, (days,))
        
        activity = [dict(row) for row in cursor.fetchall()]
        
        return jsonify(activity)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/analytics/economy', methods=['GET'])
def analytics_economy():
    """Get economy metrics"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        # Total coins in system
        cursor.execute('SELECT SUM(coins) as total FROM users')
        total_coins = cursor.fetchone()['total'] or 0
        
        # Average coins per user
        cursor.execute('SELECT AVG(coins) as avg FROM users')
        avg_coins = cursor.fetchone()['avg'] or 0
        
        # Coins earned last 24h
        cursor.execute("""
            SELECT SUM(amount) as total FROM transactions
            WHERE type = 'earn' AND timestamp > datetime('now', '-1 day')
        """)
        coins_earned_24h = cursor.fetchone()['total'] or 0
        
        # Coins spent last 24h
        cursor.execute("""
            SELECT SUM(amount) as total FROM transactions
            WHERE type IN ('purchase', 'trade', 'gift') AND timestamp > datetime('now', '-1 day')
        """)
        coins_spent_24h = cursor.fetchone()['total'] or 0
        
        return jsonify({
            'total_coins': int(total_coins),
            'avg_coins_per_user': float(avg_coins),
            'coins_earned_24h': int(coins_earned_24h),
            'coins_spent_24h': int(coins_spent_24h)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# ============================================================================
# ADMIN CONTROL ROUTES
# ============================================================================

@app.route('/api/admin/maintenance', methods=['GET', 'POST'])
@require_owner
def maintenance_mode():
    """Get or set maintenance mode status"""
    if request.method == 'POST':
        data = request.json
        enabled = data.get('enabled', False)
        # This would need to be stored in system_settings table
        return jsonify({'success': True, 'maintenance': enabled})
    
    return jsonify({'maintenance': False})

@app.route('/api/admin/events', methods=['GET'])
@require_owner
def get_events():
    """Get active seasonal events"""
    events = ['christmas', 'halloween', 'newyear', 'valentines', 'easter']
    
    # Check which events are currently active by date
    month = datetime.now().month
    active_events = {}
    
    active_events['christmas'] = month == 12
    active_events['newyear'] = month == 1
    active_events['valentines'] = month == 2
    active_events['easter'] = month == 4
    active_events['halloween'] = month == 10
    
    return jsonify(active_events)

@app.route('/api/admin/events/<event>', methods=['POST'])
@require_owner
def toggle_event(event):
    """Enable/disable an event"""
    data = request.json
    enabled = data.get('enabled', False)
    
    # This would need bot integration to update system_settings
    return jsonify({'success': True, 'event': event, 'enabled': enabled})

@app.route('/api/admin/logs', methods=['GET'])
@require_owner
def get_logs():
    """Get recent admin logs"""
    limit = request.args.get('limit', 100, type=int)
    
    # Return recent transactions (proxy for logs)
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT * FROM transactions
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))
        
        logs = [dict(row) for row in cursor.fetchall()]
        return jsonify(logs)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# ============================================================================
# SERVER ROUTES
# ============================================================================

@app.route('/api/servers', methods=['GET'])
def get_servers():
    """Get all registered servers"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT * FROM guild_settings
            WHERE is_registered = 1
            ORDER BY guild_id
        """)
        
        servers = [dict(row) for row in cursor.fetchall()]
        return jsonify(servers)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

============================================================================
# HEALTH CHECK
# ============================================================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM users')
        user_count = cursor.fetchone()[0]
        conn.close()
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'users': user_count
        })
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500

# ============================================================================
# FRONTEND ROUTES
# ============================================================================

@app.route('/')
def index():
    """Serve dashboard homepage"""
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    """Main dashboard page"""
    return render_template('dashboard.html')

@app.route('/users')
def users_page():
    """Users management page"""
    return render_template('users.html')

@app.route('/cards')
def cards_page():
    """Cards management page"""
    return render_template('cards.html')

@app.route('/analytics')
def analytics_page():
    """Analytics page"""
    return render_template('analytics.html')

@app.route('/admin')
def admin_page():
    """Admin controls page"""
    return render_template('admin.html')

if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('PORT', 5000)),
        debug=os.getenv('FLASK_ENV') == 'development'
    )
