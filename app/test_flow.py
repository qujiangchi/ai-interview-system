
import requests
import json
import time
import os
import sys
import sqlite3
from datetime import datetime

# 添加当前目录到 path 以便导入模块
sys.path.append(os.getcwd())

# 尝试导入生成脚本
try:
    import generate_interview_questions
    import generate_interview_reports
    print("成功导入生成脚本模块")
except ImportError as e:
    print(f"导入生成脚本失败: {e}")
    print("请确保在 app 目录下运行此脚本")
    sys.exit(1)

BASE_URL = "http://127.0.0.1:8000"

def create_dummy_files():
    # 创建 dummy pdf
    with open("dummy_resume.pdf", "wb") as f:
        f.write(b"%PDF-1.4\n%...\nDummy PDF Content")
    
    # 创建 dummy wav (这只是一个文本文件伪装的，whisper 可能会报错，但我们主要测试流程)
    # 为了让 whisper 不报错，最好弄个真正的 wav 头，或者指望 whisper 处理错误
    # 或者我们可以 mock 掉 server.py 里的 whisper 调用？
    # 不，我们希望测试完整流程。
    # 既然 server.py 处理音频时会尝试转录，如果失败可能会报错。
    # 让我们创建一个极简的 wav 文件头
    import wave
    with wave.open("dummy_audio.wav", "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(16000)
        wav_file.writeframes(b'\x00' * 16000) # 1秒静音

def cleanup_files():
    if os.path.exists("dummy_resume.pdf"):
        os.remove("dummy_resume.pdf")
    if os.path.exists("dummy_audio.wav"):
        os.remove("dummy_audio.wav")

def test_flow():
    print("=== 开始测试流程 ===")
    create_dummy_files()
    
    # 1. 创建职位
    print("\n1. 创建职位...")
    position_data = {
        "name": "测试工程师",
        "requirements": "熟悉Python, 自动化测试",
        "responsibilities": "编写测试脚本",
        "quantity": 1,
        "status": "招聘中",
        "recruiter": "TestBot"
    }
    resp = requests.post(f"{BASE_URL}/api/positions", json=position_data)
    print(f"创建职位响应: {resp.status_code}, {resp.text}")
    assert resp.status_code == 200
    
    # 获取职位 ID
    resp = requests.get(f"{BASE_URL}/api/positions")
    positions = resp.json()
    position_id = positions[-1]['id']
    print(f"职位 ID: {position_id}")
    
    # 2. 创建候选人
    print("\n2. 创建候选人...")
    files = {
        'resume_content': ('dummy_resume.pdf', open('dummy_resume.pdf', 'rb'), 'application/pdf')
    }
    data = {
        'position_id': position_id,
        'name': '张三测试',
        'email': 'test@example.com'
    }
    resp = requests.post(f"{BASE_URL}/api/candidates", data=data, files=files)
    print(f"创建候选人响应: {resp.status_code}, {resp.text}")
    assert resp.status_code == 200
    
    # 获取候选人 ID
    resp = requests.get(f"{BASE_URL}/api/candidates")
    candidates = resp.json()
    candidate_id = candidates[-1]['id']
    print(f"候选人 ID: {candidate_id}")
    
    # 3. 创建面试
    print("\n3. 创建面试...")
    interview_data = {
        'candidate_id': candidate_id,
        'interviewer': 'AI面试官',
        'start_time': int(time.time()),
        'status': 0, # 未开始
        'is_passed': 0
    }
    resp = requests.post(f"{BASE_URL}/api/interviews", json=interview_data)
    print(f"创建面试响应: {resp.status_code}, {resp.text}")
    assert resp.status_code == 200
    
    # 获取面试信息和 Token
    resp = requests.get(f"{BASE_URL}/api/interviews")
    interviews = resp.json()
    interview = interviews[-1]
    interview_id = interview['id']
    token = interview['token']
    print(f"面试 ID: {interview_id}, Token: {token}")
    
    # 4. 触发生成问题
    print("\n4. 触发生成问题...")
    # 手动调用生成函数
    generate_interview_questions.process_pending_interviews()
    
    # 检查状态是否更新
    time.sleep(1)
    resp = requests.get(f"{BASE_URL}/api/interview/{token}/info")
    print(f"面试信息: {resp.json()}")
    # status 应该变成 1 (试题已备好)
    assert resp.json()['status'] == 1
    
    # 5. 获取问题并回答
    print("\n5. 开始面试回答...")
    current_q_id = 0
    while True:
        resp = requests.get(f"{BASE_URL}/api/interview/{token}/get_question", params={'current_id': current_q_id})
        q_data = resp.json()
        
        if q_data.get('id') == 0:
            print("面试结束")
            break
            
        q_id = q_data['id']
        q_text = q_data['text']
        print(f"回答问题 [{q_id}]: {q_text}")
        
        # 提交答案
        files = {
            'audio_answer': ('dummy_audio.wav', open('dummy_audio.wav', 'rb'), 'audio/wav')
        }
        data = {'question_id': q_id}
        resp = requests.post(f"{BASE_URL}/api/interview/{token}/submit_answer", data=data, files=files)
        # print(f"提交响应: {resp.text}")
        
        current_q_id = q_id
        
    # 6. 触发生成报告
    print("\n6. 触发生成报告...")
    # 此时状态应该是 3 (已完成)
    resp = requests.get(f"{BASE_URL}/api/interview/{token}/info")
    assert resp.json()['status'] == 3
    
    generate_interview_reports.process_pending_reports()
    
    # 7. 下载报告
    print("\n7. 下载报告...")
    # 状态应该是 4 (报告已生成)
    # API 没有直接暴露 status，但我们可以尝试下载报告
    resp = requests.get(f"{BASE_URL}/api/interviews/{interview_id}/report")
    if resp.status_code == 200:
        print("报告下载成功")
        with open(f"report_{interview_id}.pdf", "wb") as f:
            f.write(resp.content)
    else:
        print(f"报告下载失败: {resp.status_code}, {resp.text}")
        
    cleanup_files()
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    test_flow()
