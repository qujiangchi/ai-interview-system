import os
import sys
import random
from datetime import datetime
from weasyprint import HTML
from app.core.database import get_db_connection
from app.core.config import Config

# Ensure app is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def generate_resume_pdf(name, role, experience, skills, education, output_path):
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: sans-serif; line-height: 1.6; color: #333; }}
            h1 {{ color: #2c3e50; border-bottom: 2px solid #2c3e50; padding-bottom: 10px; }}
            h2 {{ color: #34495e; margin-top: 20px; border-left: 4px solid #3498db; padding-left: 10px; }}
            .header {{ margin-bottom: 30px; }}
            .section {{ margin-bottom: 20px; }}
            .item {{ margin-bottom: 15px; }}
            .item-title {{ font-weight: bold; font-size: 1.1em; }}
            .item-meta {{ color: #7f8c8d; font-size: 0.9em; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>{name}</h1>
            <p>应聘职位: {role} | 工作经验: {experience}</p>
            <p>Email: {name.lower().replace(" ", ".")}@example.com | Tel: 13800138000</p>
        </div>

        <div class="section">
            <h2>专业技能</h2>
            <p>{skills}</p>
        </div>

        <div class="section">
            <h2>工作经历</h2>
            <div class="item">
                <div class="item-title">高级{role}</div>
                <div class="item-meta">2020 - 至今 | 某知名科技公司</div>
                <p>负责核心业务系统的架构设计与开发，主导了微服务改造，提升系统吞吐量 50%。</p>
            </div>
            <div class="item">
                <div class="item-title">{role}</div>
                <div class="item-meta">2017 - 2020 | 某创业公司</div>
                <p>参与产品从0到1的研发过程，负责后端API设计与实现。</p>
            </div>
        </div>

        <div class="section">
            <h2>教育背景</h2>
            <div class="item">
                <div class="item-title">{education}</div>
                <div class="item-meta">2013 - 2017 | 计算机科学与技术 | 本科</div>
            </div>
        </div>
    </body>
    </html>
    """
    HTML(string=html_content).write_pdf(output_path)
    return output_path

def seed_data():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Clear existing data (Optional, be careful in prod)
    # cursor.execute("DELETE FROM interview_questions")
    # cursor.execute("DELETE FROM interviews")
    # cursor.execute("DELETE FROM candidates")
    # cursor.execute("DELETE FROM positions")

    # 1. Create Positions
    positions = [
        {
            "name": "高级Python后端工程师",
            "requirements": "精通Python，熟悉Django/Flask/FastAPI框架；熟悉MySQL/Redis/MongoDB；有微服务架构经验；熟悉Docker/K8s。",
            "responsibilities": "1. 负责后端核心服务的设计与开发；2. 优化系统性能，解决高并发问题；3. 指导初级工程师。",
            "quantity": 3,
            "status": 1,
            "recruiter": "HR-Alice"
        },
        {
            "name": "资深数据科学家",
            "requirements": "数学/统计/计算机相关专业硕士及以上；精通机器学习/深度学习算法；熟练使用TensorFlow/PyTorch；有NLP或CV项目经验。",
            "responsibilities": "1. 构建和优化推荐系统算法；2. 负责AI模型在业务场景的落地；3. 探索前沿技术。",
            "quantity": 1,
            "status": 1,
            "recruiter": "HR-Bob"
        },
        {
            "name": "前端技术专家",
            "requirements": "精通JavaScript/TypeScript；深入理解React/Vue原理；熟悉前端工程化；有大型前端架构经验。",
            "responsibilities": "1. 负责前端基础设施建设；2. 解决复杂的前端技术难题；3. 提升用户体验。",
            "quantity": 2,
            "status": 1,
            "recruiter": "HR-Alice"
        }
    ]

    position_ids = []
    print("Creating Positions...")
    for p in positions:
        cursor.execute('''
            INSERT INTO positions (name, requirements, responsibilities, quantity, status, created_at, recruiter)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (p['name'], p['requirements'], p['responsibilities'], p['quantity'], p['status'], int(datetime.now().timestamp()), p['recruiter']))
        # Get ID
        if Config.DB_TYPE == 'postgres':
            # For postgres we need RETURNING id, but let's just query back for simplicity or assume sequential if clean
            # cursor.execute("SELECT currval(pg_get_serial_sequence('positions','id'))")
             # A robust way is to select max id
            pass 
        else:
             position_ids.append(cursor.lastrowid)

    # Re-fetch ids
    cursor.execute("SELECT id, name FROM positions ORDER BY id DESC LIMIT 3")
    db_positions = cursor.fetchall() # [(id, name), ...]
    
    # 2. Create Candidates & Resumes
    candidates_data = [
        {
            "name": "李明",
            "role": "Python开发",
            "pos_keyword": "Python",
            "skills": "Python, Django, Flask, MySQL, Redis, Docker, AWS",
            "exp": "5年",
            "edu": "浙江大学"
        },
        {
            "name": "Sarah Jones",
            "role": "Data Scientist",
            "pos_keyword": "数据",
            "skills": "Python, PyTorch, TensorFlow, Scikit-learn, SQL, Hadoop",
            "exp": "4年",
            "edu": "Stanford University (Master)"
        },
        {
            "name": "张伟",
            "role": "Frontend Lead",
            "pos_keyword": "前端",
            "skills": "JavaScript, TypeScript, React, Vue.js, Webpack, Node.js",
            "exp": "6年",
            "edu": "上海交通大学"
        }
    ]

    print("Creating Candidates and Resumes...")
    for c in candidates_data:
        # Match position
        target_pos_id = None
        for pid in db_positions:
             # Handle row object (sqlite) or dict (postgres adapter)
             p_name = pid['name'] if isinstance(pid, dict) or hasattr(pid, '__getitem__') else pid[1]
             p_id = pid['id'] if isinstance(pid, dict) or hasattr(pid, '__getitem__') else pid[0]
             
             if c['pos_keyword'] in p_name:
                 target_pos_id = p_id
                 break
        
        if not target_pos_id:
            continue

        # Generate PDF
        resume_filename = f"{c['name']}_{c['role']}.pdf"
        resume_path = os.path.join(Config.PROJECT_ROOT, 'data', 'resumes', resume_filename)
        generate_resume_pdf(c['name'], c['role'], c['exp'], c['skills'], c['edu'], resume_path)
        
        with open(resume_path, 'rb') as f:
            resume_content = f.read()

        # Insert Candidate
        if Config.DB_TYPE == 'sqlite':
            import sqlite3
            resume_val = sqlite3.Binary(resume_content)
        else:
            resume_val = resume_content

        cursor.execute('''
            INSERT INTO candidates (position_id, name, email, resume_content)
            VALUES (?, ?, ?, ?)
        ''', (target_pos_id, c['name'], f"{c['name'].lower().replace(' ', '.')}@example.com", resume_val))

    conn.commit()
    conn.close()
    print("Seed data generation completed.")

if __name__ == "__main__":
    seed_data()
