from datetime import datetime
from typing import Dict, List, Optional
from flask import current_app

from app.models.contact import Contact
from app.models.email_history import EmailHistory
from composer_instance import composer
from send_emails import send_email

class EmailService:
    """Service class for email operations."""

    @staticmethod
    def compose_email(contact_data: Dict) -> Optional[Dict]:
        """
        Compose an email for a given contact.
        
        Args:
            contact_data: Dictionary containing contact information
            
        Returns:
            Dictionary with subject and body, or None if failed
        """
        try:
            lead_info = {
                'name': contact_data.get('name', ''),
                'email': contact_data.get('email', ''),
                'company': contact_data.get('company', ''),
                'position': contact_data.get('position', '')
            }
            
            email_content = composer.compose_email(lead_info)
            
            if email_content and 'subject' in email_content and 'body' in email_content:
                return {
                    'subject': email_content['subject'],
                    'body': email_content['body']
                }
            else:
                current_app.logger.error(f"Invalid email content returned: {email_content}")
                return None
                
        except Exception as e:
            current_app.logger.error(f"Error composing email: {str(e)}")
            return None

    @staticmethod
    def send_email(recipient_email: str, recipient_name: str, subject: str, body: str) -> bool:
        """
        Send an email and save to history.
        
        Args:
            recipient_email: Email address of recipient
            recipient_name: Name of recipient
            subject: Email subject
            body: Email body
            
        Returns:
            True if email was sent successfully, False otherwise
        """
        try:
            # Send the email
            success = send_email(recipient_email, subject, body)
            
            # Save to history
            email_data = {
                'date': datetime.now(),
                'to': recipient_email,
                'subject': subject,
                'body': body,
                'status': 'Success' if success else 'Failed'
            }
            
            EmailHistory.save(email_data)
            
            return success
            
        except Exception as e:
            current_app.logger.error(f"Error sending email to {recipient_email}: {str(e)}")
            return False

    @staticmethod
    def send_bulk_emails(recipients: List[Dict]) -> Dict:
        """
        Send emails to multiple recipients.
        
        Args:
            recipients: List of recipient dictionaries
            
        Returns:
            Dictionary with results summary
        """
        results = {
            'success': 0,
            'failed': 0,
            'failures': []
        }
        
        for recipient in recipients:
            try:
                # Extract contact information
                contact_data = {
                    'name': recipient.get('First Name', ''),
                    'email': recipient.get('Work Email', ''),
                    'company': recipient.get('Company Name', ''),
                    'position': recipient.get('Job Title', '')
                }
                
                # Skip if no email is provided
                if not contact_data['email']:
                    results['failed'] += 1
                    results['failures'].append({
                        'name': contact_data['name'], 
                        'reason': 'Missing email address'
                    })
                    continue
                
                # Generate email content
                email_content = EmailService.compose_email(contact_data)
                
                if not email_content:
                    results['failed'] += 1
                    results['failures'].append({
                        'name': contact_data['name'],
                        'email': contact_data['email'],
                        'reason': 'Failed to generate email content'
                    })
                    continue
                
                # Send the email
                success = EmailService.send_email(
                    contact_data['email'], 
                    contact_data['name'], 
                    email_content['subject'], 
                    email_content['body']
                )
                
                if success:
                    results['success'] += 1
                else:
                    results['failed'] += 1
                    results['failures'].append({
                        'name': contact_data['name'],
                        'email': contact_data['email'],
                        'reason': 'Failed to send email'
                    })
                    
            except Exception as e:
                current_app.logger.error(f"Error processing recipient {recipient}: {str(e)}")
                results['failed'] += 1
                results['failures'].append({
                    'name': recipient.get('First Name', 'Unknown'),
                    'email': recipient.get('Work Email', 'Unknown'),
                    'reason': f'Processing error: {str(e)}'
                })
        
        return results

    @staticmethod
    def get_unsent_contacts() -> List[Contact]:
        """
        Get contacts who haven't received emails yet.
        
        Returns:
            List of Contact objects for unsent contacts
        """
        try:
            all_contacts = Contact.load_all()
            sent_emails = EmailHistory.get_sent_emails_set()
            
            unsent_contacts = []
            for contact in all_contacts:
                if contact.email and contact.email.lower() not in sent_emails:
                    unsent_contacts.append(contact)
            
            return unsent_contacts
            
        except Exception as e:
            current_app.logger.error(f"Error getting unsent contacts: {str(e)}")
            return [] 