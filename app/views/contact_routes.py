from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
import os
import tempfile
import pandas as pd
import numpy as np
import csv
import io

from app.models.contact import Contact
from app.models.company import Company
from app.models.email_history import EmailHistory
from data_ingestion_system import ContactDataIngester
from app.services.email_service import EmailService

contact_bp = Blueprint('contact_api', __name__, url_prefix='/api')

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

@contact_bp.route('/contacts', methods=['GET'])
def get_contacts():
    """Get all contacts."""
    try:
        contacts = Contact.load_all()
        return jsonify([contact.to_dict() for contact in contacts])
    except Exception as e:
        current_app.logger.error(f"Error getting contacts: {str(e)}")
        return jsonify({'error': 'Failed to load contacts'}), 500

@contact_bp.route('/contact/<email>', methods=['GET'])
@contact_bp.route('/contacts/<email>', methods=['GET'])
def get_contact(email):
    """Get a specific contact by email."""
    try:
        current_app.logger.info(f"Looking up contact: {email}")
        contacts = Contact.search(email)
        if contacts:
            contact_dict = contacts[0].to_dict()
            return jsonify({'contact': contact_dict})
        return jsonify({'error': 'Contact not found'}), 404
    except Exception as e:
        current_app.logger.error(f"Error getting contact: {str(e)}")
        return jsonify({'error': 'Failed to load contact'}), 500

