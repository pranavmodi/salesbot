#!/usr/bin/env python3
"""
Migration script to move existing JSON email configuration to tenant-specific settings.
This will migrate the email accounts from email_accounts_config.json to the Default Tenant's settings.
"""

import os
import json
import sys
from pathlib import Path

# Add the project root to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent))

from app.models.tenant_settings import TenantSettings
from app.utils.email_config import EmailConfigManager
from app.database import get_shared_engine
from sqlalchemy import text

def migrate_email_config():
    """Migrate existing JSON email configuration to Default Tenant settings."""
    
    print("🔄 Starting email configuration migration...")
    
    try:
        # Load existing JSON email configuration
        json_config_path = 'email_accounts_config.json'
        if not os.path.exists(json_config_path):
            print(f"❌ JSON config file not found: {json_config_path}")
            return False
        
        # Load accounts from JSON file
        email_config_manager = EmailConfigManager(json_config_path)
        existing_accounts = email_config_manager.get_all_accounts()
        
        if not existing_accounts:
            print("❌ No email accounts found in JSON config file")
            return False
        
        print(f"📧 Found {len(existing_accounts)} email accounts in JSON config")
        
        # Get Default Tenant ID
        engine = get_shared_engine()
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT id FROM tenants WHERE name = 'Default Tenant' LIMIT 1
            """))
            tenant_row = result.fetchone()
            
            if not tenant_row:
                print("❌ Default Tenant not found in database")
                return False
            
            default_tenant_id = str(tenant_row.id)
            print(f"🏢 Default Tenant ID: {default_tenant_id}")
        
        # Convert accounts to the format expected by tenant settings
        accounts_data = []
        for account in existing_accounts:
            account_dict = account.to_dict()
            accounts_data.append(account_dict)
            print(f"   - {account.name}: {account.email}")
        
        # Save to tenant settings
        tenant_settings = TenantSettings()
        
        # Get existing tenant settings (if any)
        current_settings = tenant_settings.get_tenant_settings(default_tenant_id)
        
        # Add email configurations
        current_settings['email_configs'] = accounts_data
        
        # Save the settings
        success = tenant_settings.save_tenant_settings(current_settings, default_tenant_id)
        
        if success:
            print("✅ Email configuration migrated successfully to Default Tenant settings!")
            print(f"   - Migrated {len(accounts_data)} email accounts")
            
            # Optionally backup the JSON file
            backup_path = f"{json_config_path}.backup"
            if os.path.exists(json_config_path):
                import shutil
                shutil.copy2(json_config_path, backup_path)
                print(f"📁 Original JSON config backed up to: {backup_path}")
            
            return True
        else:
            print("❌ Failed to save email configuration to tenant settings")
            return False
            
    except Exception as e:
        print(f"❌ Migration failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_migration():
    """Verify that the migration was successful."""
    print("\n🔍 Verifying migration...")
    
    try:
        # Get Default Tenant ID
        engine = get_shared_engine()
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT id FROM tenants WHERE name = 'Default Tenant' LIMIT 1
            """))
            tenant_row = result.fetchone()
            default_tenant_id = str(tenant_row.id)
        
        # Load settings from tenant settings
        tenant_settings = TenantSettings()
        settings = tenant_settings.get_tenant_settings(default_tenant_id)
        
        email_configs = settings.get('email_configs', [])
        
        if email_configs:
            print(f"✅ Verification successful: {len(email_configs)} email accounts found in tenant settings")
            for config in email_configs:
                print(f"   - {config.get('name', 'Unknown')}: {config.get('email', 'No email')}")
            return True
        else:
            print("❌ Verification failed: No email accounts found in tenant settings")
            return False
            
    except Exception as e:
        print(f"❌ Verification failed with error: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 Email Configuration Migration Script")
    print("=" * 60)
    
    # Run migration
    success = migrate_email_config()
    
    if success:
        # Verify migration
        verify_migration()
        print("\n🎉 Migration completed successfully!")
        print("\n💡 Next steps:")
        print("   1. Restart your Flask application")
        print("   2. Navigate to /settings to manage your email accounts")
        print("   3. New tenants will start with empty email configurations")
    else:
        print("\n💥 Migration failed. Please check the errors above.")
        
    print("=" * 60)