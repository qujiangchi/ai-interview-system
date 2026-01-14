"""
Report Generation Service
报告生成服务

此模块负责：
1. 从数据库获取面试数据
2. 调用 AI 模型 (OpenAI/Qwen) 生成评估结果
3. 使用 Jinja2 和 WeasyPrint 生成 PDF 报告
4. 管理报告文件存储和数据库更新
"""

import os
import time
from jinja2 import Environment
from weasyprint import HTML
import json
from datetime import datetime
from openai import OpenAI

from app.core.config import Config
from app.core.logger import report_logger as logger
from app.core.database import get_db_connection

# 初始化OpenAI客户端
client = OpenAI(
    api_key=Config.OPENAI_API_KEY,
    base_url=Config.OPENAI_BASE_URL
)

# Report storage configuration
# app/services/report_service.py -> app/services -> app -> project -> reports
REPORT_BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'reports')

def ensure_report_dir():
    """确保报告存储目录存在"""
    if not os.path.exists(REPORT_BASE_DIR):
        os.makedirs(REPORT_BASE_DIR)

def get_report_path(interview_id, candidate_name):
    """
    生成报告文件路径
    
    格式: reports/YYYY-MM-DD/{id}_{name}_report.pdf
    """
    date_str = datetime.now().strftime('%Y-%m-%d')
    date_dir = os.path.join(REPORT_BASE_DIR, date_str)
    if not os.path.exists(date_dir):
        os.makedirs(date_dir)
    
    # Sanitize filename (清理文件名中的非法字符)
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

