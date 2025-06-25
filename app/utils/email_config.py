import os
import json
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class EmailAccount:
    """Represents a single email account configuration."""
    
    def __init__(self, config: Dict):
        self.name = config.get('name', 'unnamed')
        self.email = config.get('email')
        self.password = config.get('password')
        self.smtp_host = config.get('smtp_host')
        self.smtp_port = config.get('smtp_port', 465)
        self.smtp_use_ssl = config.get('smtp_use_ssl', True)
        self.imap_host = config.get('imap_host')
        self.imap_port = config.get('imap_port', 993)
        self.imap_use_ssl = config.get('imap_use_ssl', True)
        self.is_default = config.get('is_default', False)
        
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'email': self.email,
            'password': self.password,
            'smtp_host': self.smtp_host,
            'smtp_port': self.smtp_port,
            'smtp_use_ssl': self.smtp_use_ssl,
            'imap_host': self.imap_host,
            'imap_port': self.imap_port,
            'imap_use_ssl': self.imap_use_ssl,
            'is_default': self.is_default
        }
    
    def is_valid(self) -> bool:
        """Check if account configuration is valid."""
        required_fields = ['email', 'password', 'smtp_host', 'imap_host']
        return all(getattr(self, field) for field in required_fields)

class EmailConfigManager:
    """Manages multiple email account configurations."""
    
    def __init__(self):
        self.accounts: List[EmailAccount] = []
        self.load_accounts()
    
    def load_accounts(self):
        """Load email accounts from environment configuration."""
        self.accounts = []
        
        # Load from JSON configuration
        email_accounts_json = os.getenv('EMAIL_ACCOUNTS')
        if not email_accounts_json:
            logger.error("EMAIL_ACCOUNTS environment variable is not set")
            raise ValueError("EMAIL_ACCOUNTS environment variable is required")
        
        try:
            accounts_data = json.loads(email_accounts_json)
            for account_data in accounts_data:
                account = EmailAccount(account_data)
                if account.is_valid():
                    self.accounts.append(account)
                else:
                    logger.warning(f"Invalid email account configuration: {account.name}")
            
            if self.accounts:
                logger.info(f"Loaded {len(self.accounts)} email accounts from JSON configuration")
            else:
                raise ValueError("No valid email accounts found in configuration")
                
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing EMAIL_ACCOUNTS JSON: {e}")
            raise ValueError(f"Invalid JSON in EMAIL_ACCOUNTS: {e}")
    

    
    def get_default_account(self) -> Optional[EmailAccount]:
        """Get the default email account."""
        # Look for explicitly marked default
        for account in self.accounts:
            if account.is_default:
                return account
        
        # Return first account if no default is set
        return self.accounts[0] if self.accounts else None
    
    def get_account_by_name(self, name: str) -> Optional[EmailAccount]:
        """Get account by name."""
        for account in self.accounts:
            if account.name == name:
                return account
        return None
    
    def get_account_by_email(self, email: str) -> Optional[EmailAccount]:
        """Get account by email address."""
        for account in self.accounts:
            if account.email.lower() == email.lower():
                return account
        return None
    
    def get_all_accounts(self) -> List[EmailAccount]:
        """Get all configured accounts."""
        return self.accounts.copy()
    
    def add_account(self, account: EmailAccount):
        """Add a new email account."""
        # If this is the first account, make it default
        if not self.accounts:
            account.is_default = True
        
        # Ensure only one default account
        if account.is_default:
            for existing_account in self.accounts:
                existing_account.is_default = False
        
        self.accounts.append(account)
    
    def remove_account(self, name: str) -> bool:
        """Remove an account by name."""
        for i, account in enumerate(self.accounts):
            if account.name == name:
                self.accounts.pop(i)
                
                # If we removed the default account, make the first remaining account default
                if account.is_default and self.accounts:
                    self.accounts[0].is_default = True
                
                return True
        return False

# Global instance
email_config = EmailConfigManager() 