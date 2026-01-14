"""
AI Intelligent Interview System - Application Entry Point
AI智能面试系统 - 应用入口文件

此模块作为整个后端应用的启动入口，负责初始化数据库、配置日志、
创建Flask应用实例，并启动开发服务器。

Usage:
    python app/server.py
"""

from app.api import create_app
from app.core.database import init_db
from app.core.config import Config
import logging

# 配置全局日志格式
# Configure global logging format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s [%(name)s] %(message)s'
)
logger = logging.getLogger('server')

# 初始化数据库（如果表不存在则创建，并检查连接）
# Initialize DB (create tables if not exist and check connection)
logger.info("Initializing database...")
init_db()
logger.info("Database initialized successfully.")

# 创建 Flask 应用实例
# Create Flask application instance
app = create_app()

if __name__ == '__main__':
    # 启动应用
    # Start the application
    # 注意：debug模式仅用于开发环境
    # Note: debug mode should only be used in development
    logger.info(f"Starting server on port 8000 (Debug={Config.DEBUG})...")
    app.run(debug=Config.DEBUG, host='0.0.0.0', port=8000)
