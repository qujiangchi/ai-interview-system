from flask import Blueprint, request, jsonify, current_app
import jwt
import datetime
import bcrypt
from app.database import get_db_connection
import time

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check admin table
        # Note: The database adapter handles ? to %s conversion for Postgres
        cursor.execute("SELECT * FROM admins WHERE username = ?", (username,))
        user = cursor.fetchone()
        
        if user:
            # Convert user to dict if it's not already (RealDictCursor returns dict-like)
            user_data = dict(user)
            stored_hash = user_data['password_hash']
            if isinstance(stored_hash, memoryview):
                stored_hash = bytes(stored_hash).decode('utf-8')
            
            if bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8')):
                token = jwt.encode({
                    'user_id': user_data['id'],
                    'username': user_data['username'],
                    'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
                }, current_app.config['SECRET_KEY'], algorithm='HS256')
                
                return jsonify({
                    'token': token,
                    'username': user_data['username']
                })
    except Exception as e:
        current_app.logger.error(f"Login error: {e}")
        return jsonify({'error': 'Login failed'}), 500
    finally:
        conn.close()
    
    return jsonify({'error': 'Invalid credentials'}), 401

@auth_bp.route('/init', methods=['POST'])
def init_admin():
    """Helper to create initial admin if none exists"""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    secret = data.get('secret')
    
    # Simple protection
    if secret != current_app.config.get('ADMIN_INIT_SECRET'):
        return jsonify({'error': 'Unauthorized'}), 403
        
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("CREATE TABLE IF NOT EXISTS admins (id SERIAL PRIMARY KEY, username TEXT UNIQUE, password_hash TEXT, created_at INTEGER)")
        cursor.execute("INSERT INTO admins (username, password_hash, created_at) VALUES (?, ?, ?)", 
                       (username, hashed, int(time.time())))
        conn.commit()
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 400
        
    conn.close()
    return jsonify({'status': 'success'})
