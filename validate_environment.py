#!/usr/bin/env python3
"""
Standalone environment validation script for SalesBot.

This script can be run independently to:
1. Validate current environment variables
2. Generate .env template
3. Test system dependencies

Usage:
    python validate_environment.py                # Validate current environment
    python validate_environment.py --template     # Generate .env template
    python validate_environment.py --test-all     # Run full system tests
"""

import os
import sys
import argparse

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

def main():
    parser = argparse.ArgumentParser(description='SalesBot environment validation')
    parser.add_argument('--template', action='store_true',
                       help='Generate .env template file')
    parser.add_argument('--test-all', action='store_true',
                       help='Run full system validation including database')
    parser.add_argument('--output', type=str, default='.env.template',
                       help='Output file for template (default: .env.template)')
    
    args = parser.parse_args()
    
    try:
        from app.startup_validation import (
            run_startup_validation, 
            generate_env_template,
            validate_environment_variables,
            validate_database_connection,
            validate_encryption_setup,
            StartupValidationError
        )
        
        if args.template:
            print("📝 Generating .env template...")
            template_content = generate_env_template()
            
            with open(args.output, 'w') as f:
                f.write(template_content)
            
            print(f"✅ Template saved to {args.output}")
            print("📋 Edit this file with your actual values and copy to .env")
            return
        
        if args.test_all:
            print("🚀 Running full system validation...")
            run_startup_validation()
            print("✅ All validations passed!")
            return
        
        # Default: validate environment variables only
        print("🔍 Validating environment variables...")
        results = validate_environment_variables()
        
        if results['success']:
            print("✅ Environment variable validation passed!")
            
            if results['warnings']:
                print("\n⚠️  Warnings:")
                for warning in results['warnings']:
                    print(f"   {warning}")
        else:
            print("❌ Environment variable validation failed!")
            for error in results['errors']:
                print(f"   {error}")
            sys.exit(1)
            
    except ImportError as e:
        print(f"❌ Failed to import validation module: {e}")
        print("Make sure you're running from the salesbot directory")
        sys.exit(1)
    except StartupValidationError as e:
        print(f"❌ Validation failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()