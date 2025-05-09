from flask import Flask, render_template, request, jsonify, redirect, url_for
import csv
from send_emails import send_email
from email_composer import EmailComposer
from datetime import datetime
import os

app = Flask(__name__)
composer = EmailComposer()

# Initialize email history file
HISTORY_FILE = 'email_history.csv'
if not os.path.exists(HISTORY_FILE):
    with open(HISTORY_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['date', 'to', 'subject', 'body', 'status'])

def load_leads():
    leads = []
    try:
        with open('dummy_leads.csv', mode='r', encoding='utf-8') as file:
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
    leads = load_leads()
    history = load_history()
    return render_template('index.html', leads=leads, history=history)

@app.route('/preview_email', methods=['POST'])
def preview_email():
    lead_info = request.json
    email_content = composer.compose_email(lead_info)
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
    leads = load_leads()
    
    if 0 <= lead_index < len(leads):
        lead = leads[lead_index]
        lead_info = {
            'name': lead.get('First Name', ''),
            'email': lead.get('Work Email', ''),
            'company': lead.get('Company', ''),
            'position': lead.get('Position', '')
        }
        
        email_content = composer.compose_email(lead_info)
        if email_content:
            success = send_email(lead_info['email'], email_content['subject'], email_content['body'])
            
            # Create email history entry
            email_data = {
                'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'to': lead_info['email'],
                'subject': email_content['subject'],
                'body': email_content['body'],
                'status': 'Success' if success else 'Failed'
            }
            
            # Save to history
            save_to_history(email_data)
            
            return jsonify({
                'success': success,
                'message': f"Email {'sent' if success else 'failed'} to {lead_info['email']}"
            })
    
    return jsonify({
        'success': False,
        'message': 'Invalid lead index'
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True) 