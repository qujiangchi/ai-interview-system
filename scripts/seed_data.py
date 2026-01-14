import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import psycopg2
import time
from app.core.config import Config
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=Config.PG_HOST,
            port=Config.PG_PORT,
            user=Config.PG_USER,
            password=Config.PG_PASSWORD,
            dbname=Config.PG_DB
        )
        return conn
    except Exception as e:
        logger.error(f"无法连接到数据库: {e}")
        return None

def seed_data():
    conn = get_db_connection()
    if not conn:
        return

    cursor = conn.cursor()

    try:
        logger.info("开始填充模拟数据...")

        # 1. 插入职位 (Positions)
        positions_data = [
            ("高级 Python 后端工程师", "精通 Python, Flask/Django, PostgreSQL", "负责核心业务系统的后端开发与维护", 2, "open", "HR_Alice"),
            ("前端开发工程师 (React)", "精通 React, TypeScript, Tailwind CSS", "负责公司产品的前端页面开发", 1, "open", "HR_Bob"),
            ("AI 算法工程师", "熟悉 PyTorch/TensorFlow, NLP, LLM", "负责大模型应用的落地与优化", 3, "open", "HR_Charlie")
        ]
        
        logger.info("插入职位数据...")
        for p in positions_data:
            cursor.execute("""
                INSERT INTO positions (name, requirements, responsibilities, quantity, status, created_at, recruiter)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id;
            """, (p[0], p[1], p[2], p[3], p[4], int(time.time()), p[5]))
        
        # 获取刚才插入的职位ID（为了简化，这里重新查询一下，或者直接假设ID）
        # 在实际脚本中，最好使用 RETURNING id
        # 这里为了演示，我们先提交一次
        conn.commit()
        
        cursor.execute("SELECT id FROM positions WHERE name = %s", ("高级 Python 后端工程师",))
        py_position_id = cursor.fetchone()[0]
        
        cursor.execute("SELECT id FROM positions WHERE name = %s", ("前端开发工程师 (React)",))
        fe_position_id = cursor.fetchone()[0]

        # 2. 插入候选人 (Candidates)
        # 模拟一个空的 PDF 内容 (bytea)
        mock_resume_content = b"%PDF-1.4 Mock Resume Content..."
        
        candidates_data = [
            (py_position_id, "张三", "zhangsan@example.com"),
            (py_position_id, "李四", "lisi@example.com"),
            (fe_position_id, "王五", "wangwu@example.com")
        ]
        
        logger.info("插入候选人数据...")
        candidate_ids = []
        for c in candidates_data:
            cursor.execute("""
                INSERT INTO candidates (position_id, name, email, resume_content)
                VALUES (%s, %s, %s, %s)
                RETURNING id;
            """, (c[0], c[1], c[2], mock_resume_content))
            candidate_ids.append(cursor.fetchone()[0])

        # 3. 插入面试记录 (Interviews)
        # 使用第一个候选人 (张三) 创建一个面试
        interview_candidate_id = candidate_ids[0]
        interview_token = "mock_token_123456789"
        
        logger.info("插入面试记录...")
        cursor.execute("""
            INSERT INTO interviews (candidate_id, interviewer, start_time, status, is_passed, token, question_count, voice_reading)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id;
        """, (interview_candidate_id, "面试官_David", int(time.time()), 1, 0, interview_token, 3, 0))
        interview_id = cursor.fetchone()[0]

        # 4. 插入面试问题 (Interview Questions)
        questions_data = [
            ("请简述 Python 中 GIL 的概念及其对多线程的影响。", "准确解释 GIL，说明 CPU 密集型和 IO 密集型场景的区别"),
            ("什么是 RESTful API？请举例说明。", "理解资源、HTTP 方法、状态码"),
            ("如何在 PostgreSQL 中优化慢查询？", "提及 Explain, 索引, 配置优化等")
        ]
        
        logger.info("插入面试问题...")
        for q in questions_data:
            cursor.execute("""
                INSERT INTO interview_questions (interview_id, question, score_standard)
                VALUES (%s, %s, %s)
            """, (interview_id, q[0], q[1]))

        conn.commit()
        logger.info("✅ 模拟数据填充成功！")

    except Exception as e:
        conn.rollback()
        logger.error(f"❌ 数据填充失败: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    seed_data()
