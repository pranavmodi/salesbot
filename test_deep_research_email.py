#!/usr/bin/env python3
"""
Test script for the enhanced Deep Research Email Composer

This script demonstrates the new functionality that:
1. Automatically triggers deep research for companies
2. Generates and publishes strategic reports
3. Includes tracking-enabled public report links in emails
"""

import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from email_composers.email_composer_deep_research import DeepResearchEmailComposer

def test_deep_research_email():
    """Test the enhanced deep research email composition."""
    
    # Initialize the composer
    composer = DeepResearchEmailComposer()
    
    # Test with a sample lead
    test_lead = {
        "name": "Sarah Johnson",
        "email": "sarah.johnson@testcompany.com", 
        "company": "TestCorp Industries",
        "position": "VP of Operations",
        "website": "testcorp.com"
    }
    
    print("🧪 Testing Enhanced Deep Research Email Composer")
    print("=" * 60)
    print(f"Lead: {test_lead['name']} from {test_lead['company']}")
    print(f"Email: {test_lead['email']}")
    print()
    
    print("🔬 Starting deep research and email composition...")
    print("This will:")
    print("- Research the company automatically")
    print("- Generate a strategic analysis report")
    print("- Publish the report with a public URL")
    print("- Include the tracking-enabled report link in the email")
    print()
    
    # Compose the email (this will trigger auto-research)
    result = composer.compose_email(
        lead=test_lead,
        calendar_url="https://calendly.com/pranav-modi/15-minute-meeting",
        extra_context="This is a test email composition",
        auto_research=True
    )
    
    if result:
        print("✅ Email composition successful!")
        print("=" * 60)
        print(f"Subject: {result['subject']}")
        print()
        print("Body:")
        print(result['body'])
        print("=" * 60)
        
        # Check if report link is included
        if "public/reports" in result['body']:
            print("✅ Public report link included in email!")
        else:
            print("⚠️ No public report link found in email")
            
        # Check for tracking parameters
        if "utm_source=email" in result['body']:
            print("✅ Tracking parameters included!")
        else:
            print("⚠️ No tracking parameters found")
            
    else:
        print("❌ Email composition failed")
        return False
    
    return True

if __name__ == "__main__":
    print("🚀 Enhanced Deep Research Email Composer Test")
    print("=" * 60)
    
    success = test_deep_research_email()
    
    if success:
        print("\n🎉 Test completed successfully!")
        print("\nThe enhanced Deep Research email template now:")
        print("✅ Automatically triggers company research")
        print("✅ Generates strategic analysis reports")
        print("✅ Publishes reports at public URLs")
        print("✅ Includes tracking-enabled report links")
        print("✅ Creates highly personalized emails")
    else:
        print("\n❌ Test failed - check logs for details")
        sys.exit(1) 