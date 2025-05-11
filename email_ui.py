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
    leads = load_leads()
    
    if 0 <= lead_index < len(leads):
        lead = leads[lead_index]
        lead_info = {
            'name': lead.get('First Name', ''),
            'email': lead.get('Work Email', ''),
            'company': lead.get('Company', ''),
            'position': lead.get('Position', '')
        }
        
        # Use the preview content instead of generating new content
        if preview_subject and preview_body:
            # Temporarily send to test email instead of lead's email
            test_email = 'pranav.modi@gmail.com'
            success = send_email(test_email, preview_subject, preview_body)
            
            # Create email history entry
            email_data = {
                'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'to': test_email,  # Store test email in history
                'subject': preview_subject,
                'body': preview_body,
                'status': 'Success' if success else 'Failed'
            }
            
            # Save to history
            save_to_history(email_data)
            
            return jsonify({
                'success': success,
                'message': f"Email {'sent' if success else 'failed'} to {test_email}"
            })
    
    return jsonify({
        'success': False,
        'message': 'Invalid lead index or missing preview content'
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True) 