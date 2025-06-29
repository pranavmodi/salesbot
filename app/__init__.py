from flask import Flask
from app.config import Config
import os

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Set DATABASE_URL in app config if not already set
    if not app.config.get('DATABASE_URL'):
        app.config['DATABASE_URL'] = os.getenv('DATABASE_URL')
    
    # Register blueprints
    from app.views.main import bp as main_bp
    app.register_blueprint(main_bp)
    
    from app.views.api import bp as api_bp
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Initialize and start campaign scheduler
    with app.app_context():
        from app.services.campaign_scheduler import campaign_scheduler
        campaign_scheduler.start()
    
    return app 