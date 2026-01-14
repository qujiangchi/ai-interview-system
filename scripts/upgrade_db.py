import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.core.database import get_db_connection
from app.core.config import Config
import time

def upgrade_db():
    print(f"Upgrading database (Type: {Config.DB_TYPE})...")
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if Config.DB_TYPE == 'postgres':
        sql = """
        CREATE TABLE IF NOT EXISTS admins (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at INTEGER NOT NULL
        );
        """
    else:
        sql = """
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at INTEGER NOT NULL
        );
        """
        
    try:
        cursor.execute(sql)
        conn.commit()
        print("Admins table created or already exists.")
    except Exception as e:
        print(f"Error creating admins table: {e}")
        
    conn.close()

if __name__ == "__main__":
    upgrade_db()
