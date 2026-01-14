"""
Interview API Module
面试相关API模块

此模块处理与面试过程相关的所有API请求，包括：
- 获取面试信息
- 获取面试问题
- 提交回答（音频/文本）
- 语音转文字处理
- 触发实时AI评估
"""

from flask import Blueprint, jsonify, request
from app.core.database import get_db_connection
from app.core.config import Config
import time
import os
import tempfile
import whisper
import logging
import torch
from datetime import datetime
import threading
from app.services.report_service import evaluate_single_question

logger = logging.getLogger(__name__)
interview_bp = Blueprint('interview', __name__)

# 全局变量缓存 Whisper 模型
# Global variable to cache Whisper model
whisper_model = None
model_lock = threading.Lock()

def get_whisper_model():
    """
    单例模式获取 Whisper 模型实例
    Get Whisper model instance (Singleton)
    
    自动检测是否有可用的 GPU，如果有则加载到 CUDA，否则使用 CPU。
    """
    global whisper_model
    if whisper_model is None:
        with model_lock:
            if whisper_model is None:
                try:
                    if torch.cuda.is_available():
                        whisper_model = whisper.load_model(Config.WHISPER_MODEL_SIZE).to("cuda")
                        logger.info(f"GPU Available. Loaded Whisper model '{Config.WHISPER_MODEL_SIZE}' on CUDA.")
                    else:
                        # 强制使用 CPU 并加载较小的模型以保证稳定性
                        # Force CPU and ensure threads
                        whisper_model = whisper.load_model("base", device="cpu")
                        logger.info("GPU Unavailable. Loaded 'base' model on CPU.")
                except Exception as e:
                    logger.error(f"Failed to load Whisper model: {e}")
                    # 回退到最小模型
                    whisper_model = whisper.load_model("tiny")
    return whisper_model

