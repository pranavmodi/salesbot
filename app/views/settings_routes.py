from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, session
from app.auth import login_required
from app.models.tenant_settings import TenantSettings
from app.tenant import current_tenant_id
from app.utils.tenant_email_config import TenantEmailConfigManager
from app.database import get_shared_engine
from sqlalchemy import text
import logging
import smtplib
import imaplib
import ssl
import socket

logger = logging.getLogger(__name__)

settings_bp = Blueprint('settings', __name__, url_prefix='/settings')

@settings_bp.route('/')
@login_required
def settings_page():
    """Display tenant settings page."""
    tenant_id = current_tenant_id()
    if not tenant_id:
        flash('No tenant context available', 'error')
        return redirect(url_for('main.index'))
    
    # Get active tab from query parameter (for onboarding flow)
    active_tab = request.args.get('tab', 'general')
    
    try:
        tenant_settings = TenantSettings()
        settings = tenant_settings.get_tenant_settings(tenant_id)
        
        # Get email configurations
        email_manager = TenantEmailConfigManager(tenant_id)
        email_accounts = [acc.to_dict() for acc in email_manager.get_accounts()]
        
        return render_template('settings.html', 
                             settings=settings,
                             active_tab=active_tab,
                             email_accounts=email_accounts)
    
    except Exception as e:
        logger.error(f"Failed to load settings: {e}")
        flash('Failed to load settings', 'error')
        return redirect(url_for('main.index'))

@settings_bp.route('/api-keys', methods=['POST'])
@login_required
def save_api_keys():
    """Save API keys for tenant."""
    tenant_id = current_tenant_id()
    if not tenant_id:
        return jsonify({'error': 'No tenant context'}), 400
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        tenant_settings = TenantSettings()
        current_settings = tenant_settings.get_tenant_settings(tenant_id)
        
        # Update API keys
        if 'openai_api_key' in data:
            current_settings['openai_api_key'] = data['openai_api_key']
        if 'anthropic_api_key' in data:
            current_settings['anthropic_api_key'] = data['anthropic_api_key']
        if 'perplexity_api_key' in data:
            current_settings['perplexity_api_key'] = data['perplexity_api_key']
        
        success = tenant_settings.save_tenant_settings(current_settings, tenant_id)
        
        if success:
            return jsonify({'message': 'API keys saved successfully'})
        else:
            return jsonify({'error': 'Failed to save API keys'}), 500
    
    except Exception as e:
        logger.error(f"Failed to save API keys: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@settings_bp.route('/email-accounts', methods=['POST'])
@login_required
def save_email_accounts():
    """Save email accounts for tenant."""
    tenant_id = current_tenant_id()
    if not tenant_id:
        return jsonify({'error': 'No tenant context'}), 400
    
    try:
        data = request.get_json()
        if not data or 'accounts' not in data:
            return jsonify({'error': 'No accounts provided'}), 400
        
        email_manager = TenantEmailConfigManager(tenant_id)
        success = email_manager.save_accounts(data['accounts'])
        
        if success:
            return jsonify({'message': 'Email accounts saved successfully'})
        else:
            return jsonify({'error': 'Failed to save email accounts'}), 500
    
    except Exception as e:
        logger.error(f"Failed to save email accounts: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@settings_bp.route('/test-email-account', methods=['POST'])
@login_required
def test_email_account():
    """Test email account configuration."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Basic validation
        required_fields = ['email', 'password', 'smtp_host', 'imap_host']
        missing_fields = [field for field in required_fields if not data.get(field)]
        
        if missing_fields:
            return jsonify({
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400
        
        # Test actual email connections
        test_results = _test_email_connections(data)
        
        if test_results['success']:
            return jsonify({
                'message': test_results['message'],
                'status': 'success',
                'details': test_results['details']
            })
        else:
            return jsonify({
                'error': test_results['message'],
                'details': test_results['details']
            }), 400
    
    except Exception as e:
        logger.error(f"Failed to test email account: {e}")
        return jsonify({'error': 'Internal server error'}), 500


def _test_email_connections(config):
    """Test both SMTP and IMAP connections for an email account."""
    results = {
        'success': True,
        'message': '',
        'details': {}
    }
    
    smtp_success = False
    imap_success = False
    
    # Test SMTP connection
    try:
        smtp_port = int(config.get('smtp_port', 465))
        smtp_use_ssl = config.get('smtp_use_ssl', True)
        
        if smtp_use_ssl:
            # Use SSL/TLS (port 465)
            context = ssl.create_default_context()
            server = smtplib.SMTP_SSL(config['smtp_host'], smtp_port, context=context)
        else:
            # Use STARTTLS (port 587)
            server = smtplib.SMTP(config['smtp_host'], smtp_port)
            server.starttls()
        
        # Test authentication
        server.login(config['email'], config['password'])
        server.quit()
        
        smtp_success = True
        results['details']['smtp'] = 'Connection successful'
        
    except smtplib.SMTPAuthenticationError:
        results['details']['smtp'] = 'Authentication failed - check email/password'
    except smtplib.SMTPServerDisconnected:
        results['details']['smtp'] = 'Server disconnected - check host/port'
    except socket.gaierror:
        results['details']['smtp'] = 'Cannot resolve hostname - check SMTP host'
    except Exception as e:
        results['details']['smtp'] = f'Connection failed: {str(e)}'
    
    # Test IMAP connection
    try:
        imap_port = int(config.get('imap_port', 993))
        imap_use_ssl = config.get('imap_use_ssl', True)
        
        if imap_use_ssl:
            # Use SSL (port 993)
            server = imaplib.IMAP4_SSL(config['imap_host'], imap_port)
        else:
            # Use non-SSL (port 143)
            server = imaplib.IMAP4(config['imap_host'], imap_port)
        
        # Test authentication
        server.login(config['email'], config['password'])
        server.logout()
        
        imap_success = True
        results['details']['imap'] = 'Connection successful'
        
    except imaplib.IMAP4.error as e:
        if 'authentication failed' in str(e).lower():
            results['details']['imap'] = 'Authentication failed - check email/password'
        else:
            results['details']['imap'] = f'IMAP error: {str(e)}'
    except socket.gaierror:
        results['details']['imap'] = 'Cannot resolve hostname - check IMAP host'
    except Exception as e:
        results['details']['imap'] = f'Connection failed: {str(e)}'
    
    # Determine overall success
    if smtp_success and imap_success:
        results['message'] = 'Both SMTP and IMAP connections successful'
    elif smtp_success:
        results['message'] = 'SMTP successful, IMAP failed'
        results['success'] = False
    elif imap_success:
        results['message'] = 'IMAP successful, SMTP failed'
        results['success'] = False
    else:
        results['message'] = 'Both SMTP and IMAP connections failed'
        results['success'] = False
    
    return results

@settings_bp.route('/complete-onboarding', methods=['POST'])
@login_required
def complete_onboarding():
    """Mark user's onboarding as complete."""
    try:
        user = session.get('user')
        if not user:
            return jsonify({'success': False, 'error': 'User not found in session'}), 400
            
        # Update user in database
        engine = get_shared_engine()
        with engine.connect() as conn:
            with conn.begin():
                conn.execute(text("""
                    UPDATE users 
                    SET is_first_login = false, updated_at = CURRENT_TIMESTAMP
                    WHERE id = :user_id
                """), {'user_id': user['id']})
        
        # Update session
        session['user']['is_first_login'] = False
        
        return jsonify({'success': True, 'message': 'Onboarding completed successfully'})
        
    except Exception as e:
        logger.error(f"Error completing onboarding: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500