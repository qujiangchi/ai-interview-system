import os
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

class Config:
    # 基础路径
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DB_PATH = os.path.join(os.path.dirname(BASE_DIR), 'interview_system.db')
    
    # 数据库类型: 'sqlite' or 'postgres'
    DB_TYPE = os.getenv("DB_TYPE", "postgres")
    
    # PostgreSQL 配置
    PG_HOST = os.getenv("PG_HOST")
    PG_PORT = os.getenv("PG_PORT")
    PG_DB = os.getenv("PG_DB")
    PG_USER = os.getenv("PG_USER")
    PG_PASSWORD = os.getenv("PG_PASSWORD")
    
    # OpenAI / LLM 配置
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")
    LLM_MODEL = os.getenv("LLM_MODEL", "qwen-plus") # 默认使用 qwen-plus
    
    # Flask 配置
    SECRET_KEY = os.getenv("SECRET_KEY")
    ADMIN_INIT_SECRET = os.getenv("ADMIN_INIT_SECRET")
    DEBUG = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    
    # 静态文件
    STATIC_FOLDER = 'static'
    
    # Whisper 配置
    WHISPER_MODEL_SIZE = "tiny" # base, small, medium, large-v3
