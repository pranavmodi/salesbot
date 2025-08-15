#!/usr/bin/env python3
"""
Migration script to fix encrypted tenant settings after encryption key change.

This script handles cases where:
1. Encryption key was changed/missing in production
2. Existing encrypted data can't be decrypted with the current key
3. Need to migrate old data or reset tenant settings

Usage:
    python fix_encrypted_tenant_settings.py --reset-all  # Clear all encrypted settings
    python fix_encrypted_tenant_settings.py --migrate   # Try to migrate (requires old key)
"""

import os
import sys
import argparse
import uuid
from datetime import datetime
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import text

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.database import get_shared_engine
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def reset_all_encrypted_settings():
    """Reset all encrypted tenant settings to empty (user must re-enter API keys)."""
    logger.info("🔄 Resetting all encrypted tenant settings...")
    
    engine = get_shared_engine()
    with engine.connect() as conn:
        with conn.begin():
            # Update all tenant settings to clear encrypted fields
            result = conn.execute(text("""
                UPDATE tenant_settings SET
                    openai_api_key_encrypted = NULL,
                    anthropic_api_key_encrypted = NULL,
                    perplexity_api_key_encrypted = NULL,
                    email_configs_encrypted = NULL,
                    updated_at = CURRENT_TIMESTAMP
            """))
            
            affected_rows = result.rowcount
            logger.info(f"✅ Reset {affected_rows} tenant settings records")
            
            # List affected tenants
            result = conn.execute(text("SELECT tenant_id FROM tenant_settings"))
            tenant_ids = [str(row.tenant_id) for row in result]
            
            logger.info("📝 Affected tenant IDs:")
            for tenant_id in tenant_ids:
                logger.info(f"  - {tenant_id}")
            
    logger.info("✅ Migration complete. Users will need to re-enter their API keys in settings.")

def test_encryption_setup():
    """Test current encryption setup."""
    logger.info("🔍 Testing encryption setup...")
    
    # Check environment variable
    encryption_key = os.getenv('TENANT_SETTINGS_ENCRYPTION_KEY')
    if encryption_key:
        logger.info(f"✅ Encryption key found in environment (length: {len(encryption_key)})")
        
        # Test Fernet initialization
        try:
            fernet = Fernet(encryption_key.encode())
            
            # Test encryption/decryption cycle
            test_data = "test_api_key_12345"
            encrypted = fernet.encrypt(test_data.encode()).decode()
            decrypted = fernet.decrypt(encrypted.encode()).decode()
            
            if decrypted == test_data:
                logger.info("✅ Encryption/decryption cycle works correctly")
                return True
            else:
                logger.error("❌ Encryption/decryption cycle failed")
                return False
                
        except Exception as e:
            logger.error(f"❌ Fernet initialization failed: {e}")
            return False
    else:
        logger.error("❌ No TENANT_SETTINGS_ENCRYPTION_KEY in environment")
        return False

def check_current_data():
    """Check current tenant settings data."""
    logger.info("📊 Checking current tenant settings data...")
    
    engine = get_shared_engine()
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT 
                tenant_id,
                CASE WHEN openai_api_key_encrypted IS NOT NULL THEN 'present' ELSE 'missing' END as openai_key,
                CASE WHEN anthropic_api_key_encrypted IS NOT NULL THEN 'present' ELSE 'missing' END as anthropic_key,
                CASE WHEN email_configs_encrypted IS NOT NULL THEN 'present' ELSE 'missing' END as email_configs,
                created_at,
                updated_at
            FROM tenant_settings
            ORDER BY created_at
        """))
        
        logger.info("Current tenant settings status:")
        logger.info("Tenant ID                               | OpenAI | Anthropic | Email    | Created     | Updated")
        logger.info("-" * 110)
        
        for row in result:
            created = row.created_at.strftime("%m-%d %H:%M") if row.created_at else "None"
            updated = row.updated_at.strftime("%m-%d %H:%M") if row.updated_at else "None"
            logger.info(f"{str(row.tenant_id):36} | {row.openai_key:6} | {row.anthropic_key:9} | {row.email_configs:8} | {created} | {updated}")

def main():
    parser = argparse.ArgumentParser(description='Fix encrypted tenant settings migration')
    parser.add_argument('--reset-all', action='store_true', 
                       help='Reset all encrypted settings (users must re-enter API keys)')
    parser.add_argument('--check', action='store_true', 
                       help='Check current data status without making changes')
    parser.add_argument('--test-encryption', action='store_true',
                       help='Test current encryption setup')
    
    args = parser.parse_args()
    
    if args.test_encryption:
        test_encryption_setup()
        return
        
    if args.check:
        check_current_data()
        return
        
    if args.reset_all:
        logger.info("⚠️  This will reset all encrypted tenant settings!")
        logger.info("⚠️  Users will need to re-enter their API keys and email configurations!")
        
        confirm = input("Are you sure you want to proceed? Type 'yes' to continue: ")
        if confirm.lower() == 'yes':
            reset_all_encrypted_settings()
        else:
            logger.info("❌ Operation cancelled")
        return
    
    # Default: show help and current status
    parser.print_help()
    logger.info("\n" + "="*50)
    check_current_data()

if __name__ == '__main__':
    main()