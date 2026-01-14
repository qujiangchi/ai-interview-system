from flask import Blueprint, jsonify, request
from app.database import get_db_connection
from app.config import Config
import time
import os
import tempfile
import whisper
import logging
import torch
from datetime import datetime

import threading
from app.generate_interview_reports import generate_report_for_interview

logger = logging.getLogger(__name__)
interview_bp = Blueprint('interview', __name__)

whisper_model = None
model_lock = threading.Lock()

def get_whisper_model():
    global whisper_model
    if whisper_model is None:
        with model_lock:
            if whisper_model is None:
                try:
                    if torch.cuda.is_available():
                        whisper_model = whisper.load_model(Config.WHISPER_MODEL_SIZE).to("cuda")
                        logger.info(f"GPU 可用，使用 {Config.WHISPER_MODEL_SIZE} 模型")
                    else:
                        # Force CPU and ensure threads
                        whisper_model = whisper.load_model("base", device="cpu")
                        logger.info("GPU 不可用，使用 base 模型")
                except Exception as e:
                    logger.error(f"加载 Whisper 模型失败: {e}")
                    whisper_model = whisper.load_model("tiny")
    return whisper_model

@interview_bp.route('/<token>/info', methods=['GET'])
def get_interview_info(token):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取面试及相关信息
        # Use adapter compatible SQL
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
            return jsonify({"error": "面试不存在"}), 404
        
        # 转换为字典
        result = dict(interview_info)
        
        # 格式化时间
        if result['start_time']:
            result['time'] = datetime.fromtimestamp(result['start_time']).strftime('%Y年%m月%d日 %H:%M')
        else:
            result['time'] = "未设置时间"
        
        # 构造返回数据
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
    try:
        current_question_id = request.args.get('current_id', type=int, default=0)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 先获取面试ID
        cursor.execute('SELECT id FROM interviews WHERE token = ?', (token,))
        interview = cursor.fetchone()
        
        if not interview:
            conn.close()
            return jsonify({"id": 0, "text": "面试无效"}), 404
        
        # 获取下一个问题
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
            # 获取下一个问题
            cursor.execute('''
                SELECT id, question as text
                FROM interview_questions
                WHERE interview_id = ? AND id > ?
                ORDER BY id ASC
                LIMIT 1
            ''', (interview['id'], current_question_id))
            next_question = cursor.fetchone()
        
        conn.close()
        
        # 如果没有下一个问题，返回结束标志
        if not next_question:
            return jsonify({"id": 0, "text": "面试已完成"})
        
        return jsonify(dict(next_question))
    except Exception as e:
        logger.error(f"Error getting next question: {e}")
        return jsonify({'error': str(e)}), 500

@interview_bp.route('/<token>/submit_answer', methods=['POST'])
def submit_answer(token):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # 验证令牌
        cursor.execute('SELECT id FROM interviews WHERE token = ?', (token,))
        interview = cursor.fetchone()
        
        if not interview:
            conn.close()
            return jsonify({"error": "面试不存在"}), 404
        
        # 获取问题ID和音频答案
        question_id = request.form.get('question_id')
        audio_answer = request.files.get('audio_answer')
        
        if not question_id or not audio_answer:
            conn.close()
            return jsonify({"error": "缺少必要参数"}), 400
        
        audio_data = audio_answer.read()
        if Config.DB_TYPE == 'postgres':
             audio_binary = audio_data # PG handles bytes
        else:
             import sqlite3
             audio_binary = sqlite3.Binary(audio_data)
             
        # 从 webm/wav 音频文件 提取 中文文本
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_file.write(audio_data)
            temp_file_path = temp_file.name

        # 使用 transcribe 处理临时文件
        audio_text = ""
        try:
            model = get_whisper_model()
            result = model.transcribe(temp_file_path, language="zh")
            audio_text = result["text"]
        except Exception as e:
            logger.error(f"Whisper transcription failed: {e}")
            audio_text = "无法识别语音"
        finally:
            # Clean up temp file
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)

        answered_time = int(time.time())
        
        cursor.execute('''
            UPDATE interview_questions
            SET answer_audio = ?, answer_text = ?, answered_at = ?
            WHERE id = ? AND interview_id = ?
        ''', (audio_binary, audio_text, answered_time, question_id, interview['id']))
        
        # 获取下一个问题
        cursor.execute('''
            SELECT id, question as text
            FROM interview_questions
            WHERE interview_id = ? AND id > ?
            ORDER BY id ASC
            LIMIT 1
        ''', (interview['id'], question_id))
        next_question = cursor.fetchone()
        
        conn.commit()
        
        # 如果没有下一个问题，检查是否所有问题都已回答
        if not next_question:
            # 检查是否所有问题都已回答
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
        
        conn.close()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error submitting answer: {e}")
        return jsonify({'error': str(e)}), 500

@interview_bp.route('/<token>/toggle_voice_reading', methods=['POST'])
def toggle_voice_reading(token):
    try:
        data = request.json
        enabled = data.get('enabled', False)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        # Update voice reading setting
        cursor.execute('UPDATE interviews SET voice_reading = ? WHERE token = ?', 
                    (1 if enabled else 0, token))
        conn.commit()
        conn.close()
        
        return jsonify({'status': 'success', 'voice_reading': enabled})
    except Exception as e:
        logger.error(f"Error toggling voice reading: {e}")
        return jsonify({'error': str(e)}), 500
