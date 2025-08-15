"""
Startup validation for required environment variables and system dependencies.

This module validates that all critical environment variables are present
before the Flask application starts up.
"""

import os
import sys
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# Required environment variables for the application
REQUIRED_ENV_VARS = {
    'DATABASE_URL': {
        'description': 'PostgreSQL database connection URL',
        'example': 'postgresql://user:password@localhost:5432/salesbot',
        'critical': True
    },
    'TENANT_SETTINGS_ENCRYPTION_KEY': {
        'description': 'Fernet encryption key for tenant settings (44 characters)',
        'example': 'WTT3DpBB5DSME4iYhuBinmU6JYNBuiHrGGEh0ZXApZs=',
        'critical': True,
        'validation': lambda val: len(val) == 44
    },
    'ADMIN_EMAILS': {
        'description': 'Comma-separated list of admin email addresses',
        'example': 'admin@example.com,user@example.com',
        'critical': True
    }
}

# Optional but recommended environment variables
OPTIONAL_ENV_VARS = {
    'OPENAI_API_KEY': {
        'description': 'OpenAI API key (fallback if tenant-specific not set)',
        'example': 'sk-...',
        'critical': False
    },
    'ANTHROPIC_API_KEY': {
        'description': 'Anthropic API key (fallback if tenant-specific not set)',
        'example': 'sk-ant-...',
        'critical': False
    },
    'PERPLEXITY_API_KEY': {
        'description': 'Perplexity API key (fallback if tenant-specific not set)',
        'example': 'pplx-...',
        'critical': False
    },
    'FLASK_SECRET_KEY': {
        'description': 'Flask session encryption key (optional - will be generated if not set)',
        'example': 'your-secret-key-here',
        'critical': False
    },
    'NETLIFY_PUBLISH_URL': {
        'description': 'Netlify deployment URL for deep research reports',
        'example': 'https://your-netlify-site.netlify.app',
        'critical': False
    }
}

class StartupValidationError(Exception):
    """Raised when critical startup validation fails."""
    pass

def validate_environment_variables() -> Dict[str, any]:
    """
    Validate all required and optional environment variables.
    
    Returns:
        Dict containing validation results
        
    Raises:
        StartupValidationError: If critical validation fails
    """
    results = {
        'success': True,
        'errors': [],
        'warnings': [],
        'missing_critical': [],
        'missing_optional': [],
        'invalid_format': []
    }
    
    logger.info("🔍 Validating environment variables...")
    
    # Check required variables
    for var_name, config in REQUIRED_ENV_VARS.items():
        value = os.getenv(var_name)
        
        if not value:
            error_msg = f"❌ Missing required environment variable: {var_name}"
            logger.error(error_msg)
            logger.error(f"   Description: {config['description']}")
            logger.error(f"   Example: {config['example']}")
            
            results['errors'].append(error_msg)
            results['missing_critical'].append(var_name)
            results['success'] = False
        else:
            # Validate format if validation function provided
            if 'validation' in config:
                try:
                    if not config['validation'](value):
                        error_msg = f"❌ Invalid format for {var_name}"
                        logger.error(error_msg)
                        logger.error(f"   Expected: {config['description']}")
                        logger.error(f"   Example: {config['example']}")
                        
                        results['errors'].append(error_msg)
                        results['invalid_format'].append(var_name)
                        results['success'] = False
                    else:
                        logger.info(f"✅ {var_name}: Valid")
                except Exception as e:
                    error_msg = f"❌ Error validating {var_name}: {e}"
                    logger.error(error_msg)
                    results['errors'].append(error_msg)
                    results['invalid_format'].append(var_name)
                    results['success'] = False
            else:
                logger.info(f"✅ {var_name}: Present")
    
    # Check optional variables
    for var_name, config in OPTIONAL_ENV_VARS.items():
        value = os.getenv(var_name)
        
        if not value:
            warning_msg = f"⚠️  Optional environment variable not set: {var_name}"
            logger.warning(warning_msg)
            logger.warning(f"   Description: {config['description']}")
            
            results['warnings'].append(warning_msg)
            results['missing_optional'].append(var_name)
        else:
            logger.info(f"✅ {var_name}: Present (optional)")
    
    return results

def validate_environment_variables_silent() -> Dict[str, any]:
    """Silent version of environment variable validation - no logging."""
    results = {'success': True, 'errors': [], 'missing_critical': []}
    
    for var_name, config in REQUIRED_ENV_VARS.items():
        value = os.getenv(var_name)
        if not value:
            results['success'] = False
            results['missing_critical'].append(var_name)
        elif 'validation' in config:
            try:
                if not config['validation'](value):
                    results['success'] = False
            except Exception:
                results['success'] = False
    
    return results

