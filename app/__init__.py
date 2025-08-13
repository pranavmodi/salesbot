from flask import Flask, session, redirect, url_for, request, g
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
    from app.views.settings_routes import settings_bp

    app.register_blueprint(contact_bp)
    app.register_blueprint(company_bp)
    app.register_blueprint(email_bp)
    app.register_blueprint(campaign_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(settings_bp)

    # Google OAuth setup
    from authlib.integrations.flask_client import OAuth
    oauth = OAuth(app)
    
    # Configure Google OAuth
    google = oauth.register(
        name='google',
        client_id=os.getenv('GOOGLE_CLIENT_ID'),
        client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={
            'scope': 'openid email profile'
        }
    )
    
    @app.route('/auth/google')
    def auth_google():
        if not os.getenv('GOOGLE_CLIENT_ID') or not os.getenv('GOOGLE_CLIENT_SECRET'):
            app.logger.warning('Google OAuth credentials not configured')
            return redirect(url_for('main.login_page'))
            
        # Use custom callback URL if provided, otherwise use Flask's url_for
        callback_url = os.getenv('GOOGLE_OAUTH_CALLBACK_URL')
        if callback_url:
            redirect_uri = callback_url
        else:
            redirect_uri = url_for('auth_google_callback', _external=True)
        return google.authorize_redirect(redirect_uri, prompt='select_account')
    
    @app.route('/auth/google/callback')
    def auth_google_callback():
        try:
            token = google.authorize_access_token()
            user_info = token.get('userinfo')
            
            if user_info:
                # Get or create user in database
                from app.database import get_shared_engine
                from sqlalchemy import text
                
                engine = get_shared_engine()
                with engine.connect() as conn:
                    with conn.begin():
                        # Check if user exists
                        result = conn.execute(text("""
                            SELECT id, tenant_id FROM users 
                            WHERE email = :email OR google_id = :google_id
                        """), {
                            'email': user_info['email'],
                            'google_id': user_info['sub']
                        })
                        user_row = result.fetchone()
                        
                        if user_row:
                            user_id = user_row.id
                            tenant_id = user_row.tenant_id
                        else:
                            # Create new tenant for this user
                            import uuid
                            tenant_name = f"{user_info['name']} ({user_info['email']})"
                            tenant_slug = user_info['email'].split('@')[0].lower().replace('.', '-')
                            
                            tenant_result = conn.execute(text("""
                                INSERT INTO tenants (id, name, slug, created_at)
                                VALUES (:id, :name, :slug, CURRENT_TIMESTAMP)
                                RETURNING id
                            """), {
                                'id': str(uuid.uuid4()),
                                'name': tenant_name,
                                'slug': tenant_slug
                            })
                            tenant_id = tenant_result.fetchone().id
                            
                            # Create new user with their own tenant
                            result = conn.execute(text("""
                                INSERT INTO users (email, name, google_id, tenant_id, created_at)
                                VALUES (:email, :name, :google_id, :tenant_id, CURRENT_TIMESTAMP)
                                RETURNING id
                            """), {
                                'email': user_info['email'],
                                'name': user_info['name'],
                                'google_id': user_info['sub'],
                                'tenant_id': tenant_id
                            })
                            user_id = result.fetchone().id
                
                # Store user session data
                session['user'] = {
                    'id': user_id,
                    'email': user_info['email'],
                    'name': user_info['name'],
                    'picture': user_info.get('picture'),
                    'google_id': user_info['sub'],
                    'tenant_id': tenant_id
                }
                
                # Redirect to originally requested page or dashboard
                next_url = session.pop('next_url', None)
                return redirect(next_url or url_for('main.index'))
            else:
                app.logger.error('Failed to get user info from Google')
                return redirect(url_for('main.login_page'))
                
        except Exception as e:
            app.logger.error(f'Google OAuth error: {e}')
            return redirect(url_for('main.login_page'))

    # Tenant resolver
    from app.tenant import resolve_tenant_context
    @app.before_request
    def _before_request_resolve_tenant():
        resolve_tenant_context()
    
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