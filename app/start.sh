#!/bin/bash
cd /root/project-interview/app
export PYTHONUNBUFFERED=1

# 启动 Web 服务
python3 server.py &

# 启动问题生成服务
python3 generate_interview_questions.py &

# 启动报告生成服务
python3 generate_interview_reports.py &

# 等待所有后台进程
wait