import os
import logging
from logging.handlers import RotatingFileHandler

# 创建日志目录
# app/core/logger.py -> app/core -> app -> project -> logs
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'logs')
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

def setup_logger(name, log_file, level=logging.INFO):
    """Function to setup as many loggers as you want"""
    formatter = logging.Formatter('%(asctime)s %(levelname)s [%(name)s] %(message)s')

    handler = RotatingFileHandler(os.path.join(LOG_DIR, log_file), maxBytes=10*1024*1024, backupCount=5)
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 避免重复添加 handler
    if not logger.handlers:
        logger.addHandler(handler)
        
        # 同时输出到控制台
        console = logging.StreamHandler()
        console.setFormatter(formatter)
        logger.addHandler(console)

    return logger

# 预定义 logger
server_logger = setup_logger('server', 'server.log')
question_logger = setup_logger('question_gen', 'question_gen.log')
report_logger = setup_logger('report_gen', 'report_gen.log')
