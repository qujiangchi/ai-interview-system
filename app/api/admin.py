from flask import Blueprint, jsonify, request, send_file
from app.database import get_db_connection
from app.utils.auth_middleware import token_required
from app.utils.helpers import generate_token
from app.config import Config
import time
import os
import sqlite3
import io
import logging

logger = logging.getLogger(__name__)
admin_bp = Blueprint('admin', __name__)

# 岗位管理
@admin_bp.route('/positions', methods=['GET'])
@token_required
def get_positions():
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

# 候选人管理
@admin_bp.route('/candidates', methods=['GET'])
@token_required
def get_candidates():
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
    try:
        data = request.form
        
        resume_content = request.files['resume_content'].read() if 'resume_content' in request.files else None
        # For Postgres, we might need to handle binary differently if not using the adapter correctly,
        # but the adapter seems to handle bytes -> bytes
        
        # If using postgres adapter with psycopg2, bytes are automatically adapted to BYTEA.
        # However, for sqlite3.Binary wrapper is needed for SQLite.
        # The adapter code in database.py doesn't seem to unwrap sqlite3.Binary if passed to it.
        # So we should be careful.
        
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
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT resume_content FROM candidates WHERE id=?', (id,))
        resume = cursor.fetchone()
        conn.close()
        
        if resume and resume['resume_content']:
            content = resume['resume_content']
            # If it's memoryview (Postgres), convert to bytes
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

# 面试管理
@admin_bp.route('/interviews', methods=['GET'])
@token_required
def get_interviews():
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
    try:
        data = request.json
        # Check if token needs to be regenerated or kept
        # Usually we don't change token on update unless specified
        # But existing code regenerated it. Let's keep existing behavior or improve.
        # Improved: only generate if not exists or requested? 
        # Existing code: data['token'] = generate_token()
        
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
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取面试信息及报告内容
        # Check if report_path exists in schema first
        try:
            cursor.execute('''SELECT id, candidate_id, report_content, report_path FROM interviews WHERE id = ? ''', (interview_id, ))
        except:
            # Fallback for old schema
            cursor.execute('''SELECT id, candidate_id, report_content FROM interviews WHERE id = ? ''', (interview_id, ))
            
        interview = cursor.fetchone()
        
        conn.close()
        
        if not interview:
            return jsonify({"error": "面试不存在"}), 404
        
        # Determine file source
        file_stream = None
        file_path = None
        
        # 1. Try to read from file system if path exists
        if 'report_path' in interview.keys() and interview['report_path'] and os.path.exists(interview['report_path']):
            file_path = interview['report_path']
            # We will use send_file with path
        
        # 2. If not, try to read from BLOB
        elif interview['report_content']:
            content = interview['report_content']
            if isinstance(content, memoryview):
                content = bytes(content)
            file_stream = io.BytesIO(content)
        else:
            return jsonify({"error": "面试报告尚未生成"}), 404
            
        # 生成文件名
        file_name = f"面试报告_{interview['id']}.pdf"
        
        # Check if preview is requested
        as_attachment = request.args.get('preview') != 'true'
        
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
