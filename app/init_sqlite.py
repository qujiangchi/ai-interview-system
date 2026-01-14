import sqlite3
from config import Config
import os

def init_sqlite_db():
    print(f"初始化 SQLite 数据库: {Config.DB_PATH}")
    conn = sqlite3.connect(Config.DB_PATH)
    cursor = conn.cursor()
    
    # 1. positions 表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS positions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
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
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        position_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        email TEXT NOT NULL,
        resume_content BLOB,
        FOREIGN KEY(position_id) REFERENCES positions(id)
    );
    """)
    
    # 3. interviews 表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS interviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        candidate_id INTEGER NOT NULL,
        interviewer TEXT NOT NULL,
        start_time INTEGER NOT NULL,
        status INTEGER NOT NULL DEFAULT 0,
        is_passed INTEGER NOT NULL DEFAULT 0,
        token TEXT,
        report_content BLOB,
        question_count INTEGER DEFAULT 0,
        voice_reading INTEGER DEFAULT 0,
        FOREIGN KEY(candidate_id) REFERENCES candidates(id)
    );
    """)
    
    # 4. interview_questions 表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS interview_questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        interview_id INTEGER NOT NULL,
        question TEXT NOT NULL,
        score_standard TEXT,
        answer_audio BLOB,
        answer_text TEXT,
        answered_at INTEGER,
        score INTEGER,
        comments TEXT,
        FOREIGN KEY(interview_id) REFERENCES interviews(id)
    );
    """)
    
    conn.commit()
    conn.close()
    print("SQLite 数据库初始化完成")

if __name__ == "__main__":
    init_sqlite_db()
