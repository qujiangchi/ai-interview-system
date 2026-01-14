"""
Interview Questions Generation Script
面试问题生成脚本

此脚本负责：
1. 定期检查尚未开始的面试任务
2. 从数据库中提取候选人简历和岗位要求
3. 调用 AI 大模型生成定制化的面试问题
4. 将生成的问题存入数据库，供面试环节使用

该脚本通常作为后台守护进程运行。
"""

import sys
import os
# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import schedule
import threading
import json
import io
from datetime import datetime
from openai import OpenAI
import PyPDF2
import logging

from app.core.config import Config
from app.core.logger import question_logger as logger
from app.core.database import get_db_connection

# 初始化OpenAI客户端
client = OpenAI(
    api_key=Config.OPENAI_API_KEY,
    base_url=Config.OPENAI_BASE_URL
)
    
def extract_text_from_pdf(pdf_content):
    """
    从PDF二进制数据中提取文本内容
    Extract text from PDF binary content
    
    Args:
        pdf_content (bytes): PDF文件二进制数据
        
    Returns:
        str: 提取的文本内容
    """
    try:
        # 如果输入是None或空值，返回空字符串
        if pdf_content is None or pdf_content == b'':
            return "无简历内容"
            
        # 创建BytesIO对象处理二进制数据
        pdf_file = io.BytesIO(pdf_content)
        
        # 创建PDF阅读器
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        
        # 提取所有页面的文本
        text = ""
        for page_num in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[page_num]
            text += page.extract_text() + "\n"
        
        # 如果没有提取到文本，尝试使用另一种方法
        if not text.strip():
            return "无法从PDF中提取文本内容"
            
        return text
    except Exception as e:
        logger.error(f"PDF文本提取错误: {str(e)}")
        # 如果pdf解析失败，尝试作为纯文本处理
        try:
            if isinstance(pdf_content, bytes):
                return pdf_content.decode('utf-8', errors='ignore')
            return str(pdf_content)
        except:
            return "无法解析简历内容"

def get_pending_interviews():
    """
    获取未开始的面试列表
    Fetch all pending interviews (status = 0)
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 获取所有状态为0(未开始)的面试
    cursor.execute('''
        SELECT i.id, i.candidate_id, i.interviewer, i.start_time
        FROM interviews i
        WHERE i.status = 0
    ''')
    
    interviews = cursor.fetchall()
    conn.close()
    return interviews

def get_candidate_info(candidate_id):
    """
    获取候选人信息
    Fetch candidate info by ID
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT c.id, c.name, c.email, c.resume_content, c.position_id
        FROM candidates c
        WHERE c.id = ?
    ''', (candidate_id,))
    
    candidate = cursor.fetchone()
    conn.close()
    return candidate

def get_position_info(position_id):
    """
    获取岗位信息
    Fetch position info by ID
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT p.id, p.name, p.requirements, p.responsibilities
        FROM positions p
        WHERE p.id = ?
    ''', (position_id,))
    
    position = cursor.fetchone()
    conn.close()
    return position

def generate_questions(resume_content, position_name, requirements, responsibilities):
    """
    根据简历内容和岗位信息生成面试问题
    Generate interview questions using LLM
    """
    # 解析简历内容 : 抽取pdf中resume_content的文本内容
    try:
        resume_text = extract_text_from_pdf(resume_content)
    except:
        resume_text = "无法解析简历内容"
    
    # 返回json格式参考
    json_format = [
         {"question": "请介绍一下你的专业背景和技能", "score_standard": "清晰度5分，相关性5分，深度5分"},
         {"question": "你认为自己最适合这个岗位的原因是什么？", "score_standard": "匹配度5分，自我认知5分，表达5分"},
         {"question": "描述一个你解决过的技术挑战", "score_standard": "复杂度5分，解决方案5分，结果5分"},
         {"question": "你如何看待团队合作？", "score_standard": "协作能力5分，沟通能力5分，角色意识5分"},
         {"question": "你对这个行业的未来趋势有什么看法？", "score_standard": "了解程度5分，前瞻性5分，分析能力5分"}
    ]
    # 调用OpenAI API生成面试问题
    try:
        response = client.chat.completions.create(
            #model="gpt-4", # 或其他适合的模型
            model=Config.LLM_MODEL,
            messages=[
                {"role": "system", "content": "你是一名专业的招聘面试官，请根据岗位要求和候选人简历生成5个针对性的技术面试问题，每个问题附带评分标准,返回标准的json格式。"},
                {"role": "user", "content": f"岗位名称: {position_name}\n岗位要求: {requirements}\n岗位职责: {responsibilities}\n候选人简历: {resume_text}\n\n请生成10个面试问题和评分标准，JSON格式参考 {json_format} ，每个问题满分10分。"}
            ],
            response_format={"type": "json_object"},
            stream = False
        )
        
        # 解析响应内容
        questions_json = response.choices[0].message.content
        questions = json.loads(questions_json)
        
        # 兼容不同格式的返回 (有时模型会返回 {'questions': [...]})
        if isinstance(questions, dict) and 'questions' in questions:
            questions = questions['questions']
            
        return questions

    except Exception as e:
        logger.error(f"生成面试问题时出错: {str(e)}")
        logger.info("使用Mock数据作为回退...")
        return [
            {"question": "请介绍一下你的专业背景和技能（Mock）", "score_standard": "清晰度5分，相关性5分，深度5分"},
            {"question": "你认为自己最适合这个岗位的原因是什么？（Mock）", "score_standard": "匹配度5分，自我认知5分，表达5分"},
            {"question": "描述一个你解决过的技术挑战（Mock）", "score_standard": "复杂度5分，解决方案5分，结果5分"}
        ]
 

