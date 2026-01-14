from flask import Flask
from flask_cors import CORS
from config import Config

def create_app():
    app = Flask(__name__, static_folder=Config.STATIC_FOLDER, static_url_path='/static')
    app.config.from_object(Config)
    
    # Enable CORS
    CORS(app)
    
    # Register Blueprints
    from app.api.auth import auth_bp
    from app.api.admin import admin_bp
    from app.api.interview import interview_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    app.register_blueprint(interview_bp, url_prefix='/api/interview')
    
    # Register public/legacy routes if any, or move them to blueprints
    # For now, we will move everything to blueprints.
    
    @app.route('/health')
    def health():
        return {'status': 'ok'}

    return app
