import time
import schedule
from jinja2 import Environment
from weasyprint import HTML
import json
from datetime import datetime
from openai import OpenAI
import os

from config import Config
from logger import report_logger as logger
from database import get_db_connection

# 初始化OpenAI客户端
client = OpenAI(
    api_key=Config.OPENAI_API_KEY,
    base_url=Config.OPENAI_BASE_URL
)

# Report storage configuration
REPORT_BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'reports')

def ensure_report_dir():
    if not os.path.exists(REPORT_BASE_DIR):
        os.makedirs(REPORT_BASE_DIR)

def get_report_path(interview_id, candidate_name):
    date_str = datetime.now().strftime('%Y-%m-%d')
    date_dir = os.path.join(REPORT_BASE_DIR, date_str)
    if not os.path.exists(date_dir):
        os.makedirs(date_dir)
    
    # Sanitize filename
    safe_name = "".join([c for c in candidate_name if c.isalpha() or c.isdigit() or c==' ']).strip()
    filename = f"{interview_id}_{safe_name}_report.pdf"
    return os.path.join(date_dir, filename)

def fetch_interviews_with_status_3():
    """Fetch all interviews with status = 3 (interview completed)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT * FROM interviews WHERE status = 3
    ''')
    
    interviews = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return interviews

def fetch_interview_by_id(interview_id):
    """Fetch interview by ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT * FROM interviews WHERE id = ?
    ''', (interview_id,))
    
    row = cursor.fetchone()
    interview = dict(row) if row else None
    conn.close()
    return interview

def fetch_candidate_info(candidate_id):
    """Fetch candidate information by candidate_id"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT * FROM candidates WHERE id = ?
    ''', (candidate_id,))
    
    row = cursor.fetchone()
    candidate = dict(row) if row else None
    conn.close()
    return candidate

