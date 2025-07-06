#!/usr/bin/env python3
"""
Reset Campaign for Testing
==========================

This script resets a campaign's contact statuses back to 'active' 
so you can re-test the "Execute Now" functionality without creating new campaigns.

Usage:
    python scripts/reset_campaign_for_testing.py <campaign_id>
    python scripts/reset_campaign_for_testing.py --list  # List all campaigns
    python scripts/reset_campaign_for_testing.py --all   # Reset all campaigns
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.campaign import Campaign
from app.models.email_history import EmailHistory
from flask import current_app
from app import create_app
import argparse
from datetime import datetime

def list_campaigns():
    """List all available campaigns."""
    print("\n🎯 Available Campaigns:")
    print("=" * 60)
    
    campaigns = Campaign.get_all()
    if not campaigns:
        print("No campaigns found.")
        return
    
    for campaign in campaigns:
        stats = Campaign.get_campaign_stats(campaign.id)
        print(f"ID: {campaign.id}")
        print(f"Name: {campaign.name}")
        print(f"Status: {campaign.status}")
        print(f"Total Contacts: {stats.get('total_contacts', 0)}")
        print(f"Active Contacts: {stats.get('active_contacts', 0)}")
        print(f"Completed Contacts: {stats.get('completed_contacts', 0)}")
        print(f"Emails Sent: {stats.get('sent_emails', 0)}")
        print("-" * 40)

def reset_campaign(campaign_id):
    """Reset a specific campaign for testing."""
    try:
        # Get campaign
        campaign = Campaign.get_by_id(campaign_id)
        if not campaign:
            print(f"❌ Campaign {campaign_id} not found!")
            return False
        
        print(f"\n🔄 Resetting Campaign: {campaign.name} (ID: {campaign_id})")
        
        # Get current stats
        stats = Campaign.get_campaign_stats(campaign_id)
        print(f"Current Status: {campaign.status}")
        print(f"Total Contacts: {stats.get('total_contacts', 0)}")
        print(f"Completed Contacts: {stats.get('completed_contacts', 0)}")
        print(f"Emails Sent: {stats.get('sent_emails', 0)}")
        
        # Reset all contacts to 'active' status
        contacts = Campaign.get_campaign_contacts(campaign_id)
        reset_count = 0
        
        for contact in contacts:
            if contact.get('campaign_status') != 'active':
                success = Campaign.update_contact_status_in_campaign(
                    campaign_id, contact['email'], 'active'
                )
                if success:
                    reset_count += 1
                    print(f"  ✅ Reset {contact['email']} to active")
                else:
                    print(f"  ❌ Failed to reset {contact['email']}")
        
        # Reset campaign status to 'ready'
        Campaign.update_status(campaign_id, 'ready')
        
        print(f"\n🎉 Campaign Reset Complete!")
        print(f"   - {reset_count} contacts reset to 'active'")
        print(f"   - Campaign status set to 'ready'")
        print(f"   - You can now test 'Execute Now' again!")
        
        # Show new stats
        new_stats = Campaign.get_campaign_stats(campaign_id)
        print(f"\nNew Stats:")
        print(f"   - Active Contacts: {new_stats.get('active_contacts', 0)}")
        print(f"   - Status: ready")
        
        return True
        
    except Exception as e:
        print(f"❌ Error resetting campaign {campaign_id}: {e}")
        return False

def reset_all_campaigns():
    """Reset all campaigns for testing."""
    campaigns = Campaign.get_all()
    if not campaigns:
        print("No campaigns found.")
        return
    
    print(f"\n🔄 Resetting ALL {len(campaigns)} campaigns...")
    
    success_count = 0
    for campaign in campaigns:
        if reset_campaign(campaign.id):
            success_count += 1
        print()  # Empty line between campaigns
    
    print(f"🎉 Reset Complete: {success_count}/{len(campaigns)} campaigns reset successfully!")

def main():
    parser = argparse.ArgumentParser(description='Reset campaigns for testing')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('campaign_id', nargs='?', type=int, help='Campaign ID to reset')
    group.add_argument('--list', '-l', action='store_true', help='List all campaigns')
    group.add_argument('--all', '-a', action='store_true', help='Reset all campaigns')
    
    args = parser.parse_args()
    
    # Create Flask app context
    app = create_app()
    with app.app_context():
        if args.list:
            list_campaigns()
        elif args.all:
            confirm = input("\n⚠️  Are you sure you want to reset ALL campaigns? (yes/no): ")
            if confirm.lower() == 'yes':
                reset_all_campaigns()
            else:
                print("Operation cancelled.")
        else:
            reset_campaign(args.campaign_id)

if __name__ == '__main__':
    main() 