@interview_bp.route('/<token>/info', methods=['GET'])
def get_interview_info(token):
    """
    获取面试基础信息
    Get Interview Basic Info
    
    Args:
        token: 面试唯一访问令牌
        
    Returns:
        JSON: 包含候选人、职位、面试状态等信息
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取面试及相关联的候选人和职位信息
        cursor.execute('''
            SELECT i.id, i.question_count, i.voice_reading, i.start_time, i.status,
                   c.name as candidate_name, c.email as candidate_email,
                   p.name as position_name, p.requirements
            FROM interviews i
            JOIN candidates c ON i.candidate_id = c.id
            JOIN positions p ON c.position_id = p.id
            WHERE i.token = ?
        ''', (token,))
        interview_info = cursor.fetchone()
        
        conn.close()
        
        if not interview_info:
            return jsonify({"error": "面试不存在 (Interview not found)"}), 404
        
        # 转换为字典以便序列化
        result = dict(interview_info)
        
        # 格式化时间戳
        if result['start_time']:
            result['time'] = datetime.fromtimestamp(result['start_time']).strftime('%Y年%m月%d日 %H:%M')
        else:
            result['time'] = "未设置时间"
        
        return jsonify({
            "interview_id": result['id'],
            "time": result['time'],
            "position": result['position_name'],
            "candidate": result['candidate_name'],
            "status": result['status'],
            "question_count": result['question_count'],
            "voice_reading": result['voice_reading']
        })
    except Exception as e:
        logger.error(f"Error getting interview info: {e}")
        return jsonify({'error': str(e)}), 500

@interview_bp.route('/<token>/get_question', methods=['GET'])
def get_next_question(token):
    """
    获取下一个面试问题
    Get Next Interview Question
    
    支持通过 current_id 参数获取指定问题之后的下一个问题。
    如果 current_id 为 0，则返回第一个问题。
    """
    try:
        current_question_id = request.args.get('current_id', type=int, default=0)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 验证 Token 并获取面试 ID
        cursor.execute('SELECT id FROM interviews WHERE token = ?', (token,))
        interview = cursor.fetchone()
        
        if not interview:
            conn.close()
            return jsonify({"id": 0, "text": "面试无效 (Invalid Interview)"}), 404
        
        next_question = None
        if current_question_id == 0:
            # 获取第一个问题
            cursor.execute('''
                SELECT id, question as text
                FROM interview_questions
                WHERE interview_id = ?
                ORDER BY id ASC
                LIMIT 1
            ''', (interview['id'],))
            next_question = cursor.fetchone()
        else:
            # 获取当前问题之后的下一个问题
            cursor.execute('''
                SELECT id, question as text
                FROM interview_questions
                WHERE interview_id = ? AND id > ?
                ORDER BY id ASC
                LIMIT 1
            ''', (interview['id'], current_question_id))
            next_question = cursor.fetchone()
        
        conn.close()
        
        # 如果没有下一个问题，说明面试已结束
        if not next_question:
            return jsonify({"id": 0, "text": "面试已完成 (Interview Completed)"})
        
        return jsonify(dict(next_question))
    except Exception as e:
        logger.error(f"Error getting next question: {e}")
        return jsonify({'error': str(e)}), 500

@interview_bp.route('/<token>/submit_answer', methods=['POST'])
def submit_answer(token):
    """
    提交面试回答
    Submit Interview Answer
    
    接收音频文件，使用 Whisper 进行语音转文字，并触发后台 AI 评分。
    
    Form Data:
        question_id: 问题 ID
        audio_answer: 音频文件
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 验证令牌
        cursor.execute('SELECT id FROM interviews WHERE token = ?', (token,))
        interview = cursor.fetchone()
        
        if not interview:
            conn.close()
            return jsonify({"error": "面试不存在"}), 404
        
        question_id = request.form.get('question_id')
        audio_answer = request.files.get('audio_answer')
        
        if not question_id or not audio_answer:
            conn.close()
            return jsonify({"error": "缺少必要参数 (Missing parameters)"}), 400
        
        # 读取音频数据
        audio_data = audio_answer.read()
        
        # 处理数据库二进制存储兼容性
        if Config.DB_TYPE == 'postgres':
             audio_binary = audio_data # PG adapter handles bytes
        else:
             import sqlite3
             audio_binary = sqlite3.Binary(audio_data)
             
        # === 语音转文字 (Speech to Text) ===
        # 将音频保存为临时文件以供 Whisper 处理
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_file.write(audio_data)
            temp_file_path = temp_file.name

        audio_text = ""
        try:
            model = get_whisper_model()
            # 调用 Whisper 模型进行转录
            result = model.transcribe(temp_file_path, language="zh")
            audio_text = result["text"]
        except Exception as e:
            logger.error(f"Whisper transcription failed: {e}")
            audio_text = "无法识别语音 (Speech recognition failed)"
        finally:
            # 清理临时文件
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)

        answered_time = int(time.time())
        
        # 更新数据库中的回答
        cursor.execute('''
            UPDATE interview_questions
            SET answer_audio = ?, answer_text = ?, answered_at = ?
            WHERE id = ? AND interview_id = ?
        ''', (audio_binary, audio_text, answered_time, question_id, interview['id']))
        
        # 检查是否还有下一个问题
        cursor.execute('''
            SELECT id, question as text
            FROM interview_questions
            WHERE interview_id = ? AND id > ?
            ORDER BY id ASC
            LIMIT 1
        ''', (interview['id'], question_id))
        next_question = cursor.fetchone()
        
        # 提前提交并关闭连接，避免长时间占用
        conn.commit()
        conn.close() 
        
        # === 异步 AI 评估 (Async AI Evaluation) ===
        # 启动后台线程对该问题的回答进行实时评分
        try:
            threading.Thread(target=evaluate_single_question, args=(question_id,)).start()
        except Exception as e:
            logger.error(f"Failed to start evaluation thread: {e}")
        
        # 如果没有下一个问题，检查整体进度
        if not next_question:
            # 重新打开连接检查状态
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT COUNT(*) as total, SUM(CASE WHEN answered_at IS NOT NULL THEN 1 ELSE 0 END) as answered
                FROM interview_questions
                WHERE interview_id = ?
            ''', (interview['id'],))
            all_answered = cursor.fetchone()
            
            # 如果所有问题都已回答，将面试状态更新为"已完成" (3)
            if all_answered['total'] == all_answered['answered']:
                cursor.execute('UPDATE interviews SET status = 3 WHERE id = ?', (interview['id'],))
                conn.commit()
            conn.close()
            
            result = {
                "status": "success",
                "message": "答案已提交",
                "next_question": {"id": 0, "text": "面试已完成"}
            }
        else:
            result = {
                "status": "success",
                "message": "答案已提交",
                "next_question": dict(next_question)
            }
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error submitting answer: {e}")
        return jsonify({'error': str(e)}), 500

@interview_bp.route('/<token>/toggle_voice_reading', methods=['POST'])
def toggle_voice_reading(token):
    """
    切换语音朗读功能开关
    Toggle Voice Reading Feature
    """
    try:
        data = request.json
        enabled = data.get('enabled', False)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE interviews SET voice_reading = ? WHERE token = ?', 
                    (1 if enabled else 0, token))
        conn.commit()
        conn.close()
        
        return jsonify({'status': 'success', 'voice_reading': enabled})
    except Exception as e:
        logger.error(f"Error toggling voice reading: {e}")
        return jsonify({'error': str(e)}), 500
