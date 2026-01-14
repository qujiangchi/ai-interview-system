"""
Admin API Module
管理员API模块

此模块处理管理员相关的操作，包括：
- 职位管理 (CRUD)
- 候选人管理 (CRUD)
- 面试管理 (CRUD)
- 简历下载
- 报告查看
"""

from flask import Blueprint, jsonify, request, send_file
from app.core.database import get_db_connection
from app.utils.auth_middleware import token_required
from app.utils.helpers import generate_token
from app.core.config import Config
import time
import os
import sqlite3
import io
import logging

logger = logging.getLogger(__name__)
admin_bp = Blueprint('admin', __name__)

# === 职位管理 (Position Management) ===

@admin_bp.route('/positions', methods=['GET'])
@token_required
def get_positions():
    """获取所有职位列表"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM positions')
        positions = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return jsonify(positions)
    except Exception as e:
        logger.error(f"Error fetching positions: {e}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/positions', methods=['POST'])
@token_required
def create_position():
    """创建新职位"""
    try:
        data = request.json
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO positions (name, requirements, responsibilities, quantity, status, created_at, recruiter)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (data['name'], data['requirements'], data['responsibilities'], data['quantity'], data['status'], int(time.time()), data['recruiter']))
            
        conn.commit()
        conn.close()
        return jsonify({'status': 'success'})
    except Exception as e:
        logger.error(f"Error creating position: {e}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/positions/<int:id>', methods=['PUT'])
@token_required
def update_position(id):
    """更新职位信息"""
    try:
        data = request.json
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE positions SET name=?, requirements=?, responsibilities=?, quantity=?, status=?, recruiter=?
            WHERE id=?
        ''', (data['name'], data['requirements'], data['responsibilities'], data['quantity'], data['status'], data['recruiter'], id))
        conn.commit()
        conn.close()
        return jsonify({'status': 'success'})
    except Exception as e:
        logger.error(f"Error updating position: {e}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/positions/<int:id>', methods=['DELETE'])
@token_required
def delete_position(id):
    """删除职位"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM positions WHERE id=?', (id,))
        conn.commit()
        conn.close()
        return jsonify({'status': 'success'})
    except Exception as e:
        logger.error(f"Error deleting position: {e}")
        return jsonify({'error': str(e)}), 500

# === 候选人管理 (Candidate Management) ===

