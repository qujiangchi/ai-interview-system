import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import psycopg2
import os
from app.core.config import Config

# 强制设置 DB_TYPE 为 postgres，以防环境变量未设置
os.environ["DB_TYPE"] = "postgres"

def check_connection():
    print(f"正在尝试连接数据库...")
    print(f"Host: {Config.PG_HOST}")
    print(f"Port: {Config.PG_PORT}")
    print(f"Database: {Config.PG_DB}")
    print(f"User: {Config.PG_USER}")
    
    try:
        conn = psycopg2.connect(
            host=Config.PG_HOST,
            port=Config.PG_PORT,
            user=Config.PG_USER,
            password=Config.PG_PASSWORD,
            dbname=Config.PG_DB
        )
        print("\n✅ 数据库连接成功！")
        
        cursor = conn.cursor()
        
        # 1. 查看所有表
        print("\n[数据库中的表]:")
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        tables = cursor.fetchall()
        for table in tables:
            print(f"- {table[0]}")
            
        # 2. 查询 positions 表的数据
        print("\n[positions 表中的前 3 条记录]:")
        cursor.execute("SELECT id, name, status FROM positions LIMIT 3")
        rows = cursor.fetchall()
        if not rows:
            print("(暂无数据)")
        else:
            print(f"{'ID':<5} {'职位名称':<20} {'状态':<10}")
            print("-" * 40)
            for row in rows:
                print(f"{row[0]:<5} {row[1]:<20} {row[2]:<10}")
                
        # 3. 统计各表数据量
        print("\n[数据统计]:")
        for table in ['positions', 'candidates', 'interviews', 'interview_questions']:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"- {table}: {count} 条记录")
            except:
                print(f"- {table}: 查询失败")

        conn.close()
        
    except Exception as e:
        print(f"\n❌ 连接失败: {e}")

if __name__ == "__main__":
    check_connection()
