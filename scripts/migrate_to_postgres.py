import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import sqlite3
import psycopg2
from psycopg2.extras import execute_values
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os
from app.core.config import Config

# PostgreSQL 配置
PG_HOST = Config.PG_HOST
PG_PORT = Config.PG_PORT
PG_USER = Config.PG_USER
PG_PASSWORD = Config.PG_PASSWORD
PG_DB = Config.PG_DB

def get_sqlite_conn():
    return sqlite3.connect(Config.DB_PATH)

def create_database_if_not_exists():
    try:
        # Connect to default 'postgres' database to create new db
        conn = psycopg2.connect(
            host=PG_HOST,
            port=PG_PORT,
            user=PG_USER,
            password=PG_PASSWORD,
            dbname="postgres"
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Check if database exists
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (PG_DB,))
        exists = cursor.fetchone()
        
        if not exists:
            print(f"创建数据库 {PG_DB}...")
            cursor.execute(f"CREATE DATABASE {PG_DB}")
            print(f"数据库 {PG_DB} 创建成功")
        else:
            print(f"数据库 {PG_DB} 已存在")
            
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"检查/创建数据库失败: {e}")
        # We continue, maybe it already exists or we can't create it but can access it

def get_pg_conn():
    return psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        user=PG_USER,
        password=PG_PASSWORD,
        dbname=PG_DB
    )

def create_pg_tables(pg_conn):
    cursor = pg_conn.cursor()
    
    # 1. positions 表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS positions (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        requirements TEXT NOT NULL,
        responsibilities TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        status TEXT NOT NULL,
        created_at INTEGER NOT NULL,
        recruiter TEXT NOT NULL
    );
    """)
    
    # 2. candidates 表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS candidates (
        id SERIAL PRIMARY KEY,
        position_id INTEGER NOT NULL REFERENCES positions(id),
        name TEXT NOT NULL,
        email TEXT NOT NULL,
        resume_content BYTEA
    );
    """)
    
    # 3. interviews 表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS interviews (
        id SERIAL PRIMARY KEY,
        candidate_id INTEGER NOT NULL REFERENCES candidates(id),
        interviewer TEXT NOT NULL,
        start_time INTEGER NOT NULL,
        status INTEGER NOT NULL DEFAULT 0,
        is_passed INTEGER NOT NULL DEFAULT 0,
        token TEXT,
        report_content BYTEA,
        question_count INTEGER DEFAULT 0,
        voice_reading INTEGER DEFAULT 0
    );
    """)
    
    # 4. interview_questions 表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS interview_questions (
        id SERIAL PRIMARY KEY,
        interview_id INTEGER NOT NULL REFERENCES interviews(id),
        question TEXT NOT NULL,
        score_standard TEXT,
        answer_audio BYTEA,
        answer_text TEXT,
        answered_at INTEGER,
        score INTEGER,
        comments TEXT
    );
    """)
    
    pg_conn.commit()
    print("PostgreSQL 表结构创建完成")

def migrate_data():
    sqlite_conn = get_sqlite_conn()
    sqlite_cursor = sqlite_conn.cursor()
    
    pg_conn = get_pg_conn()
    pg_cursor = pg_conn.cursor()
    
    try:
        # 1. 迁移 positions
        print("迁移 positions...")
        sqlite_cursor.execute("SELECT * FROM positions")
        rows = sqlite_cursor.fetchall()
        if rows:
            cols = [description[0] for description in sqlite_cursor.description]
            columns = ','.join(cols)
            # 使用 execute_values 批量插入
            insert_query = f"INSERT INTO positions ({columns}) VALUES %s ON CONFLICT (id) DO NOTHING"
            execute_values(pg_cursor, insert_query, rows)
            
            # 更新 sequence
            pg_cursor.execute(f"SELECT setval('positions_id_seq', (SELECT MAX(id) FROM positions));")
        
        # 2. 迁移 candidates
        print("迁移 candidates...")
        sqlite_cursor.execute("SELECT * FROM candidates")
        rows = sqlite_cursor.fetchall()
        if rows:
             cols = [description[0] for description in sqlite_cursor.description]
             columns = ','.join(cols)
             insert_query = f"INSERT INTO candidates ({columns}) VALUES %s ON CONFLICT (id) DO NOTHING"
             execute_values(pg_cursor, insert_query, rows)
             pg_cursor.execute(f"SELECT setval('candidates_id_seq', (SELECT MAX(id) FROM candidates));")

        # 3. 迁移 interviews
        print("迁移 interviews...")
        sqlite_cursor.execute("SELECT * FROM interviews")
        rows = sqlite_cursor.fetchall()
        if rows:
             cols = [description[0] for description in sqlite_cursor.description]
             columns = ','.join(cols)
             insert_query = f"INSERT INTO interviews ({columns}) VALUES %s ON CONFLICT (id) DO NOTHING"
             execute_values(pg_cursor, insert_query, rows)
             pg_cursor.execute(f"SELECT setval('interviews_id_seq', (SELECT MAX(id) FROM interviews));")

        # 4. 迁移 interview_questions
        print("迁移 interview_questions...")
        sqlite_cursor.execute("SELECT * FROM interview_questions")
        rows = sqlite_cursor.fetchall()
        if rows:
             cols = [description[0] for description in sqlite_cursor.description]
             columns = ','.join(cols)
             insert_query = f"INSERT INTO interview_questions ({columns}) VALUES %s ON CONFLICT (id) DO NOTHING"
             execute_values(pg_cursor, insert_query, rows)
             pg_cursor.execute(f"SELECT setval('interview_questions_id_seq', (SELECT MAX(id) FROM interview_questions));")
        
        pg_conn.commit()
        print("数据迁移成功！")
        
    except Exception as e:
        pg_conn.rollback()
        print(f"迁移失败: {e}")
    finally:
        sqlite_conn.close()
        pg_conn.close()

if __name__ == "__main__":
    # 在运行前，请确保设置了环境变量或修改了上面的配置
    # 简单测试连接
    try:
        # First ensure database exists
        create_database_if_not_exists()
        
        conn = get_pg_conn()
        print("PostgreSQL 连接成功")
        create_pg_tables(conn)
        migrate_data()
        conn.close()
    except Exception as e:
        print(f"连接或迁移错误: {e}")
