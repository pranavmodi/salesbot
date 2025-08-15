import uuid
import json
from typing import Dict, List, Optional, Any
from cryptography.fernet import Fernet
from sqlalchemy import text
from app.database import get_shared_engine
from app.tenant import current_tenant_id
import os
import base64
import logging

logger = logging.getLogger(__name__)

class TenantSettings:
    """Model for managing tenant-specific settings including encrypted email configs and API keys."""
    
    def __init__(self):
        # Generate or get encryption key from environment
        self._encryption_key = self._get_or_create_encryption_key()
        self._fernet = Fernet(self._encryption_key)
    
    def _get_or_create_encryption_key(self) -> bytes:
        """Get encryption key from environment or generate a new one."""
        key_str = os.getenv('TENANT_SETTINGS_ENCRYPTION_KEY')
        if key_str:
            return key_str.encode()
        else:
            # Generate new key for development
            key = Fernet.generate_key()
            logger.warning(f"Generated new encryption key. Add to .env: TENANT_SETTINGS_ENCRYPTION_KEY={key.decode()}")
            return key
    
    def _encrypt_data(self, data: str) -> str:
        """Encrypt sensitive data."""
        if not data:
            return data
        return self._fernet.encrypt(data.encode()).decode()
    
    def _decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data."""
        if not encrypted_data:
            return encrypted_data
        try:
            return self._fernet.decrypt(encrypted_data.encode()).decode()
        except Exception as e:
            logger.error(f"Failed to decrypt data: {e}")
            return ""
    
    def get_tenant_settings(self, tenant_id: str = None) -> Dict[str, Any]:
        """Get all settings for a tenant."""
        if not tenant_id:
            tenant_id = current_tenant_id()
        
        if not tenant_id:
            return {}
        
        engine = get_shared_engine()
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT email_configs_encrypted, openai_api_key_encrypted, 
                       anthropic_api_key_encrypted, perplexity_api_key_encrypted,
                       other_settings
                FROM tenant_settings 
                WHERE tenant_id = :tenant_id
            """), {'tenant_id': tenant_id})
            
            row = result.fetchone()
            if not row:
                return {}
            
            settings = {
                'email_configs': [],
                'openai_api_key': '',
                'anthropic_api_key': '',
                'perplexity_api_key': '',
                'other_settings': row.other_settings or {}
            }
            
            # Decrypt email configs
            if row.email_configs_encrypted:
                try:
                    decrypted_configs = self._decrypt_data(row.email_configs_encrypted)
                    settings['email_configs'] = json.loads(decrypted_configs) if decrypted_configs else []
                except (json.JSONDecodeError, Exception) as e:
                    logger.error(f"Failed to decrypt email configs: {e}")
            
            # Decrypt API keys
            settings['openai_api_key'] = self._decrypt_data(row.openai_api_key_encrypted or '')
            settings['anthropic_api_key'] = self._decrypt_data(row.anthropic_api_key_encrypted or '')
            settings['perplexity_api_key'] = self._decrypt_data(row.perplexity_api_key_encrypted or '')
            
            return settings
    
    def save_tenant_settings(self, settings: Dict[str, Any], tenant_id: str = None) -> bool:
        """Save tenant settings with encryption for sensitive data."""
        if not tenant_id:
            tenant_id = current_tenant_id()
        
        if not tenant_id:
            logger.error("No tenant_id provided for saving settings")
            return False
        
        logger.info(f"Saving tenant settings for tenant_id: {tenant_id}")
        logger.info(f"Settings keys being saved: {list(settings.keys())}")
        
        # Check if encryption key is available
        if not self._fernet:
            logger.error("CRITICAL: Fernet encryption not initialized - API keys cannot be saved securely")
            return False
            
        try:
            engine = get_shared_engine()
            with engine.connect() as conn:
                with conn.begin():
                    # Check if settings exist
                    result = conn.execute(text("""
                        SELECT id FROM tenant_settings WHERE tenant_id = :tenant_id
                    """), {'tenant_id': tenant_id})
                    
                    existing_row = result.fetchone()
                    
                    # Encrypt sensitive data
                    email_configs_encrypted = None
                    if settings.get('email_configs'):
                        email_configs_json = json.dumps(settings['email_configs'])
                        email_configs_encrypted = self._encrypt_data(email_configs_json)
                    
                    openai_key_encrypted = self._encrypt_data(settings.get('openai_api_key', ''))
                    anthropic_key_encrypted = self._encrypt_data(settings.get('anthropic_api_key', ''))
                    perplexity_key_encrypted = self._encrypt_data(settings.get('perplexity_api_key', ''))
                    
                    logger.info(f"Encrypted key lengths - OpenAI: {len(openai_key_encrypted or '')}, Anthropic: {len(anthropic_key_encrypted or '')}")
                    
                    if existing_row:
                        # Update existing settings
                        conn.execute(text("""
                            UPDATE tenant_settings SET
                                email_configs_encrypted = :email_configs,
                                openai_api_key_encrypted = :openai_key,
                                anthropic_api_key_encrypted = :anthropic_key,
                                perplexity_api_key_encrypted = :perplexity_key,
                                other_settings = :other_settings,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE tenant_id = :tenant_id
                        """), {
                            'tenant_id': tenant_id,
                            'email_configs': email_configs_encrypted,
                            'openai_key': openai_key_encrypted,
                            'anthropic_key': anthropic_key_encrypted,
                            'perplexity_key': perplexity_key_encrypted,
                            'other_settings': json.dumps(settings.get('other_settings', {}))
                        })
                    else:
                        # Create new settings
                        conn.execute(text("""
                            INSERT INTO tenant_settings (
                                id, tenant_id, email_configs_encrypted,
                                openai_api_key_encrypted, anthropic_api_key_encrypted,
                                perplexity_api_key_encrypted, other_settings
                            ) VALUES (
                                :id, :tenant_id, :email_configs,
                                :openai_key, :anthropic_key,
                                :perplexity_key, :other_settings
                            )
                        """), {
                            'id': str(uuid.uuid4()),
                            'tenant_id': tenant_id,
                            'email_configs': email_configs_encrypted,
                            'openai_key': openai_key_encrypted,
                            'anthropic_key': anthropic_key_encrypted,
                            'perplexity_key': perplexity_key_encrypted,
                            'other_settings': json.dumps(settings.get('other_settings', {}))
                        })
                    
                    # Verify the save by reading it back
                    verify_result = conn.execute(text("""
                        SELECT openai_api_key_encrypted FROM tenant_settings WHERE tenant_id = :tenant_id
                    """), {'tenant_id': tenant_id})
                    verify_row = verify_result.fetchone()
                    
                    if verify_row and verify_row.openai_api_key_encrypted:
                        logger.info(f"✅ Save verified - encrypted key exists in database for tenant {tenant_id}")
                        # Try to decrypt it immediately to verify encryption/decryption works
                        try:
                            decrypted_key = self._decrypt_data(verify_row.openai_api_key_encrypted)
                            if decrypted_key:
                                logger.info(f"✅ Encryption/decryption verified - key can be read back (length: {len(decrypted_key)})")
                            else:
                                logger.error(f"❌ Decryption failed - encrypted key exists but cannot be decrypted")
                        except Exception as decrypt_err:
                            logger.error(f"❌ Decryption test failed: {decrypt_err}")
                    else:
                        logger.error(f"❌ Save verification failed - no encrypted key found in database after save")
                    
                    return True
                    
        except Exception as e:
            logger.error(f"Failed to save tenant settings: {e}")
            logger.error(f"Exception type: {type(e).__name__}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    def get_email_configs(self, tenant_id: str = None) -> List[Dict[str, Any]]:
        """Get email configurations for a tenant."""
        settings = self.get_tenant_settings(tenant_id)
        return settings.get('email_configs', [])
    
    def get_api_key(self, service: str, tenant_id: str = None) -> str:
        """Get API key for a specific service (openai, anthropic, perplexity)."""
        settings = self.get_tenant_settings(tenant_id)
        return settings.get(f'{service}_api_key', '')