def validate_database_connection() -> bool:
    """
    Test database connection without importing heavy dependencies.
    
    Returns:
        bool: True if connection successful
    """
    try:
        from app.database import get_shared_engine
        from sqlalchemy import text
        
        logger.info("🔍 Testing database connection...")
        
        engine = get_shared_engine()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
            
        logger.info("✅ Database connection successful")
        return True
        
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False

def validate_encryption_setup() -> bool:
    """
    Test encryption key setup.
    
    Returns:
        bool: True if encryption works
    """
    try:
        from cryptography.fernet import Fernet
        
        logger.info("🔍 Testing encryption setup...")
        
        encryption_key = os.getenv('TENANT_SETTINGS_ENCRYPTION_KEY')
        if not encryption_key:
            logger.error("❌ No encryption key available")
            return False
            
        fernet = Fernet(encryption_key.encode())
        
        # Test encryption/decryption cycle
        test_data = "startup_validation_test"
        encrypted = fernet.encrypt(test_data.encode())
        decrypted = fernet.decrypt(encrypted).decode()
        
        if decrypted == test_data:
            logger.info("✅ Encryption setup working correctly")
            return True
        else:
            logger.error("❌ Encryption/decryption cycle failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ Encryption setup failed: {e}")
        return False

def validate_encryption_setup_silent() -> bool:
    """Silent version of encryption validation - no logging."""
    try:
        from cryptography.fernet import Fernet
        
        encryption_key = os.getenv('TENANT_SETTINGS_ENCRYPTION_KEY')
        if not encryption_key:
            return False
            
        fernet = Fernet(encryption_key.encode())
        
        # Test encryption/decryption cycle
        test_data = "startup_validation_test"
        encrypted = fernet.encrypt(test_data.encode())
        decrypted = fernet.decrypt(encrypted).decode()
        
        return decrypted == test_data
            
    except Exception:
        return False

# Global flag to prevent duplicate validation logging
_validation_already_run = False

def run_startup_validation() -> None:
    """
    Run complete startup validation.
    
    Raises:
        StartupValidationError: If critical validation fails
    """
    global _validation_already_run
    
    # Only show full logging on first run
    if _validation_already_run:
        # Silent validation - just check for critical errors
        env_results = validate_environment_variables_silent()
        if not env_results['success']:
            raise StartupValidationError("Critical environment variables missing or invalid")
        if not validate_encryption_setup_silent():
            raise StartupValidationError("Encryption setup validation failed")
        return
    
    logger.info("🚀 Starting application validation...")
    _validation_already_run = True
    
    # Validate environment variables
    env_results = validate_environment_variables()
    
    if not env_results['success']:
        logger.error("❌ Critical environment variable validation failed!")
        logger.error("   Application cannot start safely.")
        logger.error("")
        logger.error("🔧 To fix these issues:")
        
        for var_name in env_results['missing_critical']:
            config = REQUIRED_ENV_VARS[var_name]
            logger.error(f"   Set {var_name}={config['example']}")
            
        for var_name in env_results['invalid_format']:
            config = REQUIRED_ENV_VARS[var_name]
            logger.error(f"   Fix {var_name} format: {config['description']}")
        
        raise StartupValidationError("Critical environment variables missing or invalid")
    
    # Test database connection (non-critical - will retry)
    if not validate_database_connection():
        logger.warning("⚠️  Database connection failed - will retry during operation")
    
    # Test encryption setup (critical)
    if not validate_encryption_setup():
        raise StartupValidationError("Encryption setup validation failed")
    
    # Show warnings for optional variables (only once)
    if env_results['warnings']:
        logger.warning("⚠️  Some optional features may not work:")
        for warning in env_results['warnings']:
            logger.warning(f"   {warning}")
    
    logger.info("✅ Startup validation completed successfully!")
    logger.info("🚀 Application is ready to start")

def generate_env_template() -> str:
    """Generate a .env template file content."""
    template = "# SalesBot Environment Configuration\n"
    template += "# Copy this file to .env and fill in your values\n\n"
    
    template += "# Required Variables\n"
    for var_name, config in REQUIRED_ENV_VARS.items():
        template += f"# {config['description']}\n"
        template += f"{var_name}={config['example']}\n\n"
    
    template += "# Optional Variables (recommended for full functionality)\n"
    for var_name, config in OPTIONAL_ENV_VARS.items():
        template += f"# {config['description']}\n"
        template += f"#{var_name}={config['example']}\n\n"
    
    return template

if __name__ == '__main__':
    # Can be run standalone for validation
    try:
        run_startup_validation()
        print("✅ All validations passed!")
    except StartupValidationError as e:
        print(f"❌ Validation failed: {e}")
        sys.exit(1)