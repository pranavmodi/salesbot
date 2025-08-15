from flask import Flask, session, redirect, url_for, request, g
from app.config import Config
import os

def create_app():
    # Run startup validation before creating the app
    try:
        from app.startup_validation import run_startup_validation
        run_startup_validation()
    except ImportError:
        # If startup_validation module is not available, continue without validation
        # This allows for backward compatibility during deployment
        pass
    except Exception as e:
        # Critical startup validation failed
        import logging
        logging.error(f"❌ Startup validation failed: {e}")
        logging.error("❌ Application cannot start safely. Please fix the issues above.")
        raise SystemExit(1)
    
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
    from app.views.admin_routes import admin_bp
    from app.views.tracking_routes import tracking_bp

    app.register_blueprint(contact_bp)
    app.register_blueprint(company_bp)
    app.register_blueprint(email_bp)
    app.register_blueprint(campaign_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(tracking_bp)

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
        app.logger.info("🔐 Starting Google OAuth flow")
        
        client_id = os.getenv('GOOGLE_CLIENT_ID')
        client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
        
        app.logger.info(f"📋 GOOGLE_CLIENT_ID configured: {'Yes' if client_id else 'No'}")
        app.logger.info(f"📋 GOOGLE_CLIENT_SECRET configured: {'Yes' if client_secret else 'No'}")
        
        if not client_id or not client_secret:
            app.logger.error('❌ Google OAuth credentials not configured')
            return redirect(url_for('main.login_page'))
            
        # Use custom callback URL if provided, otherwise use Flask's url_for
        callback_url = os.getenv('GOOGLE_OAUTH_CALLBACK_URL')
        if callback_url:
            redirect_uri = callback_url
            app.logger.info(f"🔗 Using custom callback URL: {redirect_uri}")
        else:
            # Force Railway production URL to match Google Console config
            if 'railway.app' in request.host:
                redirect_uri = 'https://salesbot-production-370d.up.railway.app/auth/google/callback'
                app.logger.info(f"🔗 Using forced Railway callback URL: {redirect_uri}")
            else:
                redirect_uri = url_for('auth_google_callback', _external=True)
                app.logger.info(f"🔗 Using Flask-generated callback URL: {redirect_uri}")
            
        # Log request details for debugging
        app.logger.info(f"🌐 Request host: {request.host}")
        app.logger.info(f"🔒 Request scheme: {request.scheme}")
        app.logger.info(f"🎯 Expected callback should be: {request.scheme}://{request.host}/auth/google/callback")
            
        app.logger.info("🚀 Redirecting to Google OAuth...")
        return google.authorize_redirect(redirect_uri, prompt='select_account')
    
    @app.route('/auth/google/callback')
    def auth_google_callback():
        app.logger.info("🔄 Google OAuth callback received")
        try:
            app.logger.info("🔑 Attempting to get access token...")
            token = google.authorize_access_token()
            app.logger.info(f"✅ Token received: {'Yes' if token else 'No'}")
            
            user_info = token.get('userinfo') if token else None
            app.logger.info(f"👤 User info received: {'Yes' if user_info else 'No'}")
            
            if user_info:
                app.logger.info(f"📧 User email: {user_info.get('email')}")
                app.logger.info(f"👤 User name: {user_info.get('name')}")
                # Get or create user in database
                app.logger.info("🗄️ Connecting to database...")
                from app.database import get_shared_engine
                from sqlalchemy import text
                
                try:
                    engine = get_shared_engine()
                    app.logger.info("✅ Database engine obtained")
                    with engine.connect() as conn:
                        with conn.begin():
                            # Check if user exists
                            result = conn.execute(text("""
                            SELECT id, tenant_id, is_first_login FROM users 
                            WHERE email = :email OR google_id = :google_id
                            """), {
                                'email': user_info['email'],
                                'google_id': user_info['sub']
                            })
                            user_row = result.fetchone()
                            
                            if user_row:
                                user_id = user_row.id
                                tenant_id = user_row.tenant_id
                                is_first_login = user_row.is_first_login or False
                                app.logger.info(f"👤 Existing user found: {user_id}, first_login: {is_first_login}")
                                
                                # If this is a returning user with is_first_login=True, mark as false
                                if is_first_login:
                                    conn.execute(text("""
                                        UPDATE users 
                                        SET is_first_login = false
                                        WHERE id = :user_id
                                    """), {'user_id': user_id})
                                    app.logger.info(f"🔄 Marked user {user_id} as no longer first login")
                            else:
                                app.logger.info("👤 Creating new user and tenant...")
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
                                
                                # Create new user with their own tenant (mark as first login)
                                result = conn.execute(text("""
                                    INSERT INTO users (email, name, google_id, tenant_id, is_first_login, created_at)
                                    VALUES (:email, :name, :google_id, :tenant_id, :is_first_login, CURRENT_TIMESTAMP)
                                    RETURNING id
                                """), {
                                    'email': user_info['email'],
                                    'name': user_info['name'],
                                    'google_id': user_info['sub'],
                                    'tenant_id': tenant_id,
                                    'is_first_login': True
                                })
                                user_id = result.fetchone().id
                                is_first_login = True  # New users are always first login
                                app.logger.info(f"✅ Created new user: {user_id}")
                
                except Exception as db_error:
                    app.logger.error(f"❌ Database error during OAuth: {db_error}")
                    return redirect(url_for('main.login_page'))
                
                # Store user session data
                app.logger.info("💾 Storing user session data...")
                session['user'] = {
                    'id': user_id,
                    'email': user_info['email'],
                    'name': user_info['name'],
                    'picture': user_info.get('picture'),
                    'google_id': user_info['sub'],
                    'tenant_id': tenant_id,
                    'is_first_login': is_first_login
                }
                
                # Redirect to originally requested page or dashboard
                next_url = session.pop('next_url', None)
                redirect_url = next_url or url_for('main.index')
                app.logger.info(f"🚀 OAuth success! Redirecting to: {redirect_url}")
                return redirect(redirect_url)
            else:
                app.logger.error('Failed to get user info from Google')
                return redirect(url_for('main.login_page'))
                
        except Exception as e:
            app.logger.error(f'❌ Google OAuth error: {e}')
            app.logger.error(f'❌ Error type: {type(e).__name__}')
            import traceback
            app.logger.error(f'❌ Full traceback: {traceback.format_exc()}')
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