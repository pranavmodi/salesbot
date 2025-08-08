from flask import Blueprint, render_template, request, current_app, Response, jsonify
import os
import json
import uuid
from datetime import datetime
from sqlalchemy import text

from app.models.contact import Contact
from app.models.email_history import EmailHistory
from app.models.company import Company
from app.services.email_reader_service import email_reader, configure_email_reader
from app.services.email_service import EmailService
from app.utils.email_config import email_config

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    """Main CRM dashboard."""
    # Contacts Pagination
    contacts_page = request.args.get('contacts_page', 1, type=int)
    contacts_per_page = request.args.get('per_page', current_app.config['CONTACTS_PER_PAGE'], type=int)
    contact_data = Contact.get_paginated(page=contacts_page, per_page=contacts_per_page)
    
    # Companies Pagination
    companies_page = request.args.get('companies_page', 1, type=int)
    companies_per_page = 15  # Or get from config
    company_data = Company.get_paginated(page=companies_page, per_page=companies_per_page)

    # Get email history and convert to dictionaries for JSON serialization
    email_history_objects = EmailHistory.load_all()
    email_history = [email.to_dict() for email in email_history_objects]
    
    # Calculate stats
    total_contacts = contact_data['total_contacts']
    emails_sent = len(email_history)
    
    # Calculate success rate
    successful_emails = sum(1 for email in email_history if email['status'] == 'Success')
    success_rate = int((successful_emails / emails_sent * 100)) if emails_sent > 0 else 0
    
    # Calculate uncontacted contacts
    if total_contacts > 0:
        all_contacts = Contact.load_all()
        contacted_emails = set()
        for email in email_history_objects:
            if email.to:
                contacted_emails.add(email.to.lower().strip())
        
        uncontacted_count = 0
        for contact in all_contacts:
            if contact.email and contact.email.lower().strip() not in contacted_emails:
                uncontacted_count += 1
    else:
        uncontacted_count = 0
    
    # Get organized inbox threads (Sent/Inbox sections)
    inbox_result = get_inbox_threads()
    inbox_per_page = 10
    inbox_current_page = 1
    
    # Handle both successful organized inbox (dict) and error (dict with 'error' key)
    if isinstance(inbox_result, dict) and 'error' not in inbox_result:
        # Success - organized inbox with sent/inbox sections
        organized_threads = inbox_result
        inbox_error = None
        # Calculate total threads across both sections for pagination
        total_threads = len(organized_threads.get('sent', [])) + len(organized_threads.get('inbox', []))
        inbox_total_pages = max(1, (total_threads + inbox_per_page - 1) // inbox_per_page)
    else:
        # Error case - inbox_result is a dict with 'error' key or wrong format
        organized_threads = {'sent': [], 'inbox': []}
        inbox_error = inbox_result.get('error', 'Unknown error') if isinstance(inbox_result, dict) else 'Unknown error'
        inbox_total_pages = 1
    
    return render_template(
        'dashboard.html',
        contacts=contact_data['contacts'],
        contacts_current_page=contact_data['current_page'],
        contacts_total_pages=contact_data['total_pages'],
        companies=company_data['companies'],
        companies_current_page=company_data['current_page'],
        companies_total_pages=company_data['total_pages'],
        companies_per_page=companies_per_page,
        total_companies=company_data['total_companies'],
        per_page=contact_data['per_page'],
        total_contacts=total_contacts,
        email_history=email_history_objects,  # Keep objects for template iteration
        email_history_json=email_history,     # JSON-serializable version for JavaScript
        emails_sent=emails_sent,
        success_rate=success_rate,
        pending_contacts=len(contact_data['contacts']),
        uncontacted_count=uncontacted_count,
        organized_threads=organized_threads,
        inbox_error=inbox_error,
        inbox_current_page=inbox_current_page,
        inbox_per_page=inbox_per_page,
        inbox_total_pages=inbox_total_pages,
        netlify_publish_url=os.getenv("NETLIFY_PUBLISH_URL", "https://possibleminds.in/.netlify/functions/publish-report-persistent")
    )

def _configure_email_reader_from_accounts():
    """Configure email reader using JSON email accounts."""
    try:
        accounts = email_config.get_all_accounts()
        if not accounts:
            current_app.logger.warning("No email accounts found in JSON config")
            return False
        
        # Use the first account for inbox reading
        account = accounts[0]
        if not all([account.imap_host, account.email, account.password]):
            current_app.logger.warning(f"Incomplete IMAP configuration for account {account.email}")
            return False
            
        email_reader.configure_imap(
            host=account.imap_host,
            email=account.email, 
            password=account.password,
            port=account.imap_port
        )
        current_app.logger.info(f"Configured email reader for {account.email}")
        return True
        
    except Exception as e:
        current_app.logger.error(f"Error configuring email reader from accounts: {e}")
        return False

def get_inbox_threads():
    """Helper function to fetch and organize inbox threads by Sent/Inbox sections."""
    if not email_reader.connection:
        # Use JSON email accounts instead of environment variables
        if not _configure_email_reader_from_accounts():
            current_app.logger.error("Failed to configure email reader for inbox.")
            return {'error': 'Email accounts not configured properly'}
        if not email_reader.connect():
            current_app.logger.error("Failed to connect to email reader for inbox.")
            return {'error': 'Cannot connect to email server (IMAP may not be enabled)'}

    emails = []
    for folder in ['INBOX', 'Sent']:
        try:
            # Check if connection is alive, otherwise reconnect
            status, _ = email_reader.connection.noop()
            if status != 'OK':
                email_reader.connect()

            email_reader.connection.select(folder, readonly=True)
            status, message_ids = email_reader.connection.search(None, 'ALL')
            if status == 'OK' and message_ids[0]:
                ids = message_ids[0].split()
                # Fetch recent emails, e.g., last 50
                for msg_id in ids[-50:]:
                    email_data = email_reader._fetch_email_data(msg_id, folder)
                    if email_data:
                        emails.append(email_data)
        except Exception as e:
            current_app.logger.warning(f"Error fetching emails from {folder}: {e}")
            # Attempt to reconnect on error
            email_reader.connect()

    # Group emails into threads
    threads = email_reader.group_emails_by_thread(emails)
    
    # Organize threads by Sent vs Inbox
    organized_threads = _organize_threads_by_folder(threads)
    return organized_threads

def _organize_threads_by_folder(threads):
    """Organize email threads into Sent and Inbox sections."""
    from app.utils.email_config import email_config
    
    # Get our email addresses to identify sent vs received
    our_emails = {acc.email.lower() for acc in email_config.get_all_accounts()}
    
    organized = {
        'sent': [],      # Threads where we sent the latest message
        'inbox': []      # Threads where we received the latest message
    }
    
    for thread_emails in threads.values():
        if not thread_emails:
            continue
            
        latest_email = thread_emails[-1]
        
        # Determine if latest email is from us or them
        latest_from_us = latest_email.get('from', '').lower() in our_emails
        
        if latest_from_us:
            organized['sent'].append(thread_emails)
        else:
            organized['inbox'].append(thread_emails)
    
    # Sort each section by date (most recent first)
    for section in organized:
        organized[section].sort(key=lambda t: t[-1].get('date', datetime.min), reverse=True)
    
    return organized

@bp.route('/import')
def import_contacts():
    """CSV import page."""
    return render_template('import.html')

@bp.route('/config')
def config():
    """Email configuration page."""
    return render_template('config.html')

@bp.route('/api/track/open/<tracking_id>.png')
def track_email_open(tracking_id):
    """Handle email open tracking pixel requests."""
    try:
        from app.database import get_shared_engine
        
        engine = get_shared_engine()
        with engine.connect() as conn:
            with conn.begin():
                # Update the opened_at timestamp for this tracking ID
                result = conn.execute(text("""
                    UPDATE email_tracking 
                    SET opened_at = CURRENT_TIMESTAMP 
                    WHERE tracking_id = :tracking_id 
                    AND opened_at IS NULL
                    RETURNING company_id, recipient_email, campaign_id
                """), {'tracking_id': tracking_id})
                
                row = result.fetchone()
                if row:
                    current_app.logger.info(f"📧 Email opened: tracking_id={tracking_id}, company_id={row[0]}, recipient={row[1]}, campaign_id={row[2]}")
                else:
                    current_app.logger.info(f"📧 Email open tracking: tracking_id={tracking_id} (already tracked or not found)")
                
    except Exception as e:
        current_app.logger.error(f"Error tracking email open: {e}")
        # Still return pixel even if tracking fails
    
    # Return a transparent 1x1 PNG pixel
    # Base64 encoded transparent PNG pixel data
    pixel_data = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=='
    
    import base64
    pixel_bytes = base64.b64decode(pixel_data)
    
    response = Response(pixel_bytes, mimetype='image/png')
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response

@bp.route('/api/send-followup', methods=['POST'])
def send_followup():
    """Send a follow-up email."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
            
        recipient = data.get('recipient')
        subject = data.get('subject')
        body = data.get('body')
        include_tracking = data.get('include_tracking', True)
        
        if not all([recipient, subject, body]):
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
            
        # Initialize email service
        email_service = EmailService()
        
        # Generate tracking ID if tracking is enabled
        tracking_id = str(uuid.uuid4()) if include_tracking else None
        
        # Add tracking pixel to email body if enabled
        email_body = body
        if include_tracking and tracking_id:
            tracking_pixel = f'<img src="{request.url_root}api/track/open/{tracking_id}.png" width="1" height="1" style="display:none;" />'
            email_body = f"{body}\n\n{tracking_pixel}"
        
        # Send the email
        success = email_service.send_email(
            to_email=recipient,
            subject=subject,
            body=email_body,
            tracking_id=tracking_id
        )
        
        if success:
            # Save to email history
            email_history = EmailHistory(
                to=recipient,
                subject=subject,
                body=body,
                status='Success',
                sent_at=datetime.now(),
                tracking_id=tracking_id
            )
            email_history.save()
            
            current_app.logger.info(f"Follow-up email sent successfully to {recipient}")
            return jsonify({'success': True, 'message': 'Follow-up email sent successfully'})
        else:
            current_app.logger.error(f"Failed to send follow-up email to {recipient}")
            return jsonify({'success': False, 'error': 'Failed to send email'}), 500
            
    except Exception as e:
        current_app.logger.error(f"Error sending follow-up email: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/refresh-emails', methods=['POST'])
def refresh_emails():
    """Refresh and fetch the latest emails."""
    try:
        # Get organized inbox threads by pipeline
        inbox_result = get_inbox_threads()
        
        # Handle both successful organized inbox (dict) and error (dict with 'error' key)
        if isinstance(inbox_result, dict) and 'error' not in inbox_result:
            # Success - organized inbox with sent/inbox sections
            organized_threads = inbox_result
            
            # Calculate totals
            inbox_count = len(organized_threads.get('inbox', []))
            sent_count = len(organized_threads.get('sent', []))
            total_count = inbox_count + sent_count
            
            current_app.logger.info(f"Refreshed emails: {inbox_count} inbox, {sent_count} sent")
            
            return jsonify({
                'success': True,
                'inbox_count': inbox_count,
                'sent_count': sent_count,
                'total_count': total_count,
                'message': f'Refreshed {total_count} conversations'
            })
        else:
            # Error case
            error_msg = inbox_result.get('error', 'Unknown error') if isinstance(inbox_result, dict) else 'Unknown error'
            current_app.logger.error(f"Failed to refresh emails: {error_msg}")
            return jsonify({'success': False, 'error': error_msg}), 500
            
    except Exception as e:
        current_app.logger.error(f"Error refreshing emails: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/generate-followup-draft', methods=['POST'])
def generate_followup_draft():
    """Generate an AI draft for follow-up email using OpenAI."""
    try:
        import openai
        import os
        
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
            
        recipient = data.get('recipient')
        subject = data.get('subject')
        original_context = data.get('original_context', '')
        
        if not all([recipient, subject]):
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        # Set up OpenAI client
        openai.api_key = os.getenv('OPENAI_API_KEY')
        if not openai.api_key:
            return jsonify({'success': False, 'error': 'OpenAI API key not configured'}), 500
        
        # Prepare the prompt for follow-up generation
        prompt = f"""You are a professional sales assistant. Generate a polite, concise follow-up email based on the context below.

CONTEXT:
- Recipient: {recipient}
- Original Subject: {subject}
- Previous Email Context: {original_context[:1000] if original_context else 'No previous context available'}

REQUIREMENTS:
- Write a polite, professional follow-up email
- Keep it concise (2-3 short paragraphs maximum)
- Reference the previous communication appropriately
- Include a gentle call-to-action
- Use a warm but professional tone
- Don't be pushy or aggressive
- Make it sound natural and human

Generate only the email body text, no subject line or signatures."""

        # Call OpenAI API
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a professional email writing assistant specializing in sales follow-ups."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300,
            temperature=0.7
        )
        
        draft_content = response.choices[0].message.content.strip()
        
        current_app.logger.info(f"Generated AI draft for follow-up to {recipient}")
        
        return jsonify({
            'success': True,
            'draft': draft_content,
            'message': 'AI draft generated successfully'
        })
        
    except ImportError:
        current_app.logger.error("OpenAI library not installed")
        return jsonify({'success': False, 'error': 'OpenAI library not available'}), 500
    except Exception as e:
        current_app.logger.error(f"Error generating AI draft: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

 