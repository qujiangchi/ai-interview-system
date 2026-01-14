import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from config import Config
import logging

logger = logging.getLogger('server')

class DBConnection:
    def __init__(self):
        self.db_type = Config.DB_TYPE
        self.conn = None
        
    def __enter__(self):
        if self.db_type == 'postgres':
            try:
                self.conn = psycopg2.connect(
                    host=Config.PG_HOST,
                    port=Config.PG_PORT,
                    user=Config.PG_USER,
                    password=Config.PG_PASSWORD,
                    dbname=Config.PG_DB
                )
                return self.conn
            except Exception as e:
                logger.error(f"PostgreSQL Connection Error: {e}")
                raise e
        else:
            # SQLite (Fallback)
            self.conn = sqlite3.connect(Config.DB_PATH)
            self.conn.row_factory = sqlite3.Row
            return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()

def get_db_connection():
    """
    获取数据库连接
    注意: 返回的连接对象在使用方式上略有不同 (SQLite vs PG)
    为了兼容现有的代码(主要使用 cursor.execute(?, ?))，
    我们需要做一个适配层，或者修改 SQL 语句的占位符。
    PostgreSQL 使用 %s，SQLite 使用 ?
    """
    if Config.DB_TYPE == 'postgres':
        conn = psycopg2.connect(
            host=Config.PG_HOST,
            port=Config.PG_PORT,
            user=Config.PG_USER,
            password=Config.PG_PASSWORD,
            dbname=Config.PG_DB,
            cursor_factory=RealDictCursor
        )
        return PGConnectionAdapter(conn)
    else:
        conn = sqlite3.connect(Config.DB_PATH)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute('PRAGMA journal_mode=WAL;')
        except:
            pass
        return conn

class PGConnectionAdapter:
    """适配器：让 PG 连接表现得像 SQLite 连接，主要是处理占位符差异"""
    def __init__(self, pg_conn):
        self.conn = pg_conn
        
    def cursor(self):
        return PGCursorAdapter(self.conn.cursor())
        
    def execute(self, sql, params=None):
        cursor = self.cursor()
        cursor.execute(sql, params)
        return cursor

    def commit(self):
        self.conn.commit()
        
    def close(self):
        self.conn.close()

class PGCursorAdapter:
    def __init__(self, pg_cursor):
        self.cursor = pg_cursor
        
    def execute(self, sql, params=None):
        # 将 SQLite 的 ? 占位符转换为 PG 的 %s
        pg_sql = sql.replace('?', '%s')
        
        # 记录日志以便调试 SQL 转换
        # logging.debug(f"SQL Transformed: {sql} -> {pg_sql} with params: {params}")
        
        try:
            return self.cursor.execute(pg_sql, params)
        except Exception as e:
            logging.error(f"SQL Execution Error: {e}, SQL: {pg_sql}, Params: {params}")
            raise e
            
    def fetchall(self):
        return self.cursor.fetchall()
        
    def fetchone(self):
        return self.cursor.fetchone()
        
    @property
    def description(self):
        return self.cursor.description
    
    @property
    def rowcount(self):
        return self.cursor.rowcount

def init_db():
    """初始化数据库表结构 (兼容 PG 和 SQLite)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 检查表是否存在
    if Config.DB_TYPE == 'postgres':
        # PG 初始化逻辑通常在外部完成 (create_pg_tables)，这里只做检查
        pass
    else:
        # SQLite 初始化逻辑 (保持不变)
        pass
    
    conn.close()
