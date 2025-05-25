from flask import Blueprint, request, jsonify, current_app

from app.models.contact import Contact
from app.services.email_service import EmailService

bp = Blueprint('api', __name__)

@bp.route('/preview_email', methods=['POST'])
def preview_email():
    """Generate email preview for a contact."""
    try:
        contact_data = request.get_json()
        
        if not contact_data:
            return jsonify({'error': 'No contact data provided'}), 400
        
        email_content = EmailService.compose_email(contact_data)
        
        if email_content:
            return jsonify(email_content)
        else:
            return jsonify({'error': 'Failed to generate email content'}), 500
            
    except Exception as e:
        current_app.logger.error(f"Error in preview_email: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/send_email', methods=['POST'])
def send_email():
    """Send an email to a specific recipient."""
    try:
        recipient_email = request.form.get('recipient_email')
        recipient_name = request.form.get('recipient_name')
        subject = request.form.get('preview_subject')
        body = request.form.get('preview_body')
        
        if not all([recipient_email, recipient_name, subject, body]):
            return jsonify({
                'success': False,
                'message': 'Missing required email information'
            }), 400
        
        success = EmailService.send_email(recipient_email, recipient_name, subject, body)
        
        return jsonify({
            'success': success,
            'message': f"Email {'sent' if success else 'failed'} to {recipient_email}"
        })
        
    except Exception as e:
        current_app.logger.error(f"Error in send_email: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Internal server error'
        }), 500

@bp.route('/send_bulk_emails', methods=['POST'])
def send_bulk_emails():
    """Send emails to multiple recipients."""
    try:
        data = request.get_json()
        recipients = data.get('recipients', [])
        
        if not recipients:
            return jsonify({
                'success': False,
                'message': 'No recipients provided'
            }), 400
        
        results = EmailService.send_bulk_emails(recipients)
        
        return jsonify({
            'success': results['failed'] == 0,
            'results': results,
            'message': f"Successfully sent {results['success']} emails. Failed to send {results['failed']} emails."
        })
        
    except Exception as e:
        current_app.logger.error(f"Error in send_bulk_emails: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Internal server error'
        }), 500

@bp.route('/get_unsent_leads', methods=['GET'])
def get_unsent_leads():
    """Get contacts who haven't received emails yet."""
    try:
        unsent_contacts = EmailService.get_unsent_contacts()
        
        return jsonify({
            'unsent_leads': [contact.raw_data for contact in unsent_contacts],
            'count': len(unsent_contacts)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error in get_unsent_leads: {str(e)}")
        return jsonify({
            'unsent_leads': [],
            'count': 0,
            'error': 'Failed to load unsent leads'
        }), 500

@bp.route('/contacts', methods=['GET'])
def get_contacts():
    """Get paginated contacts."""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', current_app.config['CONTACTS_PER_PAGE'], type=int)
        
        contact_data = Contact.get_paginated(page=page, per_page=per_page)
        
        return jsonify({
            'contacts': [contact.to_dict() for contact in contact_data['contacts']],
            'current_page': contact_data['current_page'],
            'total_pages': contact_data['total_pages'],
            'per_page': contact_data['per_page'],
            'total_contacts': contact_data['total_contacts']
        })
        
    except Exception as e:
        current_app.logger.error(f"Error in get_contacts: {str(e)}")
        return jsonify({'error': 'Failed to load contacts'}), 500

@bp.route('/search_contacts', methods=['GET'])
def search_contacts():
    """Search contacts by query."""
    try:
        query = request.args.get('q', '').strip()
        
        if not query:
            return jsonify({'contacts': [], 'count': 0})
        
        contacts = Contact.search(query)
        
        return jsonify({
            'contacts': [contact.to_dict() for contact in contacts],
            'count': len(contacts)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error in search_contacts: {str(e)}")
        return jsonify({'error': 'Failed to search contacts'}), 500 