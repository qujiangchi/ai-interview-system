"""
Configuration Module
配置模块

此模块集中管理应用的所有配置项，从环境变量或默认值加载配置。
涵盖了路径配置、数据库配置、LLM模型配置、Flask配置等。
"""

import os
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量
load_dotenv()

class Config:
    """
    应用全局配置类
    Application Global Configuration Class
    """
    
    # === 路径配置 (Path Configuration) ===
    # __file__ is app/core/config.py
    # app/core
    CORE_DIR = os.path.dirname(os.path.abspath(__file__))
    # app
    APP_DIR = os.path.dirname(CORE_DIR)
    # project root
    PROJECT_ROOT = os.path.dirname(APP_DIR)
    
    # 保持兼容性，指向 app 目录
    BASE_DIR = APP_DIR 
    
    # === 数据库配置 (Database Configuration) ===
    # SQLite 数据库文件路径
    DB_PATH = os.path.join(PROJECT_ROOT, 'data', 'interview_system.db')
    
    # 数据库类型: 'sqlite' or 'postgres'
    # 优先使用 PostgreSQL，如果未配置则回退到 SQLite (在代码逻辑中处理)
    DB_TYPE = os.getenv("DB_TYPE", "postgres")
    
    # PostgreSQL 连接参数
    PG_HOST = os.getenv("PG_HOST")
    PG_PORT = os.getenv("PG_PORT")
    PG_DB = os.getenv("PG_DB")
    PG_USER = os.getenv("PG_USER")
    PG_PASSWORD = os.getenv("PG_PASSWORD")
    
    # === AI模型配置 (AI Model Configuration) ===
    # OpenAI API Key (用于调用大模型)
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    # OpenAI API Base URL (支持兼容 OpenAI 接口的其他服务商，如阿里云百炼)
    OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")
    # 使用的主要 LLM 模型名称
    LLM_MODEL = os.getenv("LLM_MODEL", "qwen-flash") 
    # 备选模型列表 (Fallback models if primary fails)
    # 包括: 'qwq-plus', 'qwen-vl-max', 'qwen-vl-max-latest', 'qvq-max', 'qvq-plus'
    
    # === Flask Web框架配置 (Flask Configuration) ===
    # 密钥，用于 Session 和 Token 加密
    SECRET_KEY = os.getenv("SECRET_KEY")
    # 管理员初始化密钥 (用于首次创建管理员账号)
    ADMIN_INIT_SECRET = os.getenv("ADMIN_INIT_SECRET")
    # 调试模式开关
    DEBUG = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    
    # 静态文件目录
    STATIC_FOLDER = os.path.join(APP_DIR, 'static')
    
    # === 语音识别配置 (Whisper Configuration) ===
    # Whisper 模型大小: tiny, base, small, medium, large-v3
    # 生产环境建议使用 small 或 medium，开发环境使用 tiny 以节省资源
    WHISPER_MODEL_SIZE = "tiny" 