def call_ai_model_for_question(question, answer, position_name):
    """
    Evaluate a single question using AI
    对单个问题的回答进行 AI 评分
    """
    prompt = f"""
    Evaluate this interview answer for position: {position_name}
    
    Question: {question.get('question')}
    Standard: {question.get('score_standard')}
    Answer: {answer}
    
    Return JSON:
    {{
        "score": (0-100),
        "comments": "evaluation text"
    }}
    """
    try:
        response = client.chat.completions.create(
            model=Config.LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        logger.error(f"Single question evaluation failed: {e}")
        return {"score": 0, "comments": "Evaluation failed"}

def evaluate_single_question(question_id):
    """
    Worker function to evaluate a single question and update DB
    后台任务：评估单个问题并更新数据库
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get question info
        cursor.execute('''
            SELECT iq.id, iq.interview_id, iq.question, iq.score_standard, iq.answer_text, 
                   c.position_id, p.name as position_name
            FROM interview_questions iq
            JOIN interviews i ON iq.interview_id = i.id
            JOIN candidates c ON i.candidate_id = c.id
            JOIN positions p ON c.position_id = p.id
            WHERE iq.id = ?
        ''', (question_id,))
        
        data = cursor.fetchone()
        if not data or not data['answer_text']:
            conn.close()
            return

        result = call_ai_model_for_question(data, data['answer_text'], data['position_name'])
        
        cursor.execute('''
            UPDATE interview_questions 
            SET ai_score = ?, ai_evaluation = ?
            WHERE id = ?
        ''', (result.get('score', 0), result.get('comments', ''), question_id))
        
        conn.commit()
        conn.close()
        logger.info(f"Evaluated question {question_id}: Score {result.get('score')}")
        
    except Exception as e:
        logger.error(f"Error evaluating question {question_id}: {e}")

def call_ai_model(candidate_name, position_name, interviewer, questions):
        """
        Modified to use existing evaluations if available
        调用 AI 模型生成整体面试报告
        """
        # Collect evaluations
        question_evals = []
        total_score = 0
        count = 0
        
        # If questions have pre-calculated scores, use them
        pre_evaluated = True
        for i, q in enumerate(questions, 1):
            if q.get('ai_evaluation'):
                question_evals.append({
                    "id": i,
                    "question": q['question'],
                    "score_standard": q['score_standard'],
                    "answer": q['answer_text'],
                    "score": q['ai_score'],
                    "comments": q['ai_evaluation']
                })
                total_score += q.get('ai_score', 0)
                count += 1
            else:
                pre_evaluated = False
                break
        
        if not pre_evaluated:
             # Fallback to full evaluation if not all questions are evaluated
             pass

        # If we have all evaluations, just generate summary
        if pre_evaluated and count > 0:
            prompt = f"""
            Generate a comprehensive interview report summary for:
            Candidate: {candidate_name}
            Position: {position_name}
            
            Based on the following Question Evaluations:
            {json.dumps(question_evals, ensure_ascii=False)}
            
            Please provide a professional, detailed evaluation. Do not leave any fields blank.
            
            Return JSON in the following format:
            {{
                "technical_score": (0-100),
                "technical_evaluation": "Detailed assessment of technical skills, depth of knowledge, and problem-solving abilities...",
                "communication_score": (0-100),
                "communication_evaluation": "Assessment of clarity, articulation, listening skills, and English proficiency (if applicable)...",
                "overall_score": (0-100),
                "overall_evaluation": "A comprehensive summary of the candidate's performance, fittingness for the role, and potential value...",
                "strengths": ["Strength 1", "Strength 2", ...],
                "weaknesses": ["Area for improvement 1", "Area for improvement 2", ...],
                "recommendation": "Strongly Hire / Hire / Weak Hire / No Hire",
                "recommendation_reason": "Brief justification for the recommendation..."
            }}
            """
            try:
                response = client.chat.completions.create(
                    model=Config.LLM_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}
                )
                summary = json.loads(response.choices[0].message.content)
                summary['question_evaluations'] = question_evals
                
                model_output = {
                    "candidate_name": candidate_name,
                    "position": position_name,
                    "interview_date": datetime.now().strftime("%Y年%m月%d日"),
                    "interviewer": interviewer,
                    "evaluation_result": summary
                }
                return model_output
            except Exception as e:
                logger.error(f"Summary generation failed: {e}")
                # Fallback
                return {
                    "candidate_name": candidate_name,
                    "position": position_name,
                    "interview_date": datetime.now().strftime("%Y年%m月%d日"),
                    "interviewer": interviewer,
                    "evaluation_result": {
                         "question_evaluations": question_evals,
                         "technical_score": int(total_score/count) if count else 0,
                         "technical_evaluation": "Evaluation generation failed.",
                         "communication_score": 80,
                         "communication_evaluation": "Evaluation generation failed.",
                         "overall_score": int(total_score/count) if count else 0,
                         "overall_evaluation": "Summary generation failed, showing raw scores.",
                         "strengths": ["N/A"],
                         "weaknesses": ["N/A"],
                         "recommendation": "Pending",
                         "recommendation_reason": "System error."
                    }
                }

        # Fallback to original big prompt if no pre-evaluations
        prompt = f"""
        你是一位资深的面试评估专家，请对候选人"{candidate_name}"应聘"{position_name}"职位的面试表现进行全方位的专业评估。
        面试官: {interviewer}
        
        请根据以下面试问答记录，生成一份详尽的面试评估报告。
        
        """
        
        # 添加每个问题的详细信息
        for i, q in enumerate(questions, 1):
            prompt += f"""
        问题{i}: {q.get('question', '未提供问题')}
        评分标准: {q.get('score_standard', '未提供评分标准')}
        候选人回答: {q.get('answer_text', '未提供回答')}
        
        """
        
        prompt += """
        请以JSON格式返回评估结果，必须包含以下所有字段，内容必须详实专业，不可为空：
        
        {
            "question_evaluations": [
                {"id": 1, "question": "...", "score_standard": "...", "answer": "...", "score": 85, "comments": "详细点评..."}
            ],
            "technical_score": (0-100),
            "technical_evaluation": "对候选人技术硬实力的深入分析，包括知识广度、深度及应用能力...",
            "communication_score": (0-100),
            "communication_evaluation": "对候选人沟通表达、逻辑思维及互动能力的评价...",
            "overall_score": (0-100),
            "overall_evaluation": "综合评价，总结候选人的整体表现、潜力及与岗位的匹配度...",
            "strengths": ["亮点1", "亮点2", "亮点3"],
            "weaknesses": ["不足1", "不足2"],
            "recommendation": "录用建议 (Strongly Hire / Hire / Weak Hire / No Hire)",
            "recommendation_reason": "给出具体的录用或拒绝理由..."
        }
        """
        
        try:
            # 调用大模型 API
            # Fallback logic for models
            models_to_try = [Config.LLM_MODEL, 'qwq-plus', 'qvq-plus', 'qvq-max']
            
            response = None
            last_error = None
            
            for model_name in models_to_try:
                try:
                    logger.info(f"Trying model: {model_name}")
                    response = client.chat.completions.create(
                        model=model_name,
                        messages=[
                            {"role": "system", "content": "你是一位专业的招聘面试官，你的评估报告将被用于最终的录用决策，请务必客观、专业、详尽。"},
                            {"role": "user", "content": prompt}
                        ],
                        response_format={"type": "json_object"},
                        stream = False
                    )
                    break # Success
                except Exception as e:
                    logger.warning(f"Model {model_name} failed: {e}")
                    last_error = e
                    continue
            
            if not response:
                raise last_error

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
                        {"id": 1, "question": "示例问题", "score_standard": "示例标准", "answer": "示例回答", "score": 0, "comments": "生成失败"}
                    ],
                    "technical_score": 0,
                    "technical_evaluation": "生成失败",
                    "communication_score": 0,
                    "communication_evaluation": "生成失败",
                    "overall_score": 0,
                    "overall_evaluation": "生成失败",
                    "strengths": [],
                    "weaknesses": [],
                    "recommendation": "Pending",
                    "recommendation_reason": "API Error"
                }
            }
            return model_output

def generate_pdf_report(model_output):
    """Generate PDF report using the template and model output"""
    # HTML template updated to match data structure from call_ai_model
    html_template = """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <title>面试评估报告</title>
        <style>
            @page {
                margin: 20mm;
                size: A4;
            }
            @font-face {
                font-family: 'SimSun';
                /* src: local('SimSun'); */
            }
            body { 
                /* Fallback fonts for WeasyPrint/Linux environment usually include WenQuanYi Micro Hei or similar */
                font-family: "WenQuanYi Micro Hei", "WenQuanYi Zen Hei", "SimHei", "SimSun", sans-serif; 
                color: #333;
                line-height: 1.6;
                font-size: 14px;
            }
            .container { width: 100%; max-width: 100%; }
            
            /* Header */
            .header {
                border-bottom: 2px solid #2c3e50;
                padding-bottom: 15px;
                margin-bottom: 30px;
                display: flex;
                justify-content: space-between;
                align-items: flex-end;
            }
            .header h1 {
                margin: 0;
                color: #2c3e50;
                font-size: 24px;
            }
            .header .meta {
                color: #7f8c8d;
                font-size: 12px;
            }
            
            /* Section Common */
            .section { margin-bottom: 30px; }
            .section-title {
                background-color: #f8f9fa;
                border-left: 5px solid #3498db;
                padding: 8px 15px;
                margin-bottom: 15px;
                color: #2c3e50;
                font-size: 16px;
                font-weight: bold;
                text-transform: uppercase;
            }
            
            /* Info Table */
            .info-grid {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 20px;
                margin-bottom: 20px;
            }
            .info-item {
                margin-bottom: 8px;
            }
            .info-label {
                font-weight: bold;
                color: #7f8c8d;
                width: 80px;
                display: inline-block;
            }
            
            /* Score Cards */
            .score-overview {
                display: flex;
                justify-content: space-between;
                background: #fdfdfd;
                border: 1px solid #eee;
                border-radius: 8px;
                padding: 20px;
                margin-bottom: 20px;
            }
            .score-card {
                text-align: center;
                flex: 1;
                border-right: 1px solid #eee;
            }
            .score-card:last-child { border-right: none; }
            .score-val {
                font-size: 28px;
                font-weight: bold;
                color: #3498db;
                display: block;
                padding: 10px;
            }
            .score-label {
                font-size: 12px;
                color: #95a5a6;
                text-transform: uppercase;
                margin-top: 5px;
            }
            .score-val.overall { color: #e74c3c; font-size: 36px; }
            
            /* Text Content */
            .content-block {
                text-align: justify;
                margin-bottom: 15px;
                background: #fff;
            }
            .subsection-title {
                font-weight: bold;
                color: #34495e;
                margin-bottom: 5px;
                margin-top: 10px;
            }
            
            /* Lists */
            .bullet-list {
                margin: 0;
                padding-left: 20px;
            }
            .bullet-list li {
                margin-bottom: 5px;
            }
            
            /* Questions */
            .question-item {
                background-color: #fff;
                border: 1px solid #eee;
                border-radius: 5px;
                padding: 15px;
                margin-bottom: 15px;
                page-break-inside: avoid;
            }
            .q-header {
                display: flex;
                justify-content: space-between;
                margin-bottom: 10px;
                border-bottom: 1px dashed #eee;
                padding-bottom: 8px;
            }
            .q-id { font-weight: bold; color: #2c3e50; }
            .q-score { 
                font-weight: bold; 
                color: #fff; 
                background: #3498db; 
                padding: 2px 8px; 
                border-radius: 4px; 
                font-size: 12px;
            }
            .q-content { margin-bottom: 10px; font-weight: 500; }
            .q-answer { 
                background: #f9f9f9; 
                padding: 10px; 
                border-left: 3px solid #ddd; 
                margin-bottom: 10px; 
                font-size: 13px;
                color: #555;
            }
            .q-comment {
                font-size: 13px;
                color: #27ae60;
            }
            
            /* Footer */
            .footer {
                margin-top: 40px;
                text-align: center;
                font-size: 10px;
                color: #bdc3c7;
                border-top: 1px solid #eee;
                padding-top: 10px;
            }
            
            /* Status Badge */
            .status-badge {
                display: inline-block;
                padding: 4px 12px;
                border-radius: 20px;
                font-weight: bold;
                font-size: 12px;
                text-transform: uppercase;
            }
            .status-hire { background: #e8f8f5; color: #27ae60; border: 1px solid #27ae60; }
            .status-no { background: #fdedec; color: #e74c3c; border: 1px solid #e74c3c; }
            
            .two-col {
                display: flex;
                gap: 20px;
            }
            .col { flex: 1; }
        </style>
    </head>
    <body>
        <div class="container">
            <!-- Header -->
            <div class="header">
                <div>
                    <h1>面试评估报告</h1>
                    <div class="meta">CONFIDENTIAL INTERVIEW REPORT</div>
                </div>
                <div style="text-align: right;">
                    <div style="font-weight: bold;">{{ interview_date }}</div>
                    <div class="meta">ID: #{{ evaluation_result.interview_id if evaluation_result.interview_id else 'N/A' }}</div>
                </div>
            </div>

            <!-- Candidate Info -->
            <div class="section">
                <div class="section-title">基本信息</div>
                <div class="info-grid" style="display: table; width: 100%;">
                    <div style="display: table-cell; width: 50%;">
                        <div class="info-item"><span class="info-label">候选人:</span> {{ candidate_name }}</div>
                        <div class="info-item"><span class="info-label">应聘职位:</span> {{ position }}</div>
                    </div>
                    <div style="display: table-cell; width: 50%;">
                        <div class="info-item"><span class="info-label">面试官:</span> {{ interviewer }}</div>
                        <div class="info-item"><span class="info-label">面试日期:</span> {{ interview_date }}</div>
                    </div>
                </div>
            </div>

            <!-- Score Overview -->
            <div class="section">
                <div class="section-title">评估概览</div>
                <div class="score-overview" style="display: table; width: 100%; padding: 0; border: none;">
                   <table style="width: 100%; border-spacing: 10px; border-collapse: separate;">
                       <tr>
                           <td style="background: #f8f9fa; padding: 15px; text-align: center; border-radius: 8px; width: 33%;">
                               <span class="score-val overall">{{ evaluation_result.overall_score }}</span>
                               <div class="score-label">综合得分</div>
                           </td>
                           <td style="background: #f8f9fa; padding: 15px; text-align: center; border-radius: 8px; width: 33%;">
                               <span class="score-val">{{ evaluation_result.technical_score }}</span>
                               <div class="score-label">技术能力</div>
                           </td>
                           <td style="background: #f8f9fa; padding: 15px; text-align: center; border-radius: 8px; width: 33%;">
                               <span class="score-val">{{ evaluation_result.communication_score }}</span>
                               <div class="score-label">沟通能力</div>
                           </td>
                       </tr>
                   </table>
                </div>
                
                <div class="content-block" style="background: #eef2f5; padding: 15px; border-radius: 5px; margin-top: 15px;">
                    <div style="font-weight: bold; margin-bottom: 5px;">录用建议: 
                        <span class="{{ 'status-hire' if 'Hire' in evaluation_result.recommendation else 'status-no' }} status-badge">
                            {{ evaluation_result.recommendation }}
                        </span>
                    </div>
                    <div>{{ evaluation_result.recommendation_reason }}</div>
                </div>
            </div>

            <!-- Detailed Evaluation -->
            <div class="section">
                <div class="section-title">综合评价</div>
                
                <div class="content-block">
                    <div class="subsection-title">总体表现</div>
                    <p>{{ evaluation_result.overall_evaluation }}</p>
                </div>
                
                <div class="two-col" style="display: table; width: 100%; border-spacing: 20px; margin-left: -20px;">
                     <div class="col" style="display: table-cell; width: 50%; vertical-align: top; padding-left: 20px;">
                        <div class="subsection-title">技术能力评价</div>
                        <p>{{ evaluation_result.technical_evaluation }}</p>
                     </div>
                     <div class="col" style="display: table-cell; width: 50%; vertical-align: top;">
                        <div class="subsection-title">沟通能力评价</div>
                        <p>{{ evaluation_result.communication_evaluation }}</p>
                     </div>
                </div>
            </div>
            
            <!-- Strengths & Weaknesses -->
             <div class="section">
                <div class="section-title">优势与不足</div>
                <div class="two-col" style="display: table; width: 100%; border-spacing: 20px; margin-left: -20px;">
                     <div class="col" style="display: table-cell; width: 50%; vertical-align: top; background: #f0fdf4; padding: 15px; border-radius: 8px; margin-left: 20px;">
                        <div class="subsection-title" style="color: #27ae60;">优势 (Strengths)</div>
                        <ul class="bullet-list">
                            {% for item in evaluation_result.strengths %}
                            <li>{{ item }}</li>
                            {% endfor %}
                        </ul>
                     </div>
                     <div class="col" style="display: table-cell; width: 50%; vertical-align: top; background: #fff5f5; padding: 15px; border-radius: 8px;">
                        <div class="subsection-title" style="color: #c0392b;">待改进 (Areas for Improvement)</div>
                        <ul class="bullet-list">
                            {% for item in evaluation_result.weaknesses %}
                            <li>{{ item }}</li>
                            {% endfor %}
                        </ul>
                     </div>
                </div>
            </div>

            <!-- Question Detail -->
            <div class="section">
                <div class="section-title">面试问答详情</div>
                {% for question in evaluation_result.question_evaluations %}
                <div class="question-item">
                    <div class="q-header">
                        <span class="q-id">Q{{ question.id }}</span>
                        <span class="q-score">{{ question.score }} 分</span>
                    </div>
                    <div class="q-content">{{ question.question }}</div>
                    
                    <div style="font-size: 12px; color: #7f8c8d; margin-bottom: 5px;">评分标准: {{ question.score_standard }}</div>
                    
                    <div class="q-answer">
                        <strong>回答:</strong> {{ question.answer }}
                    </div>
                    <div class="q-comment">
                        <strong>AI 点评:</strong> {{ question.comments }}
                    </div>
                </div>
                {% endfor %}
            </div>

            <div class="footer">
                <p>Generated by Trae Interview System | Date: {{ interview_date }}</p>
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
    try:
        pdf_bytes = HTML(string=rendered_html).write_pdf()
    except Exception as e:
        logger.error(f"Failed to generate PDF with WeasyPrint: {e}")
        # Fallback to simple HTML to PDF if fonts fail (or return error)
        # For now, let's try to return HTML as bytes if PDF fails? No, that breaks expectations.
        # We should try to use a default font config if possible.
        # Let's try to use 'serif' generic family as fallback in style
        html_template = html_template.replace('sans-serif;', 'serif;')
        template = env.from_string(html_template)
        rendered_html = template.render(**model_output)
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
        # SQLite or Postgres failure
        conn.rollback() # Important for Postgres
        try:
            cursor.execute("ALTER TABLE interviews ADD COLUMN report_path TEXT")
            conn.commit()
        except:
            # Postgres or already exists or other error
            conn.rollback()
            pass

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
