from flask import Blueprint, request, jsonify, current_app

from app.models.contact import Contact
from app.services.email_service import EmailService
from app.services.email_reader_service import email_reader, configure_email_reader, EMAIL_READING_ENABLED
import os
import tempfile
import pandas as pd
import numpy as np
from data_ingestion_system import ContactDataIngester
from app.models.email_history import EmailHistory

bp = Blueprint('api', __name__, url_prefix='/api')

def clean_data_for_json(data):
    """Clean pandas data for JSON serialization by handling NaN values and other types."""
    if isinstance(data, dict):
        return {k: clean_data_for_json(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [clean_data_for_json(item) for item in data]
    elif pd.isna(data) or data is np.nan:
        return None
    elif isinstance(data, (np.integer, np.int64)):
        return int(data)
    elif isinstance(data, (np.floating, np.float64)):
        return float(data) if not pd.isna(data) else None
    elif isinstance(data, np.bool_):
        return bool(data)
    elif isinstance(data, (pd.Timestamp, np.datetime64)):
        return data.isoformat() if not pd.isna(data) else None
    else:
        return str(data) if data is not None else None

@bp.route('/contacts', methods=['GET'])
def get_contacts():
    """Get all contacts."""
    try:
        contacts = Contact.load_all()
        return jsonify([contact.to_dict() for contact in contacts])
    except Exception as e:
        current_app.logger.error(f"Error getting contacts: {str(e)}")
        return jsonify({'error': 'Failed to load contacts'}), 500

@bp.route('/contact/<email>', methods=['GET'])
def get_contact(email):
    """Get a specific contact by email."""
    try:
        contacts = Contact.search(email)
        if contacts:
            return jsonify(contacts[0].to_dict())
        return jsonify({'error': 'Contact not found'}), 404
    except Exception as e:
        current_app.logger.error(f"Error getting contact: {str(e)}")
        return jsonify({'error': 'Failed to load contact'}), 500

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
        current_app.logger.error(f"Error generating email preview: {str(e)}")
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

# New Email Reading Endpoints

@bp.route('/email/configure', methods=['POST'])
def configure_email():
    """Configure email reading service."""
    try:
        success = configure_email_reader()
        return jsonify({
            'success': success,
            'message': 'Email reader configured successfully' if success else 'Failed to configure email reader'
        })
    except Exception as e:
        current_app.logger.error(f"Error configuring email reader: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to configure email reader'
        }), 500

@bp.route('/email/conversations/<contact_email>', methods=['GET'])
def get_contact_conversations(contact_email):
    """Get email conversations with a specific contact."""
    try:
        # Check if email reading feature is enabled
        if not EMAIL_READING_ENABLED:
            return jsonify({
                'error': 'Email reading feature is currently disabled',
                'message': 'Email conversation access requires IMAP access, which needs a plan upgrade. This feature is temporarily disabled.',
                'feature_disabled': True
            }), 503
        
        # Get query parameters
        days_back = request.args.get('days_back', 365, type=int)
        
        # Configure email reader if not already done
        if not email_reader.connection:
            success = configure_email_reader()
            if not success:
                return jsonify({
                    'error': 'Email reader not configured',
                    'message': 'Please check email credentials'
                }), 503
        
        # Get conversation summary
        conversation_data = email_reader.get_conversation_summary(contact_email)
        
        return jsonify({
            'contact_email': contact_email,
            'conversation_summary': conversation_data,
            'success': True
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting conversations for {contact_email}: {str(e)}")
        return jsonify({
            'error': 'Failed to retrieve conversations',
            'message': str(e)
        }), 500

@bp.route('/email/conversations/<contact_email>/detailed', methods=['GET'])
def get_detailed_conversations(contact_email):
    """Get detailed email conversations with threading."""
    try:
        # Check if email reading feature is enabled
        if not EMAIL_READING_ENABLED:
            return jsonify({
                'error': 'Email reading feature is currently disabled',
                'message': 'Email conversation access requires IMAP access, which needs a plan upgrade. This feature is temporarily disabled.',
                'feature_disabled': True
            }), 503
            
        days_back = request.args.get('days_back', 365, type=int)
        
        # Configure email reader if needed
        if not email_reader.connection:
            success = configure_email_reader()
            if not success:
                return jsonify({
                    'error': 'Email reader not configured'
                }), 503
        
        # Get all conversations
        conversations = email_reader.search_conversations_with_contact(contact_email, days_back)
        
        # Group by threads
        threads = email_reader.group_emails_by_thread(conversations)
        
        # Format for JSON serialization
        formatted_threads = {}
        for thread_id, emails in threads.items():
            formatted_emails = []
            for email_data in emails:
                formatted_email = {
                    'id': email_data['id'],
                    'subject': email_data['subject'],
                    'from': email_data['from'],
                    'to': email_data['to'],
                    'date': email_data['date'].isoformat() if email_data['date'] else None,
                    'body': email_data['body'][:500] + '...' if len(email_data['body']) > 500 else email_data['body'],
                    'direction': email_data['direction'],
                    'folder': email_data['folder']
                }
                formatted_emails.append(formatted_email)
            
            formatted_threads[thread_id] = {
                'thread_id': thread_id,
                'email_count': len(formatted_emails),
                'emails': formatted_emails
            }
        
        return jsonify({
            'contact_email': contact_email,
            'total_emails': len(conversations),
            'thread_count': len(threads),
            'threads': formatted_threads,
            'success': True
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting detailed conversations: {str(e)}")
        return jsonify({
            'error': 'Failed to retrieve detailed conversations',
            'message': str(e)
        }), 500

@bp.route('/email/test-connection', methods=['POST'])
def test_email_connection():
    """Test email connection."""
    try:
        # Check if email reading feature is enabled
        if not EMAIL_READING_ENABLED:
            return jsonify({
                'success': False,
                'message': 'Email reading feature is currently disabled. This feature requires IMAP access which needs a plan upgrade.',
                'feature_disabled': True
            })
        
        # Configure email reader
        success = configure_email_reader()
        if not success:
            return jsonify({
                'success': False,
                'message': 'Failed to configure email reader - check SENDER_EMAIL and SENDER_PASSWORD environment variables'
            })
        
        # Test connection
        connected = email_reader.connect()
        
        if connected:
            # Try to list folders to verify access
            try:
                status, folders = email_reader.connection.list()
                folder_count = len(folders) if folders else 0
                email_reader.disconnect()
                
                return jsonify({
                    'success': True,
                    'message': f'Successfully connected to email account',
                    'email': email_reader.email,
                    'imap_host': email_reader.imap_host,
                    'folder_count': folder_count
                })
            except Exception as e:
                return jsonify({
                    'success': False,
                    'message': f'Connected but failed to access folders: {str(e)}'
                })
        else:
            # Check if it's an IMAP not enabled error
            error_message = 'Failed to connect to email server'
            
            # Try to extract more specific error information from logs
            # This is a simplified approach - in a real scenario you'd want to capture the actual error
            if email_reader.email and 'possibleminds.in' in email_reader.email:
                error_message = '''IMAP access not enabled for your Zoho account. 

To enable IMAP access:
1. Login to Zoho Mail (www.zoho.com/mail)
2. Go to Settings > Mail Accounts
3. Click on your email address
4. Under IMAP section, check "IMAP Access"
5. Click Save

Then try testing the connection again.'''
            
            return jsonify({
                'success': False,
                'message': error_message,
                'help_url': 'https://www.zoho.com/mail/help/imap-access.html'
            })
            
    except Exception as e:
        current_app.logger.error(f"Error testing email connection: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Connection test failed: {str(e)}'
        }), 500

@bp.route('/contacts/export', methods=['GET'])
def export_contacts():
    """Export contacts to CSV."""
    try:
        import csv
        import io
        
        contacts = Contact.load_all()
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['Email', 'First Name', 'Last Name', 'Full Name', 'Company', 
                        'Job Title', 'Location', 'LinkedIn Profile', 'Company Domain'])
        
        # Write contact data
        for contact in contacts:
            writer.writerow([
                contact.email,
                contact.first_name,
                contact.last_name,
                contact.full_name,
                contact.company,
                contact.job_title,
                contact.location,
                contact.linkedin_profile,
                contact.company_domain
            ])
        
        output.seek(0)
        
        from flask import Response
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={"Content-disposition": "attachment; filename=contacts.csv"}
        )
        
    except Exception as e:
        current_app.logger.error(f"Error exporting contacts: {str(e)}")
        return jsonify({'error': 'Failed to export contacts'}), 500

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

@bp.route('/contacts/import', methods=['POST'])
def import_contacts():
    """Import contacts from uploaded CSV file."""
    try:
        # Check if file was uploaded
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not file.filename.endswith('.csv'):
            return jsonify({'error': 'File must be a CSV'}), 400
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.csv', delete=False) as temp_file:
            file.save(temp_file.name)
            temp_file_path = temp_file.name
        
        try:
            # Read CSV file with better encoding handling
            try:
                df = pd.read_csv(temp_file_path)
            except UnicodeDecodeError:
                # Try with different encoding
                df = pd.read_csv(temp_file_path, encoding='latin-1')
            except Exception as e:
                raise Exception(f"Could not read CSV file. Please ensure it's a valid CSV format. Error: {str(e)}")
            
            # Check if DataFrame is empty
            if df.empty:
                raise Exception("CSV file is empty or contains no valid data")
            
            # Log basic info about the file
            current_app.logger.info(f"Processing CSV: {file.filename}, Shape: {df.shape}, Columns: {list(df.columns)}")
            
            # Check for basic data quality issues
            if len(df.columns) == 0:
                raise Exception("CSV file has no columns")
            
            # Initialize data ingester
            ingester = ContactDataIngester()
            ingester.connect_db()
            
            # Get statistics before import
            stats_before = ingester.get_statistics()
            contacts_before = stats_before['total_contacts']
            
            # Process the CSV file
            total_rows, successful_inserts, errors = ingester.process_csv_file(temp_file_path)
            
            # Get statistics after import
            stats_after = ingester.get_statistics()
            contacts_after = stats_after['total_contacts']
            
            # Calculate duplicates (rows that didn't increase total count)
            new_contacts = contacts_after - contacts_before
            duplicates = successful_inserts - new_contacts
            
            # Read CSV to get column preview
            try:
                df = pd.read_csv(temp_file_path)
            except UnicodeDecodeError:
                df = pd.read_csv(temp_file_path, encoding='latin-1')
            except Exception as e:
                raise Exception(f"Could not read CSV file for preview. Error: {str(e)}")
            
            columns = df.columns.tolist()
            sample_data_raw = df.head(3).to_dict('records') if len(df) > 0 else []
            sample_data = clean_data_for_json(sample_data_raw)
            
            # Clean up temporary file
            os.unlink(temp_file_path)
            
            return jsonify({
                'success': True,
                'statistics': {
                    'total_rows': total_rows,
                    'successful_inserts': successful_inserts,
                    'new_contacts': new_contacts,
                    'duplicates': duplicates,
                    'errors': errors,
                    'contacts_before': contacts_before,
                    'contacts_after': contacts_after
                },
                'file_info': {
                    'filename': file.filename,
                    'columns': columns,
                    'sample_data': sample_data
                },
                'message': f'Successfully processed {total_rows} rows. {new_contacts} new contacts added, {duplicates} duplicates updated, {errors} errors.'
            })
            
        except Exception as e:
            # Clean up temporary file on error
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
            current_app.logger.error(f"Error processing CSV file: {str(e)}")
            return jsonify({'error': f'Failed to process CSV file: {str(e)}'}), 500
        
        finally:
            if 'ingester' in locals():
                ingester.close()
        
    except Exception as e:
        current_app.logger.error(f"Error in CSV import: {str(e)}")
        return jsonify({'error': 'Failed to import CSV file'}), 500

@bp.route('/contacts/preview', methods=['POST'])
def preview_csv():
    """Preview CSV file contents and column mapping."""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not file.filename.endswith('.csv'):
            return jsonify({'error': 'File must be a CSV'}), 400
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.csv', delete=False) as temp_file:
            file.save(temp_file.name)
            temp_file_path = temp_file.name
        
        try:
            # Read CSV file with better encoding handling
            try:
                df = pd.read_csv(temp_file_path)
            except UnicodeDecodeError:
                # Try with different encoding
                df = pd.read_csv(temp_file_path, encoding='latin-1')
            except Exception as e:
                raise Exception(f"Could not read CSV file. Please ensure it's a valid CSV format. Error: {str(e)}")
            
            # Check if DataFrame is empty
            if df.empty:
                raise Exception("CSV file is empty or contains no valid data")
            
            # Log basic info about the file
            current_app.logger.info(f"Processing CSV: {file.filename}, Shape: {df.shape}, Columns: {list(df.columns)}")
            
            # Check for basic data quality issues
            if len(df.columns) == 0:
                raise Exception("CSV file has no columns")
            
            # Initialize data ingester for column mapping
            ingester = ContactDataIngester()
            
            # Get column information
            columns = df.columns.tolist()
            email_columns = ingester.identify_email_columns(columns)
            column_mapping = ingester.map_columns(columns)
            
            # Get sample data (first 5 rows) and clean for JSON
            sample_data_raw = df.head(5).to_dict('records')
            sample_data = clean_data_for_json(sample_data_raw)
            
            # Clean up temporary file
            os.unlink(temp_file_path)
            
            return jsonify({
                'success': True,
                'file_info': {
                    'filename': file.filename,
                    'total_rows': len(df),
                    'columns': columns,
                    'email_columns': email_columns,
                    'column_mapping': column_mapping,
                    'sample_data': sample_data
                }
            })
            
        except Exception as e:
            # Clean up temporary file on error
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
            current_app.logger.error(f"Error previewing CSV file: {str(e)}")
            return jsonify({'error': f'Failed to preview CSV file: {str(e)}'}), 500
        
    except Exception as e:
        current_app.logger.error(f"Error in CSV preview: {str(e)}")
        return jsonify({'error': 'Failed to preview CSV file'}), 500

@bp.route('/contacts/uncontacted', methods=['GET'])
def get_uncontacted_contacts():
    """Get contacts who haven't received any emails yet."""
    try:
        # Get all contacts
        all_contacts = Contact.load_all()
        
        # Get all email recipients from history
        email_history = EmailHistory.load_all()
        contacted_emails = set()
        
        for email in email_history:
            if email.to:
                contacted_emails.add(email.to.lower().strip())
        
        # Filter contacts who haven't been contacted
        uncontacted_contacts = []
        for contact in all_contacts:
            if contact.email and contact.email.lower().strip() not in contacted_emails:
                uncontacted_contacts.append(contact)
        
        return jsonify({
            'contacts': [contact.to_dict() for contact in uncontacted_contacts],
            'count': len(uncontacted_contacts),
            'total_contacts': len(all_contacts),
            'contacted_count': len(contacted_emails)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting uncontacted contacts: {str(e)}")
        return jsonify({'error': 'Failed to load uncontacted contacts'}), 500 