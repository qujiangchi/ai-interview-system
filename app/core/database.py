"""
Database Management Module
数据库管理模块

此模块负责处理数据库连接、SQL执行适配以及数据库初始化。
它实现了一个适配层，使得 PostgreSQL 可以使用类似 SQLite 的 API（特别是占位符处理），
从而实现代码的数据库无关性。
"""

import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from app.core.config import Config
import logging

logger = logging.getLogger('server')

class DBConnection:
    """
    数据库连接上下文管理器 (Context Manager)
    用于 with 语句中自动管理连接的获取和释放
    """
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
    获取数据库连接工厂函数
    Get Database Connection Factory Function
    
    返回一个数据库连接对象。如果是 PostgreSQL，返回一个适配器对象；
    如果是 SQLite，返回原生的 Connection 对象。
    
    Returns:
        Connection object or Adapter object
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
            # 启用 Write-Ahead Logging 模式以提高并发性能
            conn.execute('PRAGMA journal_mode=WAL;')
        except:
            pass
        return conn

class PGConnectionAdapter:
    """
    PostgreSQL 连接适配器
    PostgreSQL Connection Adapter
    
    让 PG 连接表现得像 SQLite 连接，主要是为了统一接口。
    """
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
    """
    PostgreSQL 游标适配器
    PostgreSQL Cursor Adapter
    
    核心功能是将 SQLite 风格的 SQL（使用 ? 占位符）转换为 
    PostgreSQL 风格（使用 %s 占位符）。
    """
    def __init__(self, pg_cursor):
        self.cursor = pg_cursor
        
    def execute(self, sql, params=None):
        # 将 SQLite 的 ? 占位符转换为 PG 的 %s
        # Convert SQLite '?' placeholder to PostgreSQL '%s'
        pg_sql = sql.replace('?', '%s')
        
        try:
            return self.cursor.execute(pg_sql, params)
        except Exception as e:
            # 记录详细的 SQL 执行错误日志
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
    
    @property
    def lastrowid(self):
        # PG does not support lastrowid directly like sqlite
        # Need RETURNING id in SQL or fetch back
        return None

def init_db():
    """
    初始化数据库表结构
    Initialize Database Schema
    
    连接数据库并执行初始化脚本（如果需要）。
    对于 SQLite，通常需要在此处创建表；
    对于 PostgreSQL，建议使用迁移工具（如 Alembic）或外部脚本。
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 检查表是否存在
    if Config.DB_TYPE == 'postgres':
        # PG 初始化逻辑通常在外部完成 (create_pg_tables)，这里只做检查
        # 实际生产环境建议检查 schema 版本表
        pass
    else:
        # SQLite 初始化逻辑 (保持不变，或在此处添加建表语句)
        # TODO: 将建表语句移至此处或独立的 schema.sql 文件
        pass
    
    conn.close()
