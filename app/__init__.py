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
        
        # Initialize and start deep research scheduler (independent)
        try:
            from deepresearch.background_scheduler import deep_research_scheduler
            deep_research_scheduler.init_app(app)
            app.logger.info("Deep research scheduler initialized successfully")
        except Exception as e:
            app.logger.error(f"Failed to initialize deep research scheduler: {e}")
        
        # Check for and recover orphaned background research jobs on startup
        # Only run this once during startup, not on every service initialization
        try:
            from deepresearch.llm_deep_research_service import LLMDeepResearchService
            # Create a temporary instance just for startup recovery
            startup_service = LLMDeepResearchService()
            startup_service.check_and_recover_background_jobs()
            app.logger.info("Background job recovery check completed on startup")
        except Exception as e:
            app.logger.error(f"Failed to check for orphaned background jobs on startup: {e}")
    
    return app 