@contact_bp.route('/contact/<email>', methods=['PUT'])
def update_contact(email):
    """Update an existing contact's details."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
 
        # Allowed fields for update (matching column names)
        allowed_fields = [
            'first_name', 'last_name', 'full_name', 'job_title', 'company_name',
            'company_domain', 'linkedin_profile', 'location', 'phone', 'linkedin_message', 'company_id'
        ]
 
        update_fields = {k: v.strip() if isinstance(v, str) else v for k, v in data.items() if k in allowed_fields}
        if not update_fields:
            return jsonify({'success': False, 'message': 'No valid fields to update'}), 400
 
        from sqlalchemy import create_engine, text
        import os
        from datetime import datetime
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            return jsonify({'success': False, 'message': 'Database connection error'}), 500
 
        engine = create_engine(
            database_url,
            pool_size=5,          # Maximum number of permanent connections
            max_overflow=10,      # Maximum number of connections that can overflow the pool
            pool_pre_ping=True,   # Verify connections before use
            pool_recycle=3600     # Recycle connections every hour
        )
        with engine.connect() as conn:
            with conn.begin():
                # Handle company_id if company info is being updated
                company_id = None
                company_name = update_fields.get('company_name') or data.get('company_name')
                company_domain = update_fields.get('company_domain') or data.get('company_domain')
                
                if company_name or company_domain:
                    # Check by name first
                    if company_name:
                        result = conn.execute(text("""
                            SELECT id FROM companies WHERE LOWER(company_name) = LOWER(:company_name) LIMIT 1
                        """), {"company_name": company_name})
                        row = result.fetchone()
                        if row:
                            company_id = row.id
                    
                    # If not found by name, check by domain
                    if not company_id and company_domain:
                        domain_pattern = f"%{company_domain.lower()}%"
                        result = conn.execute(text("""
                            SELECT id FROM companies WHERE LOWER(website_url) LIKE :domain_pattern LIMIT 1
                        """), {"domain_pattern": domain_pattern})
                        row = result.fetchone()
                        if row:
                            company_id = row.id
                    
                    # Create new company if not found
                    if not company_id:
                        website_url = ''
                        if company_domain:
                            website_url = company_domain if company_domain.startswith(('http://', 'https://')) else f"https://{company_domain}"
                        fallback_name = company_name or company_domain or 'Unknown'
                        result = conn.execute(text("""
                            INSERT INTO companies (
                                company_name, website_url, research_status, 
                                created_at, updated_at
                            )
                            VALUES (
                                :company_name, :website_url, 'pending',
                                CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                            )
                            RETURNING id
                        """), {
                            "company_name": fallback_name,
                            "website_url": website_url
                        })
                        company_id = result.fetchone().id
                    
                    # Add company_id to update fields
                    update_fields['company_id'] = company_id

                # Build dynamic SET clause
                set_clause = ", ".join([f"{field} = :{field}" for field in update_fields.keys()])
                update_fields['updated_at'] = datetime.now()
                update_fields['email'] = email
                conn.execute(text(f"""
                    UPDATE contacts 
                    SET {set_clause}, updated_at = :updated_at
                    WHERE LOWER(email) = LOWER(:email)
                """), update_fields)
 
        current_app.logger.info(f"Updated contact: {email}")
        return jsonify({'success': True, 'message': f'Contact {email} updated successfully'})
    except Exception as e:
        current_app.logger.error(f"Error updating contact: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@contact_bp.route('/contacts/add', methods=['POST'])
def add_contact():
    """Add a new contact manually."""
    try:
        data = request.get_json()
        
        # Validate required fields
        email = data.get('email', '').strip()
        if not email:
            return jsonify({
                'success': False,
                'message': 'Email is required'
            }), 400
        
        # Basic email validation
        if '@' not in email or '.' not in email.split('@')[-1]:
            return jsonify({
                'success': False,
                'message': 'Please enter a valid email address'
            }), 400
        
        # Check if contact already exists
        existing_contacts = Contact.search(email)
        if existing_contacts:
            return jsonify({
                'success': False,
                'message': 'A contact with this email already exists'
            }), 400
        
        # Prepare contact data
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        full_name = data.get('full_name', '').strip()
        
        # Auto-generate full_name if not provided
        if not full_name and (first_name or last_name):
            full_name = f"{first_name} {last_name}".strip()
        
        # Handle company selection/creation
        company_id = None
        company_name = ''
        company_domain = ''
        
        # Check if user selected existing company or wants to create new one
        selected_company_id = data.get('company_id')
        create_new_company = data.get('create_new_company', False)
        
        if selected_company_id and not create_new_company:
            # User selected existing company
            company_id = selected_company_id
            # Get company details for contact record
            existing_company = Company.get_by_id(company_id)
            if existing_company:
                company_name = existing_company.company_name
                company_domain = existing_company.website_url
        elif create_new_company:
            # User wants to create new company - validate mandatory fields
            new_company_name = data.get('new_company_name', '').strip()
            new_company_website = data.get('new_company_website', '').strip()
            
            if not new_company_name:
                return jsonify({
                    'success': False,
                    'message': 'Company name is required when creating a new company'
                }), 400
            
            if not new_company_website:
                return jsonify({
                    'success': False,
                    'message': 'Company website is required when creating a new company'
                }), 400
            
            company_name = new_company_name
            company_domain = new_company_website
        else:
            # Backward compatibility - check for old company_name field
            company_name = data.get('company_name', '').strip()
            company_domain = data.get('company_domain', '').strip()
        
        # Create contact data dictionary
        contact_data = {
            'email': email,
            'first_name': first_name,
            'last_name': last_name,
            'full_name': full_name,
            'job_title': data.get('job_title', '').strip(),
            'company_name': company_name,
            'company_domain': company_domain,
            'linkedin_profile': data.get('linkedin_profile', '').strip(),
            'location': data.get('location', '').strip(),
            'phone': data.get('phone', '').strip(),
            'linkedin_message': data.get('linkedin_message', '').strip(),
        }
        
        # Use the Contact model to save the contact
        # Since Contact model doesn't have a save method, we'll use the database directly
        from sqlalchemy import create_engine, text
        from datetime import datetime
        import json
        import os
        
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            return jsonify({
                'success': False,
                'message': 'Database connection error'
            }), 500
        
        engine = create_engine(
            database_url,
            pool_size=5,          # Maximum number of permanent connections
            max_overflow=10,      # Maximum number of connections that can overflow the pool
            pool_pre_ping=True,   # Verify connections before use
            pool_recycle=3600     # Recycle connections every hour
        )
        with engine.connect() as conn:
            with conn.begin():
                # -------------------------------------------------------------
                # First, ensure the associated company exists and get its ID
                # -------------------------------------------------------------
                final_company_id = company_id  # Use pre-selected company_id if available
                contact_company_name = contact_data.get('company_name')
                contact_company_domain = contact_data.get('company_domain')

                # Only search/create company if we don't already have a company_id
                if not final_company_id and (contact_company_name or contact_company_domain):
                    # Check by company name (case-insensitive)
                    if contact_company_name:
                        result = conn.execute(text("""
                            SELECT id FROM companies
                            WHERE LOWER(company_name) = LOWER(:company_name)
                            LIMIT 1
                        """), {"company_name": contact_company_name})
                        row = result.fetchone()
                        if row:
                            final_company_id = row.id

                    # If not found by name, check by website_url/domain
                    if not final_company_id and contact_company_domain:
                        domain_pattern = f"%{contact_company_domain.lower()}%"
                        result = conn.execute(text("""
                            SELECT id FROM companies
                            WHERE LOWER(website_url) LIKE :domain_pattern
                            LIMIT 1
                        """), {"domain_pattern": domain_pattern})
                        row = result.fetchone()
                        if row:
                            final_company_id = row.id

                    # Insert new company if it doesn't exist
                    if not final_company_id:
                        website_url = ''
                        if contact_company_domain:
                            website_url = contact_company_domain if contact_company_domain.startswith(('http://', 'https://')) else f"https://{contact_company_domain}"
                        # Use company_name if available, otherwise fallback to domain
                        fallback_name = contact_company_name or contact_company_domain or 'Unknown'
                        result = conn.execute(text("""
                            INSERT INTO companies (
                                company_name, website_url, research_status, 
                                created_at, updated_at
                            )
                            VALUES (
                                :company_name, :website_url, 'pending',
                                CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                            )
                            RETURNING id
                        """), {
                            "company_name": fallback_name,
                            "website_url": website_url
                        })
                        final_company_id = result.fetchone().id

                # Insert new contact with company_id foreign key
                conn.execute(text("""
                    INSERT INTO contacts (
                        email, first_name, last_name, full_name, job_title, 
                        company_name, company_domain, linkedin_profile, location, 
                        phone, linkedin_message, company_id, source_files, all_data
                    ) VALUES (
                        :email, :first_name, :last_name, :full_name, :job_title,
                        :company_name, :company_domain, :linkedin_profile, :location,
                        :phone, :linkedin_message, :company_id, :source_files, :all_data
                    )
                """), {
                    **contact_data,
                    'company_id': final_company_id,
                    'source_files': json.dumps(["manual_entry"]),
                    'all_data': json.dumps({
                        'source': 'manual_entry',
                        'created_by': 'user',
                        'entry_date': datetime.now().isoformat()
                    })
                })
                # -------------------------------------------------------------
        
        current_app.logger.info(f"Successfully added new contact: {email}")
        
        return jsonify({
            'success': True,
            'message': f'Contact {full_name or email} added successfully',
            'contact': {
                'email': email,
                'name': full_name or f"{first_name} {last_name}".strip() or email,
                'company': contact_data['company_name'],
                'job_title': contact_data['job_title']
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error adding contact: {e}")
        return jsonify({
            'success': False,
            'message': 'An unexpected error occurred'
        }), 500

@contact_bp.route('/contacts/export', methods=['GET'])
def export_contacts():
    """Export contacts to CSV."""
    try:
        from flask import Response
        
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
        
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={"Content-disposition": "attachment; filename=contacts.csv"}
        )
        
    except Exception as e:
        current_app.logger.error(f"Error exporting contacts: {str(e)}")
        return jsonify({'error': 'Failed to export contacts'}), 500

@contact_bp.route('/get_unsent_leads', methods=['GET'])
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

@contact_bp.route('/search_contacts', methods=['GET'])
@contact_bp.route('/contacts/search', methods=['GET'])
def search_contacts():
    """Search contacts by query."""
    try:
        query = request.args.get('q', '').strip()
        
        if not query:
            return jsonify({
                'success': True,
                'contacts': [], 
                'count': 0,
                'query': ''
            })
        
        contacts = Contact.search(query)
        
        return jsonify({
            'success': True,
            'contacts': [contact.to_dict() for contact in contacts],
            'count': len(contacts),
            'query': query
        })
        
    except Exception as e:
        current_app.logger.error(f"Error in search_contacts: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to search contacts',
            'contacts': [],
            'count': 0
        }), 500

@contact_bp.route('/contacts/import', methods=['POST'])
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

@contact_bp.route('/contacts/preview', methods=['POST'])
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

@contact_bp.route('/contacts/uncontacted', methods=['GET'])
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

@contact_bp.route('/contacts/count-filtered', methods=['POST'])
def count_filtered_contacts():
    """Count contacts based on filter criteria for campaign selection."""
    try:
        data = request.get_json()
        filter_type = data.get('type', 'quick')
        
        # Get all contacts
        all_contacts = Contact.load_all()
        
        if filter_type == 'quick':
            filter_value = data.get('filter_type', 'all')
            company_filter = data.get('company', '')
            
            if filter_value == 'all':
                filtered_contacts = all_contacts
            elif filter_value == 'uncontacted':
                # Get contacted emails from history
                email_history = EmailHistory.load_all()
                contacted_emails = set()
                for email in email_history:
                    if email.to:
                        contacted_emails.add(email.to.lower().strip())
                
                filtered_contacts = [
                    contact for contact in all_contacts
                    if contact.email and contact.email.lower().strip() not in contacted_emails
                ]
            elif filter_value == 'has_phone':
                filtered_contacts = [
                    contact for contact in all_contacts
                    if contact.raw_data and contact.raw_data.get('phone')
                ]
            elif filter_value == 'has_linkedin':
                filtered_contacts = [
                    contact for contact in all_contacts
                    if contact.raw_data and contact.raw_data.get('linkedin_profile')
                ]
            elif filter_value == 'recent':
                # Get contacts from last 30 days (simplified)
                filtered_contacts = all_contacts[:50]  # Placeholder
            else:
                filtered_contacts = all_contacts
            
            # Apply company filter if specified
            if company_filter:
                filtered_contacts = [
                    contact for contact in filtered_contacts
                    if contact.company and company_filter.lower() in contact.company.lower()
                ]
            
        elif filter_type == 'advanced':
            filtered_contacts = all_contacts
            
            # Apply advanced filters
            company = data.get('company', '').lower()
            job_title = data.get('job_title', '').lower()
            location = data.get('location', '').lower()
            exclude_contacted = data.get('exclude_contacted', False)
            require_phone = data.get('require_phone', False)
            require_linkedin = data.get('require_linkedin', False)
            
            if company:
                filtered_contacts = [
                    contact for contact in filtered_contacts
                    if contact.company and company in contact.company.lower()
                ]
            
            if job_title:
                filtered_contacts = [
                    contact for contact in filtered_contacts
                    if contact.job_title and job_title in contact.job_title.lower()
                ]
            
            if location:
                filtered_contacts = [
                    contact for contact in filtered_contacts
                    if contact.location and location in contact.location.lower()
                ]
            
            if require_phone:
                filtered_contacts = [
                    contact for contact in filtered_contacts
                    if contact.raw_data and contact.raw_data.get('phone')
                ]
            
            if require_linkedin:
                filtered_contacts = [
                    contact for contact in filtered_contacts
                    if contact.raw_data and contact.raw_data.get('linkedin_profile')
                ]
            
            if exclude_contacted:
                email_history = EmailHistory.load_all()
                contacted_emails = set()
                for email in email_history:
                    if email.to:
                        contacted_emails.add(email.to.lower().strip())
                
                filtered_contacts = [
                    contact for contact in filtered_contacts
                    if contact.email and contact.email.lower().strip() not in contacted_emails
                ]
        
        else:  # manual selection
            # For manual selection, count is handled on frontend
            return jsonify({'count': 0})
        
        return jsonify({
            'count': len(filtered_contacts),
            'total_contacts': len(all_contacts)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error counting filtered contacts: {str(e)}")
        return jsonify({'error': 'Failed to count contacts', 'count': 0}), 500
