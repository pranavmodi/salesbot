#!/usr/bin/env python3
"""
Test script to debug email configuration discrepancy between UI and API.
"""

import requests
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_configuration_endpoints():
    """Test the email configuration endpoints to identify discrepancies."""
    base_url = "http://127.0.0.1:8080"
    
    print("🔍 Testing Email Configuration Discrepancy")
    print("=" * 50)
    
    # Test 1: Get current accounts via API
    print("\n1. Testing GET /api/email/accounts")
    try:
        response = requests.get(f"{base_url}/api/email/accounts")
        if response.status_code == 200:
            data = response.json()
            if data['success']:
                accounts = data['accounts']
                print(f"✅ API returned {len(accounts)} accounts")
                for i, account in enumerate(accounts):
                    print(f"   Account {i+1}: {account['name']}")
                    print(f"   - Email: {account['email']}")
                    print(f"   - IMAP Host: {account['imap_host']}")
                    print(f"   - IMAP Port: {account['imap_port']}")
                    print(f"   - Is Default: {account['is_default']}")
                    print()
            else:
                print(f"❌ API Error: {data['message']}")
        else:
            print(f"❌ HTTP Error: {response.status_code}")
    except Exception as e:
        print(f"❌ Request failed: {e}")
    
    # Test 2: Check environment variable directly
    print("\n2. Testing environment variable EMAIL_ACCOUNTS")
    email_accounts_env = os.getenv('EMAIL_ACCOUNTS')
    if email_accounts_env:
        try:
            env_accounts = json.loads(email_accounts_env)
            print(f"✅ Environment variable contains {len(env_accounts)} accounts")
            for i, account in enumerate(env_accounts):
                print(f"   Account {i+1}: {account['name']}")
                print(f"   - Email: {account['email']}")
                print(f"   - IMAP Host: {account['imap_host']}")
                print(f"   - IMAP Port: {account['imap_port']}")
                print(f"   - Is Default: {account['is_default']}")
                print()
        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing error: {e}")
    else:
        print("❌ EMAIL_ACCOUNTS environment variable not found")
    
    # Test 3: Check .env file directly
    print("\n3. Testing .env file content")
    try:
        with open('.env', 'r') as f:
            lines = f.readlines()
            for i, line in enumerate(lines):
                if line.startswith('EMAIL_ACCOUNTS='):
                    print(f"✅ Found EMAIL_ACCOUNTS at line {i+1}")
                    # Try to parse the JSON from the file
                    json_part = line[len('EMAIL_ACCOUNTS='):].strip()
                    try:
                        file_accounts = json.loads(json_part)
                        print(f"✅ File contains {len(file_accounts)} accounts")
                        for j, account in enumerate(file_accounts):
                            print(f"   Account {j+1}: {account['name']}")
                            print(f"   - Email: {account['email']}")
                            print(f"   - IMAP Host: {account['imap_host']}")
                            print(f"   - IMAP Port: {account['imap_port']}")
                            print(f"   - Is Default: {account['is_default']}")
                            print()
                    except json.JSONDecodeError as e:
                        print(f"❌ JSON parsing error in file: {e}")
                        print(f"   Raw content: {json_part[:100]}...")
                    break
            else:
                print("❌ EMAIL_ACCOUNTS line not found in .env file")
    except FileNotFoundError:
        print("❌ .env file not found")
    except Exception as e:
        print(f"❌ Error reading .env file: {e}")
    
    # Test 4: Use debug endpoint
    print("\n4. Testing debug endpoint")
    try:
        response = requests.get(f"{base_url}/api/email/config/debug")
        if response.status_code == 200:
            data = response.json()
            if data['success']:
                debug_info = data['debug_info']
                print("✅ Debug endpoint response:")
                print(f"   - .env file exists: {debug_info['env_file_exists']}")
                print(f"   - .env2 file exists: {debug_info['env2_file_exists']}")
                print(f"   - Config manager status: {debug_info['config_manager_status']}")
                print(f"   - Loaded accounts count: {len(debug_info['loaded_accounts'])}")
                
                if 'env_file_line' in debug_info:
                    print(f"   - .env file line: {debug_info['env_file_line'][:100]}...")
                    
                if debug_info['loaded_accounts']:
                    print("   - Loaded accounts:")
                    for account in debug_info['loaded_accounts']:
                        print(f"     * {account['name']}: IMAP {account['imap_host']}")
            else:
                print(f"❌ Debug endpoint error: {data['message']}")
        else:
            print(f"❌ Debug endpoint HTTP error: {response.status_code}")
    except Exception as e:
        print(f"❌ Debug endpoint request failed: {e}")

def compare_configurations():
    """Compare configurations between different sources."""
    print("\n" + "=" * 50)
    print("🔍 Configuration Comparison Summary")
    print("=" * 50)
    
    # This will help identify where the discrepancy is coming from
    configurations = {}
    
    # Get API configuration
    try:
        response = requests.get("http://127.0.0.1:8080/api/email/accounts")
        if response.status_code == 200 and response.json()['success']:
            configurations['api'] = response.json()['accounts']
    except:
        configurations['api'] = "ERROR"
    
    # Get environment variable configuration
    try:
        env_accounts = os.getenv('EMAIL_ACCOUNTS')
        if env_accounts:
            configurations['env_var'] = json.loads(env_accounts)
    except:
        configurations['env_var'] = "ERROR"
    
    # Get .env file configuration
    try:
        with open('.env', 'r') as f:
            for line in f:
                if line.startswith('EMAIL_ACCOUNTS='):
                    json_part = line[len('EMAIL_ACCOUNTS='):].strip()
                    configurations['env_file'] = json.loads(json_part)
                    break
    except:
        configurations['env_file'] = "ERROR"
    
    # Compare primary account IMAP hosts
    print("\nPrimary Account IMAP Host Comparison:")
    for source, config in configurations.items():
        if isinstance(config, list) and config:
            primary_account = next((acc for acc in config if acc.get('is_default')), config[0])
            imap_host = primary_account.get('imap_host', 'UNKNOWN')
            print(f"   {source.upper()}: {imap_host}")
        else:
            print(f"   {source.upper()}: {config}")
    
    return configurations

if __name__ == "__main__":
    test_configuration_endpoints()
    compare_configurations()
    
    print("\n" + "=" * 50)
    print("💡 Troubleshooting Tips:")
    print("1. If API and env_var differ, the app needs restart to reload .env")
    print("2. If env_var and env_file differ, there's a loading issue")
    print("3. If all sources match but UI shows different, check browser cache")
    print("4. Use the debug endpoint to get real-time configuration state")
    print("=" * 50) 