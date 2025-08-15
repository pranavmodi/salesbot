from flask import Blueprint, render_template, request, jsonify, current_app, session, redirect, url_for
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
import os
from functools import wraps

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(f):
    """Decorator to require admin access."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get admin emails from environment variable (fallback to hardcoded)
        admin_emails = os.getenv('ADMIN_EMAILS', 'pranav.modi@gmail.com').split(',')
        admin_emails = [email.strip() for email in admin_emails]  # Clean whitespace
        
        user = session.get('user')
        if not user or user.get('email') not in admin_emails:
            current_app.logger.warning(f"Unauthorized admin access attempt from: {user.get('email') if user else 'anonymous'}")
            if request.path.startswith('/admin/api/'):
                return jsonify({'success': False, 'error': 'Unauthorized'}), 403
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/')
@admin_required
def dashboard():
    """Admin dashboard with usage statistics."""
    return render_template('admin/dashboard.html')

@admin_bp.route('/api/stats')
@admin_required
def get_stats():
    """Get usage statistics for admin dashboard."""
    try:
        from app.database import get_shared_engine
        
        current_app.logger.info("Admin requesting stats")
        engine = get_shared_engine()
        if not engine:
            raise Exception("Could not get database engine")
            
        with engine.connect() as conn:
            # Get basic counts
            stats = {}
            
            # Total counts with error handling
            try:
                result = conn.execute(text("SELECT COUNT(*) FROM users"))
                stats['total_users'] = result.scalar()
            except Exception as e:
                current_app.logger.warning(f"Error counting users: {e}")
                stats['total_users'] = 0
                
            try:
                result = conn.execute(text("SELECT COUNT(*) FROM tenants"))
                stats['total_tenants'] = result.scalar()
            except Exception as e:
                current_app.logger.warning(f"Error counting tenants: {e}")
                stats['total_tenants'] = 0
            
            try:
                result = conn.execute(text("SELECT COUNT(*) FROM companies"))
                stats['total_companies'] = result.scalar()
            except Exception as e:
                current_app.logger.warning(f"Error counting companies: {e}")
                stats['total_companies'] = 0
            
            try:
                result = conn.execute(text("SELECT COUNT(*) FROM contacts"))
                stats['total_contacts'] = result.scalar()
            except Exception as e:
                current_app.logger.warning(f"Error counting contacts: {e}")
                stats['total_contacts'] = 0
            
            try:
                result = conn.execute(text("SELECT COUNT(*) FROM campaigns"))
                stats['total_campaigns'] = result.scalar()
            except Exception as e:
                current_app.logger.warning(f"Error counting campaigns: {e}")
                stats['total_campaigns'] = 0
            
            try:
                result = conn.execute(text("SELECT COUNT(*) FROM email_history"))
                stats['total_emails_sent'] = result.scalar()
            except Exception as e:
                current_app.logger.warning(f"Error counting email_history: {e}")
                stats['total_emails_sent'] = 0
            
            # Research stats
            try:
                result = conn.execute(text("""
                    SELECT COUNT(*) FROM companies 
                    WHERE llm_research_step_status = 'completed'
                """))
                stats['completed_research'] = result.scalar()
            except Exception as e:
                current_app.logger.warning(f"Error counting completed research: {e}")
                stats['completed_research'] = 0
            
            try:
                result = conn.execute(text("""
                    SELECT COUNT(*) FROM companies 
                    WHERE llm_research_step_status IN ('step_1_in_progress', 'step_2_in_progress', 'step_3_in_progress', 'background_job_running')
                """))
                stats['research_in_progress'] = result.scalar()
            except Exception as e:
                current_app.logger.warning(f"Error counting research in progress: {e}")
                stats['research_in_progress'] = 0
            
            # Recent activity (last 7 days)
            seven_days_ago = datetime.now() - timedelta(days=7)
            
            try:
                result = conn.execute(text("""
                    SELECT COUNT(*) FROM users 
                    WHERE created_at >= :date
                """), {'date': seven_days_ago})
                stats['new_users_7d'] = result.scalar()
            except Exception as e:
                current_app.logger.warning(f"Error counting new users in 7 days: {e}")
                stats['new_users_7d'] = 0
            
            try:
                result = conn.execute(text("""
                    SELECT COUNT(*) FROM companies 
                    WHERE created_at >= :date
                """), {'date': seven_days_ago})
                stats['new_companies_7d'] = result.scalar()
            except Exception as e:
                current_app.logger.warning(f"Error counting new companies in 7 days: {e}")
                stats['new_companies_7d'] = 0
            
            try:
                result = conn.execute(text("""
                    SELECT COUNT(*) FROM email_history 
                    WHERE date >= :date
                """), {'date': seven_days_ago})
                stats['emails_sent_7d'] = result.scalar()
            except Exception as e:
                current_app.logger.warning(f"Error counting emails sent in 7 days: {e}")
                stats['emails_sent_7d'] = 0
            
            try:
                result = conn.execute(text("""
                    SELECT COUNT(*) FROM companies 
                    WHERE llm_research_completed_at >= :date
                """), {'date': seven_days_ago})
                stats['research_completed_7d'] = result.scalar()
            except Exception as e:
                current_app.logger.warning(f"Error counting research completed in 7 days: {e}")
                stats['research_completed_7d'] = 0
            
            # Top tenants by activity
            try:
                result = conn.execute(text("""
                    SELECT t.name, t.slug, COUNT(u.id) as user_count,
                           (SELECT COUNT(*) FROM companies c WHERE c.tenant_id = t.id) as company_count,
                           (SELECT COUNT(*) FROM contacts ct WHERE ct.tenant_id = t.id) as contact_count
                    FROM tenants t
                    LEFT JOIN users u ON t.id = u.tenant_id
                    GROUP BY t.id, t.name, t.slug
                    ORDER BY user_count DESC, company_count DESC
                    LIMIT 10
                """))
                stats['top_tenants'] = []
                for row in result:
                    stats['top_tenants'].append({
                        'name': row.name,
                        'slug': row.slug,
                        'user_count': row.user_count,
                        'company_count': row.company_count,
                        'contact_count': row.contact_count
                    })
            except Exception as e:
                current_app.logger.warning(f"Error getting top tenants: {e}")
                stats['top_tenants'] = []
            
            # Research status breakdown
            try:
                result = conn.execute(text("""
                    SELECT llm_research_step_status, COUNT(*) as count
                    FROM companies 
                    WHERE llm_research_step_status IS NOT NULL
                    GROUP BY llm_research_step_status
                    ORDER BY count DESC
                """))
                stats['research_status_breakdown'] = []
                for row in result:
                    stats['research_status_breakdown'].append({
                        'status': row.llm_research_step_status,
                        'count': row.count
                    })
            except Exception as e:
                current_app.logger.warning(f"Error getting research status breakdown: {e}")
                stats['research_status_breakdown'] = []
            
            # Recent errors (if any error tracking table exists)
            try:
                result = conn.execute(text("""
                    SELECT COUNT(*) FROM companies 
                    WHERE research_error IS NOT NULL AND research_error != ''
                """))
                stats['companies_with_errors'] = result.scalar()
            except:
                stats['companies_with_errors'] = 0
            
            return jsonify({
                'success': True,
                'stats': stats
            })
        
    except Exception as e:
        current_app.logger.error(f"Error fetching admin stats: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/recent-activity')
@admin_required
def get_recent_activity():
    """Get recent activity across the platform."""
    try:
        from app.database import get_shared_engine
        
        engine = get_shared_engine()
        with engine.connect() as conn:
            activities = []
            
            # Recent users
            result = conn.execute(text("""
                SELECT 'user_created' as type, u.name as description, u.created_at as timestamp, t.name as tenant
                FROM users u
                LEFT JOIN tenants t ON u.tenant_id = t.id
                ORDER BY u.created_at DESC
                LIMIT 10
            """))
            for row in result:
                activities.append({
                    'type': row.type,
                    'description': f"New user: {row.description}",
                    'timestamp': row.timestamp.isoformat() if row.timestamp else None,
                    'tenant': row.tenant
                })
            
            # Recent research completions
            result = conn.execute(text("""
                SELECT 'research_completed' as type, c.company_name as description, 
                       c.llm_research_completed_at as timestamp, t.name as tenant
                FROM companies c
                LEFT JOIN tenants t ON c.tenant_id = t.id
                WHERE c.llm_research_completed_at IS NOT NULL
                ORDER BY c.llm_research_completed_at DESC
                LIMIT 10
            """))
            for row in result:
                activities.append({
                    'type': row.type,
                    'description': f"Research completed: {row.description}",
                    'timestamp': row.timestamp.isoformat() if row.timestamp else None,
                    'tenant': row.tenant
                })
            
            # Sort all activities by timestamp
            activities.sort(key=lambda x: x['timestamp'] or '', reverse=True)
            
            return jsonify({
                'success': True,
                'activities': activities[:20]  # Return top 20
            })
        
    except Exception as e:
        current_app.logger.error(f"Error fetching recent activity: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500