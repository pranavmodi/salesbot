import logging
from typing import List, Dict, Optional
from app.models.tenant_settings import TenantSettings
from app.tenant import current_tenant_id

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

class TenantEmailConfigManager:
    """Manages tenant-specific email account configurations."""
    
    def __init__(self, tenant_id: str = None):
        self.tenant_id = tenant_id or current_tenant_id()
        self.tenant_settings = TenantSettings()
        self.accounts: List[EmailAccount] = []
        self.load_accounts()
    
    def load_accounts(self):
        """Load email accounts from tenant settings."""
        try:
            if not self.tenant_id:
                logger.warning("No tenant_id available for loading email accounts")
                return
            
            email_configs = self.tenant_settings.get_email_configs(self.tenant_id)
            self.accounts = [EmailAccount(config) for config in email_configs]
            
            if self.accounts:
                logger.info(f"Loaded {len(self.accounts)} email accounts from tenant settings")
            else:
                logger.info("No email accounts configured for tenant")
                
        except Exception as e:
            logger.error(f"Failed to load email accounts from tenant settings: {e}")
            self.accounts = []
    
    def save_accounts(self, accounts_data: List[Dict]) -> bool:
        """Save email accounts to tenant settings."""
        try:
            if not self.tenant_id:
                logger.error("No tenant_id available for saving email accounts")
                return False
            
            # Get current settings and update email configs
            settings = self.tenant_settings.get_tenant_settings(self.tenant_id)
            settings['email_configs'] = accounts_data
            
            success = self.tenant_settings.save_tenant_settings(settings, self.tenant_id)
            if success:
                # Reload accounts after saving
                self.load_accounts()
                logger.info(f"Saved {len(accounts_data)} email accounts to tenant settings")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to save email accounts to tenant settings: {e}")
            return False
    
    def add_account(self, account_config: Dict) -> bool:
        """Add a new email account."""
        account = EmailAccount(account_config)
        if not account.is_valid():
            logger.error("Invalid email account configuration")
            return False
        
        # Get current accounts and add new one
        current_configs = [acc.to_dict() for acc in self.accounts]
        current_configs.append(account_config)
        
        return self.save_accounts(current_configs)
    
    def remove_account(self, email: str) -> bool:
        """Remove an email account by email address."""
        current_configs = [acc.to_dict() for acc in self.accounts if acc.email != email]
        return self.save_accounts(current_configs)
    
    def get_accounts(self) -> List[EmailAccount]:
        """Get all email accounts for the current tenant."""
        return self.accounts
    
    def get_default_account(self) -> Optional[EmailAccount]:
        """Get the default email account."""
        default_accounts = [acc for acc in self.accounts if acc.is_default]
        if default_accounts:
            return default_accounts[0]
        elif self.accounts:
            return self.accounts[0]  # Return first account as fallback
        return None
    
    def get_account_by_email(self, email: str) -> Optional[EmailAccount]:
        """Get account by email address."""
        for account in self.accounts:
            if account.email == email:
                return account
        return None
    
    def has_accounts(self) -> bool:
        """Check if tenant has any email accounts configured."""
        return len(self.accounts) > 0