from app.api import create_app
from app.database import init_db
from app.config import Config
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('server')

# Initialize DB (and check connection)
init_db()

app = create_app()

if __name__ == '__main__':
    app.run(debug=Config.DEBUG, host='0.0.0.0', port=8000)
