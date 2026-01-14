import sys
import os
import time
import schedule

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.logger import report_logger as logger
from app.services.report_service import process_pending_reports, ensure_report_dir

def run_scheduler():
    """Set up the scheduler to run the task every 5 minutes"""
    # Schedule the job to run every 5 minutes
    schedule.every(5).minutes.do(process_pending_reports)
    
    # Run the job once immediately when starting
    process_pending_reports()
    
    # Keep the script running
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    ensure_report_dir()
    logger.info("Starting interview report generation service...")
    run_scheduler()
