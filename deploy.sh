#!/bin/bash
set -e

# 设置工作目录
APP_DIR="/root/project-interview/app"
cd $APP_DIR

# 确保日志目录存在
mkdir -p ../logs

# 设置环境变量为 Postgres (这会覆盖 .env 中的默认值，或者您可以在 .env 中设置)
export DB_TYPE=postgres

echo "Stopping old processes..."
pkill -f "python3 server.py" || true
pkill -f "gunicorn" || true
pkill -f "python3 generate_interview_questions.py" || true
pkill -f "python3 generate_interview_reports.py" || true

echo "Starting Backend Services (with PostgreSQL)..."

# 启动 Gunicorn Web 服务
# 4 workers, timeout 120s (因为语音处理可能耗时), bind 0.0.0.0:8000
nohup gunicorn -w 4 -b 0.0.0.0:8000 --timeout 120 server:app > ../logs/gunicorn.log 2>&1 &
echo "Gunicorn started."

# 启动后台任务
nohup python3 generate_interview_questions.py > ../logs/question_gen_console.log 2>&1 &
echo "Question Generator started."

nohup python3 generate_interview_reports.py > ../logs/report_gen_console.log 2>&1 &
echo "Report Generator started."

echo "Restarting Nginx..."
nginx -s reload || systemctl restart nginx

echo "Deployment Complete!"
echo "Logs are available in /root/project-interview/logs/"