@admin_bp.route('/candidates', methods=['GET'])
@token_required
def get_candidates():
    """获取候选人列表"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, position_id, name, email FROM candidates')
        candidates = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return jsonify(candidates)
    except Exception as e:
        logger.error(f"Error fetching candidates: {e}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/candidates', methods=['POST'])
@token_required
def create_candidate():
    """创建候选人（包含简历上传）"""
    try:
        data = request.form
        
        resume_content = request.files['resume_content'].read() if 'resume_content' in request.files else None
        
        # 数据库适配处理：SQLite 需要 Binary 包装，Postgres 不需要
        if Config.DB_TYPE == 'postgres':
             resume_val = resume_content
        else:
             resume_val = sqlite3.Binary(resume_content) if resume_content is not None else None

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO candidates (position_id, name, email, resume_content)
            VALUES (?, ?, ?, ?)
        ''', (data['position_id'], data['name'], data['email'], resume_val))
        conn.commit()
        conn.close()
        return jsonify({'status': 'success'})
    except Exception as e:
        logger.error(f"Error creating candidate: {e}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/candidates/<int:id>/resume', methods=['GET'])
@token_required
def download_resume(id):
    """下载候选人简历"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT resume_content FROM candidates WHERE id=?', (id,))
        resume = cursor.fetchone()
        conn.close()
        
        if resume and resume['resume_content']:
            content = resume['resume_content']
            # 如果是 memoryview (Postgres)，转换为 bytes
            if isinstance(content, memoryview):
                content = bytes(content)
                
            return send_file(io.BytesIO(content), download_name=f'resume_{id}.pdf', as_attachment=True)
        return jsonify({'error': '简历不存在'}), 404
    except Exception as e:
        logger.error(f"Error downloading resume: {e}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/candidates/<int:id>', methods=['DELETE'])
@token_required
def delete_candidate(id):
    """删除候选人"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM candidates WHERE id=?', (id,))
        conn.commit()
        conn.close()
        return jsonify({'status': 'success'})
    except Exception as e:
        logger.error(f"Error deleting candidate: {e}")
        return jsonify({'error': str(e)}), 500

# === 面试管理 (Interview Management) ===

@admin_bp.route('/interviews', methods=['GET'])
@token_required
def get_interviews():
    """获取所有面试记录"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, candidate_id, interviewer, start_time, status, is_passed, token FROM interviews')
        interviews = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return jsonify(interviews)
    except Exception as e:
        logger.error(f"Error fetching interviews: {e}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/interviews', methods=['POST'])
@token_required
def create_interview():
    """创建新的面试安排"""
    try:
        data = request.json
        data['token'] = generate_token()
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO interviews (candidate_id, interviewer, start_time, status, is_passed , token)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (data['candidate_id'], data['interviewer'], data['start_time'], data['status'], data['is_passed'], data['token'] ))
        conn.commit()
        conn.close()
        return jsonify({'status': 'success'})
    except Exception as e:
        logger.error(f"Error creating interview: {e}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/interviews/<int:id>', methods=['PUT'])
@token_required
def update_interview(id):
    """更新面试信息"""
    try:
        data = request.json
        # 重新生成 Token（如果需要保持 Token 不变，可以修改此处逻辑）
        new_token = generate_token()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE interviews SET candidate_id=?, interviewer=?, start_time=?, status=?, is_passed=? ,token=?
            WHERE id=?
        ''', (data['candidate_id'], data['interviewer'], data['start_time'], data['status'], data['is_passed'], new_token, id))
        conn.commit()
        conn.close()
        return jsonify({'status': 'success'})
    except Exception as e:
        logger.error(f"Error updating interview: {e}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/interviews/<int:id>', methods=['DELETE'])
@token_required
def delete_interview(id):
    """删除面试记录（级联删除相关问题）"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 先删除相关的面试问题
        cursor.execute('DELETE FROM interview_questions WHERE interview_id = ?', (id,))
        
        # 然后删除面试记录
        cursor.execute('DELETE FROM interviews WHERE id = ?', (id,))
        
        conn.commit()
        conn.close()
        return jsonify({'status': 'success'})
    except Exception as e:
        logger.error(f"Error deleting interview: {e}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/interviews/<int:interview_id>/report', methods=['GET'])
@token_required
def download_interview_report(interview_id):
    """
    下载面试评估报告
    
    Query Params:
        preview (bool): 如果为 true，则在浏览器预览；否则作为附件下载。
    """
    return _download_interview_report_logic(interview_id)

def _download_interview_report_logic(interview_id):
    """下载报告的核心逻辑"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 尝试获取报告路径和内容
        # 兼容旧表结构（如果没有 report_path 字段）
        try:
            cursor.execute('''SELECT id, candidate_id, report_content, report_path FROM interviews WHERE id = ? ''', (interview_id, ))
        except Exception:
            conn.rollback() # Postgres 需要回滚事务
            cursor.execute('''SELECT id, candidate_id, report_content FROM interviews WHERE id = ? ''', (interview_id, ))
            
        interview = cursor.fetchone()
        
        conn.close()
        
        if not interview:
            return jsonify({"error": "面试不存在"}), 404
        
        file_stream = None
        file_path = None
        
        # 1. 优先尝试从文件系统读取 (如果 report_path 存在且文件存在)
        if 'report_path' in interview.keys() and interview['report_path'] and os.path.exists(interview['report_path']):
            file_path = interview['report_path']
        
        # 2. 如果文件不存在，尝试从 BLOB 读取
        elif interview['report_content']:
            content = interview['report_content']
            if isinstance(content, memoryview):
                content = bytes(content)
            file_stream = io.BytesIO(content)
        else:
            return jsonify({"error": "面试报告尚未生成"}), 404
            
        # 生成文件名
        file_name = f"interview_report_{interview['id']}.pdf"
        
        # 检查是否为预览模式
        as_attachment = True
        if request.args.get('preview') == 'true':
            as_attachment = False
        
        if file_path:
            return send_file(
                file_path,
                mimetype='application/pdf',
                as_attachment=as_attachment,
                download_name=file_name
            )
        else:
            return send_file(
                file_stream,
                mimetype='application/pdf',
                as_attachment=as_attachment,
                download_name=file_name
            )
    except Exception as e:
        logger.error(f"Error downloading report: {e}")
        return jsonify({'error': str(e)}), 500
