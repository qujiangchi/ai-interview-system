"""
Authentication API Module
认证API模块

此模块处理用户认证和授权相关的操作，包括：
- 管理员登录 (JWT Token生成)
- 初始化管理员账号
"""

from flask import Blueprint, request, jsonify, current_app
import jwt
import datetime
import bcrypt
from app.core.database import get_db_connection
import time

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    """
    管理员登录
    Admin Login
    
    验证用户名和密码，成功后返回 JWT Token。
    """
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 查询管理员表
        # Check admin table
        # Note: The database adapter handles ? to %s conversion for Postgres
        cursor.execute("SELECT * FROM admins WHERE username = ?", (username,))
        user = cursor.fetchone()
        
        if user:
            # 转换查询结果为字典
            # Convert user to dict if it's not already (RealDictCursor returns dict-like)
            user_data = dict(user)
            stored_hash = user_data['password_hash']
            if isinstance(stored_hash, memoryview):
                stored_hash = bytes(stored_hash).decode('utf-8')
            
            # 验证密码
            if bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8')):
                # 生成 JWT Token
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
    """
    初始化管理员账号
    Initialize Admin Account
    
    Helper to create initial admin if none exists.
    Requires a secret key defined in environment variables.
    """
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    secret = data.get('secret')
    
    # 简单的安全验证
    # Simple protection
    if secret != current_app.config.get('ADMIN_INIT_SECRET'):
        return jsonify({'error': 'Unauthorized'}), 403
        
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # 确保表存在（虽然 server 启动时会初始化，这里作为双重保险）
        if current_app.config['DB_TYPE'] == 'postgres':
             cursor.execute("CREATE TABLE IF NOT EXISTS admins (id SERIAL PRIMARY KEY, username TEXT UNIQUE, password_hash TEXT, created_at INTEGER)")
        else:
             cursor.execute("CREATE TABLE IF NOT EXISTS admins (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password_hash TEXT, created_at INTEGER)")
             
        cursor.execute("INSERT INTO admins (username, password_hash, created_at) VALUES (?, ?, ?)", 
                       (username, hashed, int(time.time())))
        conn.commit()
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 400
        
    conn.close()
    return jsonify({'status': 'success'})
