from flask import Flask, render_template, request, jsonify, redirect, url_for
from send_emails import send_email
from composer_instance import composer
from datetime import datetime
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
import logging

app = Flask(__name__)
load_dotenv() # Load environment variables

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DATABASE_URL = os.getenv("DATABASE_URL")

def get_db_engine():
    if not DATABASE_URL:
        logging.error("DATABASE_URL not configured.")
        return None
    try:
        engine = create_engine(DATABASE_URL)
        return engine
    except Exception as e:
        logging.error(f"Error creating database engine: {e}")
        return None

def load_leads():
    """Load leads from PostgreSQL database."""
    leads = []
    engine = get_db_engine()
    if not engine:
        return leads
        
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT email, first_name, last_name, full_name, job_title, 
                       company_name, company_domain, linkedin_profile, location, 
                       phone, linkedin_message, created_at, updated_at
                FROM contacts 
                WHERE email IS NOT NULL AND email != ''
                ORDER BY created_at DESC
            """))
            
            for row in result:
                contact_data = dict(row._mapping)
                # Convert to the format expected by the UI (maintaining backward compatibility)
                lead_data = {
                    'First Name': contact_data.get('first_name', ''),
                    'Last Name': contact_data.get('last_name', ''),
                    'Full Name': contact_data.get('full_name', ''),
                    'Work Email': contact_data.get('email', ''),
                    'Company Name': contact_data.get('company_name', ''),
                    'Job Title': contact_data.get('job_title', ''),
                    'Location': contact_data.get('location', ''),
                    'LinkedIn Profile': contact_data.get('linkedin_profile', ''),
                    'Company Domain': contact_data.get('company_domain', ''),
                    'Position': contact_data.get('job_title', ''),  # Alias for compatibility
                    'Company': contact_data.get('company_name', ''),  # Alias for compatibility
                }
                leads.append(lead_data)
                
    except SQLAlchemyError as e:
        logging.error(f"Error loading leads from database: {e}")
    except Exception as e:
        logging.error(f"Unexpected error loading leads: {e}")
        
    return leads

def load_history():
    engine = get_db_engine()
    if not engine:
        return []
    history = []
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT id, date, \"to\", subject, body, status FROM email_history ORDER BY date DESC"))
            for row in result:
                # Convert row to a dictionary-like object or a plain dictionary
                # The template likely expects dictionary access (e.g., email['subject'])
                history.append(dict(row._mapping)) # _mapping gives dict-like access to columns
        logging.info(f"Loaded {len(history)} records from email_history table.")
    except SQLAlchemyError as e:
        logging.error(f"Error loading history from database: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred while loading history: {e}")
    return history

def save_to_history(email_data):
    engine = get_db_engine()
    if not engine:
        logging.error("Failed to save to history: Database engine not available.")
        return

    try:
        # Ensure date is in correct format or a datetime object
        # The email_data['date'] is already a string from strftime
        # The database expects a datetime object or a string that it can parse.
        # If email_data['date'] is a string like "YYYY-MM-DD HH:MM:SS", it should work.
        # For robustness, ensure it's a datetime object if not already:
        if isinstance(email_data.get('date'), str):
            email_data['date'] = datetime.strptime(email_data['date'], "%Y-%m-%d %H:%M:%S")

        with engine.connect() as connection:
            with connection.begin(): # Start a transaction
                insert_query = text(
                    'INSERT INTO email_history (date, "to", subject, body, status) '
                    'VALUES (:date, :to, :subject, :body, :status)'
                )
                connection.execute(insert_query, {
                    'date': email_data['date'],
                    'to': email_data['to'],
                    'subject': email_data['subject'],
                    'body': email_data['body'], # CSV version had .replace('\\n', '\\\\n'), ensure this is handled or not needed
                    'status': email_data['status']
                })
            logging.info(f"Successfully saved email to {email_data['to']} to history database.")
    except SQLAlchemyError as e:
        logging.error(f"Database error saving to history: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred while saving to history: {e}")

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