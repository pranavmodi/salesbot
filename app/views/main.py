from flask import Blueprint, render_template, request, current_app

from app.models.contact import Contact
from app.models.email_history import EmailHistory

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    """Main CRM dashboard."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', current_app.config['CONTACTS_PER_PAGE'], type=int)
    
    # Get paginated contacts
    contact_data = Contact.get_paginated(page=page, per_page=per_page)
    
    # Get email history and convert to dictionaries for JSON serialization
    email_history_objects = EmailHistory.load_all()
    email_history = [email.to_dict() for email in email_history_objects]
    
    # Calculate stats
    total_contacts = contact_data['total_contacts']
    emails_sent = len(email_history)
    
    # Calculate success rate
    successful_emails = sum(1 for email in email_history if email['status'] == 'Success')
    success_rate = int((successful_emails / emails_sent * 100)) if emails_sent > 0 else 0
    
    return render_template(
        'dashboard.html',
        contacts=contact_data['contacts'],
        current_page=contact_data['current_page'],
        total_pages=contact_data['total_pages'],
        per_page=contact_data['per_page'],
        total_contacts=total_contacts,
        email_history=email_history_objects,  # Keep objects for template iteration
        email_history_json=email_history,     # JSON-serializable version for JavaScript
        emails_sent=emails_sent,
        success_rate=success_rate,
        pending_contacts=len(contact_data['contacts'])
    ) 