from datetime import datetime
from typing import Dict, List, Optional
from flask import current_app
import os
import time # Import the time module

from app.models.contact import Contact
from app.models.email_history import EmailHistory
from composer_instance import composer
from send_emails import send_email
from email_composer_warm import WarmEmailComposer
from email_composer_alt_subject import AltSubjectEmailComposer

class EmailService:
    """Service class for email operations."""

    @staticmethod
    def compose_email(contact_id: int, calendar_url: str = None, extra_context: str = None, composer_type: str = "warm") -> Dict[str, str] | None:
        """
        Compose an email for a given contact.
        
        Args:
            contact_id: ID of the contact
            calendar_url: URL of the calendar
            extra_context: Additional context for the email
            composer_type: Type of composer to use
            
        Returns:
            Dictionary with subject and body, or None if failed
        """
        # For this application, we need to find the contact by email since we don't have contact IDs
        # This is a limitation of the current database structure
        # We'll need to modify this to work with the existing Contact model
        
        # Since Contact model doesn't have get by ID, we'll need to handle this differently
        # For now, let's assume contact_id is actually the contact email or we need to find another way
        
        # This is a temporary workaround - in a real application, you'd want proper ID-based lookups
        all_contacts = Contact.load_all()
        contact = None
        
        # Try to find contact by ID (assuming it's an index) or by email
        try:
            if isinstance(contact_id, int) and contact_id < len(all_contacts):
                contact = all_contacts[contact_id]
            else:
                # Try to find by email if contact_id is actually an email
                for c in all_contacts:
                    if c.email == str(contact_id):
                        contact = c
                        break
        except:
            pass
            
        if not contact:
            current_app.logger.error(f"Contact not found for ID: {contact_id}")
            return None

        lead_data = {
            "name": contact.display_name,
            "email": contact.email,
            "company": contact.company,
            "position": contact.job_title,
            "website": contact.company_domain,
            "notes": "",
        }
        
        if composer_type == "alt_subject":
            composer = AltSubjectEmailComposer()
        else: # Default to warm
            composer = WarmEmailComposer()

        # Get the default calendar URL if not provided
        effective_calendar_url = calendar_url or os.getenv("CALENDAR_URL", "https://calendly.com/pranav-modi/15-minute-meeting")

        email_content = composer.compose_email(lead=lead_data, calendar_url=effective_calendar_url, extra_context=extra_context)
        
        if email_content and 'subject' in email_content and 'body' in email_content:
            return {
                'subject': email_content['subject'],
                'body': email_content['body']
            }
        else:
            current_app.logger.error(f"Invalid email content returned: {email_content}")
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
    def send_bulk_emails(recipients_data: List[Dict], composer_type: str = "warm", calendar_url: str = None, extra_context: str = None) -> Dict[str, List[str]]:
        """
        Send emails to a list of recipients.
        Composes email for each using the specified composer_type.
        Args:
            recipients_data: List of dictionaries, each with contact_id and optionally other email parameters.
            composer_type: Identifier for the email composer to use (e.g., 'warm', 'alt_subject').
            calendar_url: Optional calendar URL to use for all emails.
            extra_context: Optional extra context for all emails.
        Returns:
            Dictionary with 'sent' and 'failed' lists of email addresses.
        """
        sent_emails = []
        failed_emails = []

        default_calendar = calendar_url or os.getenv("CALENDAR_URL", "https://calendly.com/pranav-modi/15-minute-meeting")

        for recipient_info in recipients_data:
            contact_id = recipient_info.get('contact_id')
            if not contact_id:
                # Try to get email if contact_id is missing, to report failure
                email_for_failure_report = recipient_info.get('email', 'Unknown (missing contact_id)')
                failed_emails.append(email_for_failure_report)
                current_app.logger.error(f"Missing contact_id for recipient: {recipient_info}")
                continue

            # Use per-recipient values if provided, else use bulk values, else use defaults
            current_calendar_url = recipient_info.get('calendar_url', default_calendar)
            current_extra_context = recipient_info.get('extra_context', extra_context)
            current_composer_type = recipient_info.get('composer_type', composer_type)

            try:
                email_content = EmailService.compose_email(
                    contact_id=contact_id, 
                    calendar_url=current_calendar_url, 
                    extra_context=current_extra_context,
                    composer_type=current_composer_type
                )
                
                if not email_content or 'subject' not in email_content or 'body' not in email_content:
                    current_app.logger.error(f"Failed to compose email for contact_id {contact_id} using {current_composer_type} composer.")
                    failed_emails.append(f"Contact ID {contact_id}")
                    continue

                # Get contact info for sending
                all_contacts = Contact.load_all()
                contact = None
                try:
                    if isinstance(contact_id, int) and contact_id < len(all_contacts):
                        contact = all_contacts[contact_id]
                    else:
                        for c in all_contacts:
                            if c.email == str(contact_id):
                                contact = c
                                break
                except:
                    pass
                
                if not contact:
                    failed_emails.append(f"Contact ID {contact_id} not found")
                    continue

                # Send the email (actual sending logic)
                success = EmailService.send_email(
                    recipient_email=contact.email, 
                    recipient_name=contact.display_name, 
                    subject=email_content['subject'], 
                    body=email_content['body']
                )
                
                if success:
                    sent_emails.append(contact.email)
                else:
                    failed_emails.append(contact.email)

            except Exception as e:
                current_app.logger.error(f"Error processing email for contact_id {contact_id}: {str(e)}")
                failed_emails.append(f"Contact ID {contact_id}")

        return {"sent": sent_emails, "failed": failed_emails}

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

    @staticmethod
    def send_test_email(recipient_emails: List[str], subject: str, body: str) -> Dict[str, List[str]]:
        """
        Send a test email to a list of recipients.

        Args:
            recipient_emails: List of email addresses of recipients
            subject: Email subject
            body: Email body

        Returns:
            Dictionary with 'sent' and 'failed' lists of email addresses
        """
        sent_emails = []
        failed_emails = []
        total_emails = len(recipient_emails)
        current_app.logger.info(f"Starting test email sending process for {total_emails} recipient(s).")

        for i, email_address in enumerate(recipient_emails):
            current_app.logger.info(f"Processing test email {i+1} of {total_emails} to: {email_address}")
            try:
                # We can reuse the existing send_email from send_emails.py for the actual sending
                # Assuming a generic name for the recipient for test emails
                success = send_email(recipient_email=email_address, subject=subject, body_markdown=body)
                
                # Save to history - reusing existing EmailHistory logic
                email_data = {
                    'date': datetime.now(),
                    'to': email_address,
                    'subject': subject,
                    'body': body,
                    'status': 'Success - Test Email' if success else 'Failed - Test Email'
                }
                EmailHistory.save(email_data)

                if success:
                    sent_emails.append(email_address)
                    current_app.logger.info(f"Test email sent successfully to {email_address}")
                else:
                    failed_emails.append(email_address)
                    current_app.logger.error(f"Failed to send test email to {email_address}")
            
            except Exception as e:
                current_app.logger.error(f"Error sending test email to {email_address}: {str(e)}")
                failed_emails.append(email_address)
            
            # Add delay if it's not the last email
            if i < total_emails - 1:
                current_app.logger.info(f"Waiting for 60 seconds before sending the next test email...")
                time.sleep(60)
                current_app.logger.info(f"Delay finished. Proceeding with the next email.")

        current_app.logger.info(f"Test email sending process completed. Sent: {len(sent_emails)}, Failed: {len(failed_emails)}")
        return {"sent": sent_emails, "failed": failed_emails} 