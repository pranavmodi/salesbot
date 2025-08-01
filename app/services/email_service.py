from datetime import datetime
from typing import Dict, List, Optional
from flask import current_app
import os
import time # Import the time module

from app.models.contact import Contact
from app.models.email_history import EmailHistory
from app.utils.email_config import email_config, EmailAccount
from email_composers.composer_instance import composer
from send_emails import send_email
from email_composers.email_composer_warm import WarmEmailComposer
from email_composers.email_composer_alt_subject import AltSubjectEmailComposer
from email_composers.email_composer_deep_research import DeepResearchEmailComposer

class EmailService:
    """Service class for email operations."""

    @staticmethod
    def get_available_accounts() -> List[Dict]:
        """Get all available email accounts."""
        accounts = email_config.get_all_accounts()
        return [
            {
                'name': account.name,
                'email': account.email,
                'is_default': account.is_default
            }
            for account in accounts
        ]

    @staticmethod
    def send_email_with_account(recipient_email: str, recipient_name: str, subject: str, body: str, account_name: str = None, campaign_id: int = None) -> bool:
        """
        Send an email using a specific account.
        
        Args:
            recipient_email: Email address of recipient
            recipient_name: Name of recipient
            subject: Email subject
            body: Email body
            account_name: Name of the account to use (None for default)
            
        Returns:
            True if email was sent successfully, False otherwise
        """
        try:
            # Get the account to use
            if account_name:
                account = email_config.get_account_by_name(account_name)
                if not account:
                    current_app.logger.error(f"Account '{account_name}' not found")
                    return False
            else:
                account = email_config.get_default_account()
                if not account:
                    current_app.logger.error("No default account available")
                    return False

            # Send using the specific account
            success = EmailService._send_with_account(account, recipient_email, subject, body)
            
            # Save to history with standardized status
            email_data = {
                'date': datetime.now(),
                'to': recipient_email,
                'subject': subject,
                'body': body,
                'status': 'sent' if success else 'failed',
                'campaign_id': campaign_id,
                'sent_via': account.email,
                'email_type': 'campaign' if campaign_id else 'manual',
                'error_details': None  # Could be populated with specific error info if needed
            }
            
            EmailHistory.save(email_data)
            
            return success
            
        except Exception as e:
            current_app.logger.error(f"Error sending email to {recipient_email}: {str(e)}")
            return False

    @staticmethod
    def _send_with_account(account: EmailAccount, recipient_email: str, subject: str, body: str) -> bool:
        """
        Send email using a specific account configuration.
        
        Args:
            account: EmailAccount instance
            recipient_email: Recipient email address
            subject: Email subject
            body: Email body
            
        Returns:
            True if successful, False otherwise
        """
        # TEMPORARY: Send all emails to a specific address for testing
        original_recipient = recipient_email
        # recipient_email = "pranav.modi@gmail.com"
        
        try:
            from email.message import EmailMessage
            from email.utils import make_msgid
            import smtplib
            import ssl
            
            msg = EmailMessage()
            msg["Subject"] = subject
            msg["From"] = account.email
            msg["To"] = recipient_email
            msg["Message-ID"] = make_msgid()
            
            # Set content - check if body contains HTML
            if '<a href=' in body or '<html>' in body.lower():
                # Set HTML content with plain text alternative
                msg.set_content(body, subtype='html')
            else:
                # Set plain text content
                msg.set_content(body)
            
            # Create SSL context
            context = ssl.create_default_context()
            
            # Send the email
            if account.smtp_use_ssl:
                with smtplib.SMTP_SSL(account.smtp_host, account.smtp_port, context=context) as server:
                    server.login(account.email, account.password)
                    server.send_message(msg)
            else:
                with smtplib.SMTP(account.smtp_host, account.smtp_port) as server:
                    server.starttls(context=context)
                    server.login(account.email, account.password)
                    server.send_message(msg)
            
            current_app.logger.info(f"Email sent successfully to {recipient_email} (originally {original_recipient}) from {account.email}")
            return True
            
        except Exception as e:
            current_app.logger.error(f"Failed to send email from {account.email} to {recipient_email} (originally {original_recipient}): {str(e)}")
            return False

    @staticmethod
    def compose_email(contact_id: int, calendar_url: str = None, extra_context: str = None, composer_type: str = "warm", campaign_id: int = None) -> Dict[str, str] | None:
        """
        Thread-safe email composition for a given contact.
        
        Args:
            contact_id: ID of the contact
            calendar_url: URL of the calendar
            extra_context: Additional context for the email
            composer_type: Type of composer to use
            
        Returns:
            Dictionary with subject and body, or None if failed
        """
        import threading
        thread_id = threading.get_ident()
        current_app.logger.info(f"Thread {thread_id}: Starting email composition for contact {contact_id}")
        
        try:
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
                current_app.logger.error(f"Thread {thread_id}: Contact not found for ID: {contact_id}")
                return None

            lead_data = {
                "name": contact.display_name,
                "email": contact.email,
                "company": contact.company,
                "position": contact.job_title,
                "website": contact.company_domain,
                "notes": "",
            }
            
            # Get the default calendar URL if not provided
            effective_calendar_url = calendar_url or os.getenv("CALENDAR_URL", "https://calendly.com/pranav-modi/15-minute-meeting")
            
            # Use thread-safe composer for deep_research type (most memory intensive)
            if composer_type == "deep_research":
                current_app.logger.info(f"Thread {thread_id}: Using thread-safe deep research composer")
                from app.services.thread_safe_email_composer import get_thread_safe_composer
                
                thread_safe_composer = get_thread_safe_composer()
                email_content = thread_safe_composer.compose_email_safely(
                    lead=lead_data, 
                    calendar_url=effective_calendar_url, 
                    extra_context=extra_context,
                    composer_type=composer_type,
                    campaign_id=campaign_id
                )
            else:
                # Use regular composers for other types (legacy support)
                if composer_type == "alt_subject":
                    composer = AltSubjectEmailComposer()
                elif composer_type == "possible_minds":
                    from email_composers.email_composer_possible_minds import PossibleMindsEmailComposer
                    composer = PossibleMindsEmailComposer()
                else: # Default to warm
                    composer = WarmEmailComposer()

                # Pass campaign_id to composer if it supports it
                if hasattr(composer, 'compose_email'):
                    email_content = composer.compose_email(lead=lead_data, calendar_url=effective_calendar_url, extra_context=extra_context)
                else:
                    email_content = composer.compose_email(lead=lead_data, calendar_url=effective_calendar_url, extra_context=extra_context)
            
            if email_content and 'subject' in email_content and 'body' in email_content:
                current_app.logger.info(f"Thread {thread_id}: Email composition successful")
                return {
                    'subject': email_content['subject'],
                    'body': email_content['body']
                }
            else:
                current_app.logger.error(f"Thread {thread_id}: Invalid email content returned: {email_content}")
                return None
                
        except Exception as e:
            current_app.logger.error(f"Thread {thread_id}: Email composition failed: {str(e)}")
            return None
                
    @staticmethod
    def send_email(recipient_email: str, recipient_name: str, subject: str, body: str, campaign_id: int = None) -> bool:
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
            # Send the email using the global send_email function from send_emails.py
            from send_emails import send_email as global_send_email
            success = global_send_email(recipient_email, subject, body)
            
            # Save to history with standardized status
            email_data = {
                'date': datetime.now(),
                'to': recipient_email,
                'subject': subject,
                'body': body,
                'status': 'sent' if success else 'failed',
                'campaign_id': campaign_id,
                'sent_via': None,  # Will be populated by default email service
                'email_type': 'campaign' if campaign_id else 'manual',
                'error_details': None
            }
            
            EmailHistory.save(email_data)
            
            return success
            
        except Exception as e:
            current_app.logger.error(f"Error sending email to {recipient_email}: {str(e)}")
            return False

    @staticmethod
    def send_bulk_emails(recipients_data: List[Dict], composer_type: str = "warm", calendar_url: str = None, extra_context: str = None, account_name: str = None) -> Dict[str, List[str]]:
        """
        Send emails to a list of recipients.
        Composes email for each using the specified composer_type.
        Args:
            recipients_data: List of dictionaries, each with contact_id and optionally other email parameters.
            composer_type: Identifier for the email composer to use (e.g., 'warm', 'alt_subject').
            calendar_url: Optional calendar URL to use for all emails.
            extra_context: Optional extra context for all emails.
            account_name: Optional account name to use for sending all emails.
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

                # Send the email using specified account (actual sending logic)
                success = EmailService.send_email_with_account(
                    recipient_email=contact.email, 
                    recipient_name=contact.display_name, 
                    subject=email_content['subject'], 
                    body=email_content['body'],
                    account_name=account_name
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
                from send_emails import send_email as global_send_email
                success = global_send_email(recipient_email=email_address, subject=subject, body_markdown=body)
                
                # Save to history with standardized status
                email_data = {
                    'date': datetime.now(),
                    'to': email_address,
                    'subject': subject,
                    'body': body,
                    'status': 'sent' if success else 'failed',
                    'campaign_id': None,
                    'sent_via': None,  # Could be populated with account info
                    'email_type': 'test',
                    'error_details': None
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