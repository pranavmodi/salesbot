from flask import Blueprint, render_template, request, current_app

from app.models.contact import Contact
from app.models.email_history import EmailHistory
from app.models.company import Company
from app.services.email_reader_service import email_reader, configure_email_reader

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
        threads=get_inbox_threads() # Add threads to dashboard context
    )

def get_inbox_threads():
    """Helper function to fetch and process inbox threads."""
    if not email_reader.connection:
        configure_email_reader()
        if not email_reader.connection:
            if not email_reader.connect():
                current_app.logger.error("Failed to connect to email reader for inbox.")
                return [] # Return empty list on connection failure

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

    threads = email_reader.group_emails_by_thread(emails)
    sorted_threads = sorted(threads.values(), key=lambda t: t[-1]['date'], reverse=True)
    return sorted_threads

@bp.route('/import')
def import_contacts():
    """CSV import page."""
    return render_template('import.html')

@bp.route('/config')
def config():
    """Email configuration page."""
    return render_template('config.html')

 