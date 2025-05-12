from flask import Flask, render_template, request, jsonify, redirect, url_for
import csv
from send_emails import send_email
from composer_instance import composer
from datetime import datetime
import os

app = Flask(__name__)

# Initialize email history file
HISTORY_FILE = 'email_history.csv'
if not os.path.exists(HISTORY_FILE):
    with open(HISTORY_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['date', 'to', 'subject', 'body', 'status'])

def load_leads():
    leads = []
    try:
        with open('leads_with_messages.csv', mode='r', encoding='utf-8') as file:
            csv_reader = csv.DictReader(file)
            for row in csv_reader:
                leads.append(row)
    except Exception as e:
        print(f"Error loading leads: {str(e)}")
    return leads

def load_history():
    history = []
    try:
        with open(HISTORY_FILE, mode='r', encoding='utf-8') as file:
            csv_reader = csv.DictReader(file)
            for row in csv_reader:
                history.append(row)
    except Exception as e:
        print(f"Error loading history: {str(e)}")
    return history

def save_to_history(email_data):
    with open(HISTORY_FILE, 'a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow([
            email_data['date'],
            email_data['to'],
            email_data['subject'],
            email_data['body'].replace('\n', '\\n'),
            email_data['status']
        ])

@app.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 1, type=int)  # Default to 1 for debugging
    leads = load_leads()
    history = load_history()
    
    # Calculate pagination for leads
    total_leads = len(leads)
    total_pages = (total_leads + per_page - 1) // per_page
    start_idx = (page - 1) * per_page
    end_idx = min(start_idx + per_page, total_leads)
    paginated_leads = leads[start_idx:end_idx]
    
    return render_template('index.html', 
                         leads=paginated_leads, 
                         history=history,
                         current_page=page,
                         total_pages=total_pages,
                         per_page=per_page,
                         total_leads=total_leads)

@app.route('/get_leads')
def get_leads():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 3, type=int)
    leads = load_leads()
    
    # Calculate pagination
    total_leads = len(leads)
    total_pages = (total_leads + per_page - 1) // per_page
    start_idx = (page - 1) * per_page
    end_idx = min(start_idx + per_page, total_leads)
    paginated_leads = leads[start_idx:end_idx]
    
    return jsonify({
        'leads': paginated_leads,
        'current_page': page,
        'total_pages': total_pages,
        'per_page': per_page,
        'total_leads': total_leads
    })

@app.route('/get_unsent_leads')
def get_unsent_leads():
    """Identify leads who haven't received emails yet"""
    leads = load_leads()
    history = load_history()
    
    # Create a set of emails that have been sent to already
    sent_emails = {record['to'].lower() for record in history}
    
    # Filter leads that haven't been sent emails
    unsent_leads = []
    for lead in leads:
        # Skip leads without email addresses
        if not lead.get('Work Email'):
            continue
            
        email = lead['Work Email'].lower()
        if email and email not in sent_emails:
            unsent_leads.append(lead)
    
    return jsonify({
        'unsent_leads': unsent_leads,
        'count': len(unsent_leads)
    })

@app.route('/preview_email', methods=['POST'])
def preview_email():
    lead_info = request.json
    print("Received lead info:", lead_info)  # Debug log
    email_content = composer.compose_email(lead_info)
    print("Generated email content:", email_content)  # Debug log
    if email_content:
        return jsonify({
            'subject': email_content['subject'],
            'body': email_content['body']
        })
    return jsonify({
        'subject': 'Error',
        'body': 'Failed to generate email content'
    }), 400

@app.route('/send_email', methods=['POST'])
def send_email_route():
    lead_index = int(request.form.get('lead_index'))
    preview_subject = request.form.get('preview_subject')  # Get the preview subject
    preview_body = request.form.get('preview_body')        # Get the preview body
    
    # Get recipient information directly from form data
    recipient_email = request.form.get('recipient_email')
    recipient_name = request.form.get('recipient_name')
    
    # Validation
    if not (preview_subject and preview_body and recipient_email):
        return jsonify({
            'success': False,
            'message': 'Missing required email information'
        })
    
    # Use the preview content directly with the specified recipient
    success = send_email(recipient_email, preview_subject, preview_body)
    
    # Create email history entry
    email_data = {
        'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'to': recipient_email,  # Store the explicit recipient email
        'subject': preview_subject,
        'body': preview_body,
        'status': 'Success' if success else 'Failed'
    }
    
    # Save to history
    save_to_history(email_data)
    
    return jsonify({
        'success': success,
        'message': f"Email {'sent' if success else 'failed'} to {recipient_email}"
    })

@app.route('/send_bulk_emails', methods=['POST'])
def send_bulk_emails():
    """Send emails to multiple leads"""
    data = request.json
    recipients = data.get('recipients', [])
    
    if not recipients:
        return jsonify({
            'success': False,
            'message': 'No recipients provided'
        })
    
    results = {
        'success': 0,
        'failed': 0,
        'failures': []
    }
    
    for recipient in recipients:
        lead_info = {
            'name': recipient.get('First Name', ''),
            'email': recipient.get('Work Email', ''),
            'company': recipient.get('Company Name', ''),
            'position': recipient.get('Job Title', '')
        }
        
        # Skip if no email is provided
        if not lead_info['email']:
            results['failed'] += 1
            results['failures'].append({
                'name': lead_info['name'], 
                'reason': 'Missing email address'
            })
            continue
        
        # Generate email content
        email_content = composer.compose_email(lead_info)
        
        if not email_content:
            results['failed'] += 1
            results['failures'].append({
                'name': lead_info['name'],
                'email': lead_info['email'],
                'reason': 'Failed to generate email content'
            })
            continue
        
        # Send the email
        success = send_email(lead_info['email'], email_content['subject'], email_content['body'])
        
        if success:
            results['success'] += 1
            # Save to history
            email_data = {
                'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'to': lead_info['email'],
                'subject': email_content['subject'],
                'body': email_content['body'],
                'status': 'Success'
            }
            save_to_history(email_data)
        else:
            results['failed'] += 1
            results['failures'].append({
                'name': lead_info['name'],
                'email': lead_info['email'],
                'reason': 'Failed to send email'
            })
    
    return jsonify({
        'success': results['failed'] == 0,
        'results': results,
        'message': f"Successfully sent {results['success']} emails. Failed to send {results['failed']} emails."
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True) 