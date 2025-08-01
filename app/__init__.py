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
    
    from app.views.contact_routes import contact_bp
    from app.views.company_routes import company_bp
    from app.views.email_routes import email_bp
    from app.views.campaign_routes import campaign_bp
    from app.views.api import api_bp

    app.register_blueprint(contact_bp)
    app.register_blueprint(company_bp)
    app.register_blueprint(email_bp)
    app.register_blueprint(campaign_bp)
    app.register_blueprint(api_bp)
    
    # Initialize and start campaign scheduler
    with app.app_context():
        from app.services.campaign_scheduler import campaign_scheduler
        campaign_scheduler.init_app(app)
    
    return app 