def save_questions(interview_id, questions):
    """
    将生成的问题保存到数据库
    Save generated questions to DB
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    for question in questions:
        # 将score_standard转换为JSON字符串(如果是字典类型)
        score_standard = question.get('score_standard', '')
        if isinstance(score_standard, dict):
            score_standard = json.dumps(score_standard, ensure_ascii=False)
            
        cursor.execute('''
            INSERT INTO interview_questions (interview_id, question, score_standard)
            VALUES (?, ?, ?)
        ''', (interview_id, question.get('question'), score_standard))
    
    # 更新面试状态为"试题已备好"(1)
    cursor.execute('''
        UPDATE interviews SET status = 1 , question_count = ? WHERE id = ?
    ''', (len(questions), interview_id))
    
    conn.commit()
    conn.close()

def process_pending_interviews():
    """
    处理未开始的面试的主逻辑
    Main processing function
    """
    logger.info("开始处理未开始的面试...")
    
    # 获取所有未开始的面试
    pending_interviews = get_pending_interviews()
    
    if not pending_interviews:
        # logger.info("没有未开始的面试需要处理")
        return
    
    logger.info(f"找到 {len(pending_interviews)} 个待处理的面试")
    
    for interview in pending_interviews:
        # Check if interview is dict (Postgres) or Row (SQLite)
        if isinstance(interview, dict):
            interview_id = interview['id']
            candidate_id = interview['candidate_id']
            interviewer = interview['interviewer']
            start_time = interview['start_time']
        else:
            # Assume tuple/Row
            interview_id = interview['id']
            candidate_id = interview['candidate_id']
            interviewer = interview['interviewer']
            start_time = interview['start_time']
        
        # 获取候选人信息
        candidate = get_candidate_info(candidate_id)
        if not candidate:
            logger.error(f"无法找到候选人ID: {candidate_id}的信息")
            continue
        
        if isinstance(candidate, dict):
            candidate_name = candidate['name']
            candidate_email = candidate['email']
            resume_content = candidate['resume_content']
            position_id = candidate['position_id']
        else:
            candidate_name = candidate['name']
            candidate_email = candidate['email']
            resume_content = candidate['resume_content']
            position_id = candidate['position_id']
        
        # 获取岗位信息
        position = get_position_info(position_id)
        if not position:
            logger.error(f"无法找到岗位ID: {position_id}的信息")
            continue
            
        if isinstance(position, dict):
            position_name = position['name']
            requirements = position['requirements']
            responsibilities = position['responsibilities']
        else:
            position_name = position['name']
            requirements = position['requirements']
            responsibilities = position['responsibilities']
        
        logger.info(f"为面试ID: {interview_id}, 候选人: {candidate_name}, 岗位: {position_name} 生成面试问题")
        
        # 生成面试问题
        questions = generate_questions(resume_content, position_name, requirements, responsibilities)
        
        # 保存问题到数据库
        save_questions(interview_id, questions)

        logger.info(f"已为面试ID: {interview_id} 成功生成 {len(questions)} 个问题")

def run_scheduler():
    """
    定时任务调度器
    Scheduler runner
    """
    schedule.every(5).minutes.do(process_pending_interviews)
    
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
  
    # 立即运行一次，然后启动定时任务
    process_pending_interviews()
    
    # 在后台线程中运行定时任务
    scheduler_thread = threading.Thread(target=run_scheduler)
    scheduler_thread.daemon = True
    scheduler_thread.start()
    
    logger.info("面试问题生成定时任务已启动，每5分钟执行一次")
    
    try:
        # 保持主线程运行
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        logger.info("程序已停止") 
