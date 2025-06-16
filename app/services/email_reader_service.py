import imaplib
import email
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from email.header import decode_header
from email.utils import parseaddr, parsedate_to_datetime
import re
import os
from flask import current_app

class EmailReaderService:
    """Service for reading emails and extracting conversations with contacts."""
    
    def __init__(self):
        self.imap_host = None
        self.imap_port = 993
        self.email = None
        self.password = None
        self.connection = None
        
    def configure_imap(self, host: str, email: str, password: str, port: int = 993):
        """Configure IMAP connection settings."""
        self.imap_host = host
        self.imap_port = port
        self.email = email
        self.password = password
        
    def connect(self) -> bool:
        """Connect to email server via IMAP."""
        try:
            if not all([self.imap_host, self.email, self.password]):
                current_app.logger.error("IMAP configuration incomplete")
                return False
                
            self.connection = imaplib.IMAP4_SSL(self.imap_host, self.imap_port)
            self.connection.login(self.email, self.password)
            current_app.logger.info(f"Successfully connected to {self.email}")
            return True
            
        except imaplib.IMAP4.error as e:
            error_msg = str(e)
            if b'IMAP' in error_msg.encode() and b'enable' in error_msg.encode():
                current_app.logger.error(f"IMAP not enabled for {self.email}: {error_msg}")
                current_app.logger.info("Please enable IMAP access in Zoho Mail Settings > Mail Accounts > IMAP Access")
            else:
                current_app.logger.error(f"IMAP authentication failed for {self.email}: {error_msg}")
            return False
        except Exception as e:
            current_app.logger.error(f"Failed to connect to email: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from email server."""
        if self.connection:
            try:
                self.connection.logout()
            except:
                pass
            self.connection = None
    
    def search_conversations_with_contact(self, contact_email: str, days_back: int = 365) -> List[Dict]:
        """
        Search for all email conversations with a specific contact.
        
        Args:
            contact_email: Email address to search for
            days_back: How many days back to search
            
        Returns:
            List of email dictionaries with conversation data
        """
        if not self.connection:
            if not self.connect():
                return []
        
        conversations = []
        
        try:
            # Search in multiple folders
            folders = ['INBOX', 'Sent', 'Drafts']
            
            for folder in folders:
                try:
                    self.connection.select(folder)
                    
                    # Calculate date range
                    since_date = datetime.now() - timedelta(days=days_back)
                    since_str = since_date.strftime("%d-%b-%Y")
                    
                    # Search for emails with this contact
                    search_criteria = [
                        f'(OR FROM "{contact_email}" TO "{contact_email}")',
                        f'SINCE {since_str}'
                    ]
                    
                    status, message_ids = self.connection.search(None, *search_criteria)
                    
                    if status == 'OK' and message_ids[0]:
                        ids = message_ids[0].split()
                        
                        for msg_id in ids[-50:]:  # Limit to last 50 emails
                            email_data = self._fetch_email_data(msg_id, folder)
                            if email_data:
                                conversations.append(email_data)
                                
                except Exception as e:
                    current_app.logger.warning(f"Error searching folder {folder}: {e}")
                    
        except Exception as e:
            current_app.logger.error(f"Error searching conversations: {e}")
            
        # Sort by date (newest first)
        conversations.sort(key=lambda x: x.get('date', datetime.min), reverse=True)
        return conversations
    
    def _fetch_email_data(self, msg_id: bytes, folder: str) -> Optional[Dict]:
        """Fetch and parse email data."""
        try:
            status, msg_data = self.connection.fetch(msg_id, '(RFC822)')
            
            if status != 'OK' or not msg_data[0]:
                return None
                
            email_message = email.message_from_bytes(msg_data[0][1])
            
            # Extract headers
            subject = self._decode_header(email_message.get('Subject', ''))
            from_addr = self._decode_header(email_message.get('From', ''))
            to_addr = self._decode_header(email_message.get('To', ''))
            cc_addr = self._decode_header(email_message.get('Cc', ''))
            date_str = email_message.get('Date', '')
            message_id = email_message.get('Message-ID', '')
            in_reply_to = email_message.get('In-Reply-To', '')
            
            # Parse date
            try:
                email_date = parsedate_to_datetime(date_str) if date_str else datetime.now()
            except:
                email_date = datetime.now()
            
            # Extract body
            body = self._extract_email_body(email_message)
            
            # Determine direction
            sender_email = parseaddr(from_addr)[1].lower()
            direction = 'sent' if sender_email == self.email.lower() else 'received'
            
            return {
                'id': msg_id.decode(),
                'message_id': message_id,
                'in_reply_to': in_reply_to,
                'subject': subject,
                'from': from_addr,
                'to': to_addr,
                'cc': cc_addr,
                'date': email_date,
                'body': body,
                'direction': direction,
                'folder': folder,
                'thread_id': self._extract_thread_id(subject, message_id, in_reply_to)
            }
            
        except Exception as e:
            current_app.logger.error(f"Error fetching email {msg_id}: {e}")
            return None
    
    def _decode_header(self, header_value: str) -> str:
        """Decode email header."""
        if not header_value:
            return ''
            
        try:
            decoded_parts = decode_header(header_value)
            decoded_string = ''
            
            for part, encoding in decoded_parts:
                if isinstance(part, bytes):
                    decoded_string += part.decode(encoding or 'utf-8', errors='ignore')
                else:
                    decoded_string += part
                    
            return decoded_string.strip()
            
        except Exception as e:
            current_app.logger.warning(f"Error decoding header: {e}")
            return header_value
    
    def _extract_email_body(self, email_message) -> str:
        """Extract email body text."""
        body = ""
        
        try:
            if email_message.is_multipart():
                for part in email_message.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition"))
                    
                    if content_type == "text/plain" and "attachment" not in content_disposition:
                        charset = part.get_content_charset() or 'utf-8'
                        payload = part.get_payload(decode=True)
                        if payload:
                            body += payload.decode(charset, errors='ignore')
                            
                    elif content_type == "text/html" and "attachment" not in content_disposition and not body:
                        # Use HTML as fallback if no plain text
                        charset = part.get_content_charset() or 'utf-8'
                        payload = part.get_payload(decode=True)
                        if payload:
                            html_body = payload.decode(charset, errors='ignore')
                            # Simple HTML to text conversion
                            body += re.sub(r'<[^>]+>', '', html_body)
            else:
                charset = email_message.get_content_charset() or 'utf-8'
                payload = email_message.get_payload(decode=True)
                if payload:
                    body = payload.decode(charset, errors='ignore')
                    
        except Exception as e:
            current_app.logger.warning(f"Error extracting email body: {e}")
            
        return body.strip()
    
    def _extract_thread_id(self, subject: str, message_id: str, in_reply_to: str) -> str:
        """Generate a thread ID for grouping related emails."""
        # Clean subject for threading
        clean_subject = re.sub(r'^(Re:|Fwd?:|AW:|SV:)\s*', '', subject, flags=re.IGNORECASE).strip()
        
        # Use in_reply_to or clean subject as thread identifier
        if in_reply_to:
            return in_reply_to
        elif clean_subject:
            return f"subject:{clean_subject}"
        else:
            return message_id
    
    def group_emails_by_thread(self, emails: List[Dict]) -> Dict[str, List[Dict]]:
        """Group emails by conversation thread."""
        threads = {}
        
        for email_data in emails:
            thread_id = email_data.get('thread_id', email_data.get('message_id', 'unknown'))
            
            if thread_id not in threads:
                threads[thread_id] = []
                
            threads[thread_id].append(email_data)
        
        # Sort emails within each thread by date
        for thread_id in threads:
            threads[thread_id].sort(key=lambda x: x.get('date', datetime.min))
            
        return threads
    
    def get_conversation_summary(self, contact_email: str) -> Dict:
        """Get a summary of email conversation with a contact."""
        conversations = self.search_conversations_with_contact(contact_email)
        
        if not conversations:
            return {
                'total_emails': 0,
                'sent_count': 0,
                'received_count': 0,
                'last_email_date': None,
                'last_email_direction': None,
                'threads': {},
                'recent_emails': []
            }
        
        sent_count = len([e for e in conversations if e['direction'] == 'sent'])
        received_count = len([e for e in conversations if e['direction'] == 'received'])
        
        threads = self.group_emails_by_thread(conversations)
        
        return {
            'total_emails': len(conversations),
            'sent_count': sent_count,
            'received_count': received_count,
            'last_email_date': conversations[0]['date'] if conversations else None,
            'last_email_direction': conversations[0]['direction'] if conversations else None,
            'threads': threads,
            'recent_emails': conversations[:10]  # Last 10 emails
        }

# Singleton instance
email_reader = EmailReaderService()

def configure_email_reader():
    """Configure email reader from environment variables."""
    
    # Try different email providers
    email_address = os.getenv('SENDER_EMAIL', '')
    password = os.getenv('SENDER_PASSWORD', '') or os.getenv('EMAIL_PASSWORD', '')
    
    if not email_address or not password:
        current_app.logger.warning("Email reading not configured - missing credentials")
        return False
    
    # Determine IMAP settings based on email provider
    domain = email_address.split('@')[-1].lower()
    
    imap_settings = {
        'gmail.com': 'imap.gmail.com',
        'googlemail.com': 'imap.gmail.com',
        'outlook.com': 'outlook.office365.com',
        'hotmail.com': 'outlook.office365.com',
        'live.com': 'outlook.office365.com',
        'zoho.com': 'imap.zoho.com',
        'zoho.in': 'imap.zoho.in', # Added for Zoho India
        'possibleminds.in': 'imap.zoho.in',  # Your domain uses Zoho India
        'possiblemindshq.com': 'imap.zoho.in', # Updated for your domain to use Zoho India
        'yahoo.com': 'imap.mail.yahoo.com'
    }
    
    imap_host = imap_settings.get(domain, 'imap.' + domain)
    
    email_reader.configure_imap(imap_host, email_address, password)
    current_app.logger.info(f"Email reader configured for {email_address}")
    return True 