def fetch_position_info(position_id):
    """Fetch position information by position_id"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT * FROM positions WHERE id = ?
    ''', (position_id,))
    
    row = cursor.fetchone()
    position = dict(row) if row else None
    conn.close()
    return position

def fetch_interview_questions(interview_id):
    """Fetch all questions and answers for a specific interview"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT * FROM interview_questions WHERE interview_id = ?
    ''', (interview_id,))
    
    questions = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return questions

def call_ai_model(candidate_name, position_name, interviewer, questions):
        """
        调用OpenAI API生成面试报告
        """
        # 构建发送给OpenAI的提示内容
        prompt = f"""
        你是一位专业的面试评估专家，需要对候选人"{candidate_name}"应聘"{position_name}"职位的面试表现进行评估。
        面试官是{interviewer}。
        
        请根据以下面试问题、评分标准和候选人的回答，对每个问题进行评分和点评，并给出综合评价
        注意每个问题评分范围是0-100分，综合评分范围是0-100分
        
        """
        
        # 添加每个问题的详细信息
        for i, q in enumerate(questions, 1):
            prompt += f"""
        问题{i}: {q.get('question', '未提供问题')}
        评分标准: {q.get('score_standard', '未提供评分标准')}
        候选人回答: {q.get('answer_text', '未提供回答')}
        
        """
        
        prompt += """
        请以JSON格式返回评估结果，包含以下内容：
        1. 每个问题的评分和评价
        2. 技术能力总分(满分100)
        3. 沟通能力总分(满分100)
        4. 综合评分(满分100)
        5. 面试官评语(综合评价候选人的优缺点)
        6. 录用建议(推荐录用/可以考虑/不建议录用)
        
        JSON格式示例:
        {
            "question_evaluations": [
                {"id": 1, "question": "[question]", "score_standard": "[score_standard]", "answer": "[answer_text]", "score": 7, "comments": "回答详细，展示了扎实的基础知识..."},
                {"id": 2, "question": "[question]", "score_standard": "[score_standard]", "answer": "[answer_text]", "score": 9, "comments": "思路清晰，解决方案合理..."}
                ...
            ],
            "technical_score": 88,
            "communication_score": 90,
            "overall_score": 89,
            "comments": "候选人技术基础扎实，沟通能力强...",
            "recommendation": "推荐录用"
        }
        """
        
        try:
            # 调用大模型 API
            response = client.chat.completions.create(
                model=Config.LLM_MODEL,
                messages=[
                    {"role": "system", "content": "你是一位专业的面试评估专家，负责评估技术面试表现。"},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                stream = False
            )
            
            # 解析返回的JSON结果
            result_text = response.choices[0].message.content
            evaluation_result = json.loads(result_text)
            
            # Create model output similar to the example
            model_output = {
                "candidate_name": candidate_name,
                "position": position_name,
                "interview_date": datetime.now().strftime("%Y年%m月%d日"),
                "interviewer": interviewer,
                "evaluation_result": evaluation_result
            }
            
            return model_output
            
        except Exception as e:
            logger.error(f"调用AI模型时出错: {str(e)}")
            # 创建一个模拟的评估结果，以防API调用失败
            # 返回模拟数据
            model_output = {
                "candidate_name": candidate_name,
                "position": position_name,
                "interview_date": datetime.now().strftime("%Y年%m月%d日"),
                "interviewer": interviewer,
                "evaluation_result": {
                    "question_evaluations": [
                        {"id": 1, "question": "请介绍一下你的专业背景和技能（Mock）", "score_standard": "清晰度5分", "answer": "我是Mock回答", "score": 8, "comments": "回答尚可"},
                        {"id": 2, "question": "描述一个技术挑战（Mock）", "score_standard": "复杂度5分", "answer": "Mock回答2", "score": 9, "comments": "不错"}
                    ],
                    "technical_score": 85,
                    "communication_score": 90,
                    "overall_score": 88,
                    "comments": "这是一个由于API调用失败而生成的模拟报告。",
                    "recommendation": "推荐录用(Mock)"
                }
            }
            return model_output

def generate_pdf_report(model_output):
    """Generate PDF report using the template and model output"""
    # HTML template updated to match data structure from call_ai_model
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>面试报告</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .container { max-width: 800px; margin: auto; }
            .header { text-align: center; border-bottom: 2px solid #333; padding-bottom: 20px; }
            .section { margin-top: 20px; }
            .section h2 { color: #2c3e50; }
            .table { width: 100%; border-collapse: collapse; margin-top: 10px; }
            .table th, .table td { border: 1px solid #ddd; padding: 8px; text-align: left; }
            .table th { background-color: #f2f2f2; }
            .question-section { border: 1px solid #ddd; padding: 15px; margin-bottom: 15px; border-radius: 5px; }
            .question-title { font-weight: bold; color: #2c3e50; }
            .score { font-weight: bold; color: #e74c3c; }
            .footer { margin-top: 30px; text-align: center; color: #7f8c8d; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>面试报告</h1>
                <p>{{ interview_date }}</p>
            </div>
            <div class="section">
                <h2>候选人信息</h2>
                <table class="table">
                    <tr><th>姓名</th><td>{{ candidate_name }}</td></tr>
                    <tr><th>应聘职位</th><td>{{ position }}</td></tr>
                    <tr><th>面试官</th><td>{{ interviewer }}</td></tr>
                </table>
            </div>
            <div class="section">
                <h2>面试评估</h2>
                <table class="table">
                    <tr><th>技术能力</th><td>{{ evaluation_result.technical_score }}/100</td></tr>
                    <tr><th>沟通能力</th><td>{{ evaluation_result.communication_score }}/100</td></tr>
                    <tr><th>综合评分</th><td>{{ evaluation_result.overall_score }}/100</td></tr>
                </table>
            </div>
            <div class="section">
                <h2>面试官评语</h2>
                <p>{{ evaluation_result.comments }}</p>
            </div>
            <div class="section">
                <h2>推荐意见</h2>
                <p>{{ evaluation_result.recommendation }}</p>
            </div>
            
            <div class="section">
                <h2>问题评估详情</h2>
                {% for question in evaluation_result.question_evaluations %}
                <div class="question-section">
                    <p class="question-title">问题{{ question.id }}: {{ question.question }}</p>
                    <p><strong>评分标准:</strong> {{ question.score_standard }}</p>
                    <p><strong>候选人回答:</strong> {{ question.answer }}</p>
                    <p><strong>评分:</strong> <span class="score">{{ question.score }}/10</span></p>
                    <p><strong>点评:</strong> {{ question.comments }}</p>
                </div>
                {% endfor %}
            </div>
            
            <div class="footer">
                <p>Generated by xAI Interview System</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Initialize Jinja2 environment
    env = Environment()
    
    # Load template from string
    template = env.from_string(html_template)
    
    # Render template
    rendered_html = template.render(**model_output)
    
    # Convert to PDF bytes
    pdf_bytes = HTML(string=rendered_html).write_pdf()
    
    return pdf_bytes

def update_interview_report(interview_id, report_content, report_path=None):
    """Save the report content to the interview record and update status to 4"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if report_path column exists, if not create it (safe migration)
    try:
        cursor.execute("SELECT report_path FROM interviews LIMIT 1")
    except Exception:
        # SQLite
        try:
             cursor.execute("ALTER TABLE interviews ADD COLUMN report_path TEXT")
        except:
             # Postgres or already exists
             pass
        conn.commit()

    if Config.DB_TYPE == 'postgres':
        # psycopg2 handles bytes automatically
        cursor.execute('''
        UPDATE interviews 
        SET report_content = %s, report_path = %s, status = 4 
        WHERE id = %s
        ''', (report_content, report_path, interview_id))
    else:
        cursor.execute('''
        UPDATE interviews 
        SET report_content = ?, report_path = ?, status = 4 
        WHERE id = ?
        ''', (report_content, report_path, interview_id))
    
    conn.commit()
    conn.close()

def generate_report_for_interview(interview_id):
    """Generate report for a specific interview ID"""
    logger.info(f"Starting report generation for interview ID {interview_id}")
    try:
        # 1. Get interview info
        interview = fetch_interview_by_id(interview_id)
        if not interview:
            logger.error(f"Interview {interview_id} not found")
            return
            
        candidate_id = interview['candidate_id']
        interviewer = interview['interviewer']
        
        # 2. Get candidate information
        candidate = fetch_candidate_info(candidate_id)
        if not candidate:
            logger.error(f"Could not find candidate with ID {candidate_id}")
            return
        
        # 3. Get position information
        position = fetch_position_info(candidate['position_id'])
        if not position:
            logger.error(f"Could not find position with ID {candidate['position_id']}")
            return
        
        # 4. Get interview questions and answers
        questions = fetch_interview_questions(interview_id)
        
        # 5. Call AI model to generate report
        model_output = call_ai_model(
            candidate['name'],
            position['name'],
            interviewer,
            questions
        )
        
        # Generate PDF report
        pdf_bytes = generate_pdf_report(model_output)
        
        # Save to file
        report_path = get_report_path(interview_id, candidate['name'])
        with open(report_path, 'wb') as f:
            f.write(pdf_bytes)
        
        logger.info(f"Report saved to {report_path}")
        
        # 6. Save report to database (both blob and path)
        # 7. Update interview status to 4
        update_interview_report(interview_id, pdf_bytes, report_path)
        
        logger.info(f"Generated report for interview ID {interview_id}, candidate: {candidate['name']}")
        return True
        
    except Exception as e:
        logger.error(f"Error processing interview ID {interview_id}: {str(e)}")
        return False

def process_pending_reports():
    """Main function to process all interviews with status = 3"""
    logger.info("Checking for interviews that need reports...")
    
    # 1. Get all interviews with status = 3
    interviews = fetch_interviews_with_status_3()
    
    if not interviews:
        # logger.info("No interviews need reports at this time.")
        return
    
    logger.info(f"Found {len(interviews)} interviews that need reports.")
    
    for interview in interviews:
        generate_report_for_interview(interview['id'])

def run_scheduler():
    """Set up the scheduler to run the task every 5 minutes"""
    # Schedule the job to run every 5 minutes
    schedule.every(5).minutes.do(process_pending_reports)
    
    # Run the job once immediately when starting
    process_pending_reports()
    
    # Keep the script running
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    ensure_report_dir()
    logger.info("Starting interview report generation service...")
    run_scheduler()
